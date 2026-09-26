# Nongki_OP8_OOS_build — Patch Archive & Build Record

Kernel: **OnePlus OSS official (OnePlusOSS/android_kernel_oneplus_sm8250)** branch `oneplus/sm8250_t_13.1_op8`
Version: **4.19.157-perf+** (OxygenOS 13.1 / Android 13)
Base commit: `1d2678a3548f4825447f17b25a5cc1754c4cd1ae`
(Synchronize code for OnePlus IN2013_13.1.0.593(EX01) ... QCOM release TAG:AU_LINUX_ANDROID_LA.UM.9.12.1.R1.11.00.00.893.009)
Kernel source: `~/android_kernel_oneplus_sm8250` (local)
Archive generated: 2026-08-20

> This is the **continue-from-here** handoff record. Read the whole README before resuming.
> The live patches actually used by the workflow are under `../Patch/` and `../Droidspaces/`;
> `Archive/` mirrors them for record/replay and includes the full dev log.

---

## Repository layout (what the workflow actually does)

GitHub Actions chain: `build-release.yml` → `build-kernel.yml` → `build-oneplus-8-los23-a16.yml`
+ composite actions `build-env` / `build-ready` / `build-process` / `pack-process` / `upload-files`.

Component sources:
- Kernel: `OnePlusOSS/android_kernel_oneplus_sm8250@oneplus/sm8250_t_13.1_op8`
- Vendor/Devicetree/Techpack: `OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8250@oneplus/sm8250_t_13.1_op8`
- ReSukiSU: `setup.sh` at build time (latest `main`)
- SUSFS: bundled patch (re-generated for OOS 4.19.157)
- BBG: `curl setup.sh | bash` at build time (non-GKI path)
- DroidSpaces: bundled patch

Integrations (final): **ReSukiSU + SUSFS v2.2.0 + DroidSpaces + Baseband Guard**. **No Re:Kernel** (see below).

---

## ⚠️ CRITICAL differences vs the LineageOS fork (NonGKI_Kernel_Build_OP8)

The OnePlus OSS kernel is an **old 4.19.157 structure** with several non-obvious facts that
cost a lot of iteration to discover. Read these before changing anything.

### 1. Device tree is NOT in-tree (symlink to external repo)
- `arch/arm64/boot/dts/vendor` is a symlink → `../../../../../../vendor/qcom/proprietary/devicetree-4.19`
- 86+ symlinks point into `vendor/oplus/kernel/*` (charger, touchpanel, oplus_performance, network, ...)
- These must be supplied from the **modules_and_devicetree** repo.

**Symlink depth resolution (crucial):**
- `arch/arm64/boot/dts/vendor` (6 `..`) and `drivers/soc/oplus/*` (5 `..`) and `kernel/sched_assist`
  (3 `..`) all resolve to the **2-level parent of the kernel dir**.
- If kernel sits at `$GITHUB_WORKSPACE/device_kernel`, that 2-level parent is the **runner workspace
  (read-only)** → symlinks cannot resolve.
- **Fix: place kernel at `$GITHUB_WORKSPACE/kernel/device_kernel`**, then vendor at
  `$GITHUB_WORKSPACE/vendor` resolves correctly for ALL symlinks.
- Verified with a local dir-tree test: all symlinks resolve when kernel is one level deeper.

### 2. Techpack (camera/display/video) is an EMPTY gitlink in the kernel repo
- `git ls-tree HEAD techpack/` → `160000 commit ...` for `camera`/`display`/`video` (gitlinks),
  but **no `.gitmodules`** (OnePlus manages them via Android build manifest).
- Empty dirs + `techpack/Kbuild`'s `find` → build error:
  `../techpack/camera/Makefile: No such file or directory` / `techpack/modules.builtin` Error 2.
- **Fix: the actual techpack sources live in the modules_and_devicetree repo** at
  `kernel/msm-4.19/techpack/{camera,display,video}`. Copy them over the empty gitlinks.
  - This is the SAME QCOM release tag as the kernel (`AU_LINUX_ANDROID_LA.UM.9.12.1.R1.11.00.00.893.009`)
    → version-matched, compiles.
  - OOS `kona-perf_defconfig` does **not** enable these drivers (`CONFIG_SPECTRA_CAMERA` etc. unset),
    so after filling they compile as no-ops (Kbuild passes, drivers stay off, matching stock config).
  - Do NOT borrow techpack from ppajda XTD kernel (4.19.325) — version mismatch → compile failures.

### 3. No Re:Kernel — OOS ships its own HANS
- OOS has `drivers/staging/android/hans.c` + `hans_netfilter.c` (`CONFIG_OPLUS_HANS=y`),
  a OnePlus binder/freeze manager that covers the same role as Re:Kernel.
- Re:Kernel's `enum report_type { BINDER, SIGNAL, NETWORK }` **clashes** with OOS
  `include/linux/hans.h` (`enum message_type { ... SIGNAL ... }`) → `redefinition of enumerator 'SIGNAL'`
  in `kernel/signal.c`.
- **Decision: drop Re:Kernel entirely.** Removed patch, workflow step, and config.

---

## Build-time issues & fixes (chronological, all verified)

### FIX A — Vendor symlink resolution (build-ready "Setup OOS vendor layout")
Symptom: `[-] arch/arm64/boot/dts/vendor cannot resolve, OOS build will fail.`
Fix: put kernel in `$GITHUB_WORKSPACE/kernel/device_kernel`, vendor in `$GITHUB_WORKSPACE/vendor`.
(Also clone techpack from the same modules_and_devicetree clone.)

### FIX B — Clang assembler wrong (vdso)
Symptom: `vgettimeofday.s: Error: junk at end of line` via `/usr/bin/as` (x86 assembler).
Cause: `CLANG_TRIPLE=aarch64-linux-gnu-` mismatched the downloaded GCC prefix
(`aarch64-linux-android-`). Clang looked for `aarch64-linux-gnu-as`, fell back to host `as`.
Fix: `CUSTOM_CMDS : "CLANG_TRIPLE=aarch64-linux-android-"` (match actual binutils prefix).

### FIX C — clang 19 strict warnings as -Werror (recurring)
OOS 4.19.157 oplus code triggers several clang-19 default `-Werror` diagnostics:
- `-Wstrict-prototypes` (empty-arg fn `static void __exit boot_state_exit()`)
  → `arch/arm64/kernel/rootguard/oplus_guard_general.c:86`
- `-Wimplicit-int` (missing return type) → `drivers/block/zram/hybridswap/hybridswap_eswap.c:544`
- (also covered) `-Wincompatible-function-pointer-types`, `-Wdeprecated-non-prototype`,
  `-Wint-to-pointer-cast`, `-Wpointer-to-int-cast`, `-Wimplicit-function-declaration`,
  `-Wunused-but-set-variable`

**Critical gotcha:** the KCFLAGS value contains spaces. An **unquoted**
`KCFLAGS=-Wa -Wb -Wc` is split by the shell → only `-Wa` reaches make. Must quote:
```
EXTRA_CMDS : 'KCFLAGS="-Wno-strict-prototypes ... -Wno-implicit-int ..."'
```
This is why `-Wstrict-prototypes` (first flag) took effect but `-Wimplicit-int` didn't,
until the whole value was quoted. Verified with a make test.

### FIX D — fdinfo.o implicit declaration
Symptom: `fs/notify/fdinfo.c: error: implicit declaration of function 'inotify_mark_user_mask'`.
Cause: SUSFS patch referenced `inotify_mark_user_mask(mark)` which **does not exist in OOS 4.19.157**.
Fix: use native `(mark->mask & IN_ALL_EVENTS)` (matches OOS's own inotify_fdinfo code).

### FIX E — (historical) Re:Kernel enum clash → removed Re:Kernel (see §3).

---

## SUSFS re-generation for OOS 4.19.157

The OP8/LOS patch (4.19.325) does **not** apply cleanly to OOS (namei/namespace layout differs:
OOS uses old `vfs_kern_mount`, has no `ND_STATE`). The OOS patch is based on
**JackA1ltman's generic 4.19 patch** (`NonGKI_Kernel_Build_2nd`), which targets the same
old `vfs_kern_mount` structure, then manually fixed for OOS:

- `fs/namespace.c`: OOS has an extra `CONFIG_OPLUS_SECURE_GUARD` include block → hunk#1 fixed manually.
- `fs/notify/fdinfo.c`: OOS already had partial SUSFS signatures (3-arg `show_fdinfo`) →
  hunk#4 body filled manually (also fix `inotify_mark_user_mask` → `(mark->mask & IN_ALL_EVENTS)`, see FIX D).
- `drivers/input/input.c`: OOS has `OPLUS_FEATURE_SAUPWK` block → input hook placed accordingly.
- `fs/read_write.c`: OOS has `OPLUS_FEATURE_IOMONITOR` block → sys_read hook adapted
  (+ extern decl added manually).
- `fs/stat.c`: `ksu_handle_stat` added manually (Jack's patch doesn't include it for OOS).

ReSukiSU inline hooks kept (exec / open(faccessat) / read_write / stat / input / reboot / setresuid),
applied via the bundled `susfs_resukisu_oos_4.19.patch`.

### SUSFS notes (inherited from the OP8 fork, still relevant)
- 4.19: use `inode->i_state` for `AS_FLAGS_*` (NOT `i_mapping->flags`), old fsnotify API,
  `set_nameidata()` sets `p->state = 0` (boot-crash suspect #1).
- `CONFIG_KALLSYMS_ALL=y` (OOS has it) → no need for static-symbol exports.
- ReSukiSU setup.sh registers `drivers/kernelsu` (symlink + Makefile + Kconfig); SUSFS config
  symbols live in ReSukiSU's `kernel/Kconfig`.

---

## Defconfig fragment (defconfig_oos.patch)

OOS `vendor/kona-perf_defconfig` embeds oplus config already (no separate oplus.config to merge).
Injected at top:
```
CONFIG_KSU=y, CONFIG_KSU_SUSFS=y + all 10 sub-options,
CONFIG_BBG=y,
DroidSpaces Non-GKI: SYSVIPC, POSIX_MQUEUE, IPC_NS, CGROUP_DEVICE/PIDS/NET_PRIO,
  DEVTMPFS, BRIDGE_NETFILTER, NF_TABLES, NETFILTER_XT_MATCH_ADDRTYPE, USER_NS
```
NO `CONFIG_REKERNEL` (Re:Kernel dropped).

---

## Verification status (as of archive date)

- All patches apply cleanly (zero `.rej`) to a clean OOS kernel in order:
  SUSFS+ReSukiSU → DroidSpaces → BBG(setup.sh) → defconfig, after ReSukiSU setup.sh.
- `make ... vendor/kona-perf_defconfig` succeeds; `.config` contains
  `CONFIG_KSU=y`, `CONFIG_KSU_SUSFS=y` (+all subs), `CONFIG_BBG=y`, `CONFIG_USER_NS=y`,
  `CONFIG_OPLUS_HANS=y`, and **no** `CONFIG_REKERNEL`.
- Full kernel compile **not yet green locally** (host lacks aarch64 binutils). CI on
  GitHub Actions has progressed through: vendor symlinks ✅, vdso asm ✅, rootguard ✅,
  hybridswap (`-Wimplicit-int`) ✅ (after quoting KCFLAGS), fdinfo ✅, Re:Kernel removed ✅.
  The next CI run should advance further; watch for further clang-19 strict warnings and
  add matching `-Wno-` flags to `EXTRA_CMDS` (quoted!).
- Do NOT build with `-j8` on an 8G host (OOM); `-j2` only (from OP8 fork's hard-won lesson).

---

## Replay order (if kernel upstream moves and patches need regenerating)

```
0. Prereqs: kernel @ 1d2678a3548f; modules_and_devicetree @ oneplus/sm8250_t_13.1_op8
   (place its vendor/ at kernel's 2-level parent; copy its kernel/msm-4.19/techpack/{camera,display,video}
    over the empty gitlinks).
1. ReSukiSU: curl setup.sh | bash main  (registers drivers/kernelsu + Kconfig)
2. Patch/susfs_resukisu_oos_4.19.patch  (SUSFS + ReSukiSU inline hooks)
3. Droidspaces/oos_droidspaces.patch    (cgroup prefix + xt_qtaguid panic fix)
4. Baseband-guard: curl setup.sh | bash (non-GKI path, security_add_hooks_compat)
5. Patch/defconfig_oos.patch            (KSU/SUSFS/BBG/DroidSpaces configs)
6. Build: make CC=clang CLANG_TRIPLE=aarch64-linux-android- \
        KCFLAGS="-Wno-strict-prototypes ... -Wno-implicit-int ..." O=out ARCH=arm64 \
        vendor/kona-perf_defconfig  then  make -j2 ...
```

---

## Files in this archive

| File | Content |
|---|---|
| `0000-full-all-changes.patch` | full combined patch set (SUSFS+ReSukiSU + DroidSpaces + defconfig) |
| `0001-susfs-resukisu-oos-4.19.patch` | SUSFS v2.2.0 (4.19.157) + ReSukiSU inline hooks |
| `0001-defconfig-oos.patch` | KSU/SUSFS/BBG/DroidSpaces configs |
| `0001-droidspaces-oos.patch` | cgroup prefix + xt_qtaguid panic fix |
| `README.md` | this record |

Live (workflow-used) copies: `../Patch/` (susfs_resukisu_oos_4.19.patch, defconfig_oos.patch),
`../Droidspaces/` (oos_droidspaces.patch). BBG and ReSukiSU are fetched at build time.

---

## Key references
- [OnePlusOSS/android_kernel_oneplus_sm8250](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8250)
- [OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8250](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8250)
- [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd)
- [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) · [SuSFS](https://gitlab.com/simonpunk/susfs4ksu) ·
  [Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
- Reference (GKI-only, not applicable to OP8): [Numbersf/Action-Build](https://github.com/Numbersf/Action-Build)
