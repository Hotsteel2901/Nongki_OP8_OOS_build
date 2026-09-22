# Nongki_OP8_OOS_build

Automated kernel build for **OnePlus 8 (instantnoodle, 4.19.157-perf+)** with **OxygenOS 13.1 (Android 13)**.
A fork of [NonGKI_Kernel_Build_OP8](https://github.com/Hotsteel2901/NonGKI_Kernel_Build_OP8) re-targeted from
LineageOS 23.2 (A16) to the **OnePlus OSS official kernel (OnePlusOS)**.

## ⚠️ Key difference vs the LineageOS fork

The OnePlus OSS kernel (`OnePlusOSS/android_kernel_oneplus_sm8250`, branch `oneplus/sm8250_t_13.1_op8`,
`4.19.157`) is an **older 4.19 structure** and has **no device tree in-tree**:

- `arch/arm64/boot/dts/vendor` is a symlink → `../../../../../../vendor/qcom/proprietary/devicetree-4.19`
- 86+ symlinks point into `vendor/oplus/kernel/*` (charger, touchpanel, oplus_performance, network, ...)
- **These must be supplied from a separate repo:**
  `OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8250` (branch `oneplus/sm8250_t_13.1_op8`)
- The workflow clones that repo and places it so the symlinks resolve (see below).

## Integrations

| Component | Note |
|---|---|
| ReSukiSU | KernelSU fork, CONFIG_KSU_SUSFS (inline hook) mode |
| SUSFS v2.2.0 | Re-generated for OOS 4.19.157 old structure (uses `vfs_kern_mount`, no `ND_STATE`) |
| DroidSpaces | cgroup prefix hiding + Non-GKI configs (incl. USER_NS) |
| Baseband Guard | non-GKI / pre-5.1 LSM style (`security_add_hooks_compat`, no `DEFINE_LSM`) |

> Re:Kernel is **not** integrated: OOS 13.1 already ships its own binder/freeze monitor
> **HANS** (`CONFIG_OPLUS_HANS=y`, `drivers/staging/android/hans.c`), which covers the same
> freeze-management role, so Re:Kernel would be redundant (and its enum clashed with `hans.h`).

## Usage

1. Fork this repo, enable **Actions** with `Read and write permissions`.
2. Run the `Build Kernel` workflow (or push to trigger).
3. Download the zip artifact and flash via recovery (AnyKernel3 style).
4. Verify in KernelSU Manager.

## Patches (Patches/)

| File | Content | Applied by |
|---|---|---|
| `Patch/susfs_resukisu_oos_4.19.patch` | SUSFS v2.2.0 (4.19.157) + ReSukiSU inline hooks (all 7 required) | workflow step |
| `Patch/defconfig_oos.patch` | KSU/SUSFS/BBG/DroidSpaces Non-GKI configs | workflow step |
| `Droidspaces/oos_droidspaces.patch` | cgroup prefix + xt_qtaguid panic fix | workflow step |
| Baseband Guard | fetched at build time via `setup.sh` (non-GKI path) | workflow step |

> All OOS patches are generated against kernel commit `1d2678a3548f` (OOS13.1 final, 4.19.157-perf).

## Patch Record Archive (Patches/Archive/)

Complete dev record and re-generation guide (in English): `Patches/Archive/README.md`
- `0000-full-all-changes.patch` — full combined patch set (SUSFS+ReSukiSU + DroidSpaces + defconfig)
- `0001-susfs-resukisu-oos-4.19.patch` / `0001-defconfig-oos.patch` / `0001-droidspaces-oos.patch`
- Documents the non-obvious OOS facts (devicetree symlink depth, techpack from
  modules_and_devicetree, no Re:Kernel/HANS, clang-19 KCFLAGS quoting) and every
  build error + fix so the next person can pick up where we left off.

## SUSFS re-generation notes (OOS 4.19.157)

The OP8/LOS patch (4.19.325) does **not** apply cleanly to OOS (different namei/namespace layout).
The OOS patch is based on **JackA1ltman's generic 4.19 patch** which targets the older
`vfs_kern_mount` structure that OOS shares, then manually fixed for OOS:

- `fs/namespace.c`: OOS has an extra `CONFIG_OPLUS_SECURE_GUARD` include block → hunk#1 fixed manually
- `fs/notify/fdinfo.c`: OOS already had partial SUSFS signatures (3-arg show_fdinfo) → hunk#4 body fixed manually
- `drivers/input/input.c`: OOS has `OPLUS_FEATURE_SAUPWK` block → input hook placed accordingly
- `fs/read_write.c`: OOS has `OPLUS_FEATURE_IOMONITOR` block → sys_read hook adapted
- `fs/stat.c`: `ksu_handle_stat` + `ksu_handle_vfs_fstat` wired manually against OOS's
  `vfs_statx`/`vfs_fstatat` layout (both call sites carry `OPLUS_FEATURE_*` neighbours)
- `fs/namei.c` + `include/linux/namei.h`: OOS's `filename_lookup` is `static`, so it is
  de-static'd and declared in the header — ReSukiSU's `struct filename **` signatures need it
- `fs/exec.c`: `susfs_is_current_proc_no_su()` guard for the execveat hook

## Key settings (build-oneplus-8-oos13.1.yml)

- `KERNEL_SOURCE/Branch`: OnePlus OSS repo, `oneplus/sm8250_t_13.1_op8`
- `VENDOR_SOURCE/Branch`: `android_kernel_modules_and_devicetree_oneplus_sm8250`, `oneplus/sm8250_t_13.1_op8`
- `MERGE_CONFIG_FILES`: empty — OOS defconfig already embeds `CONFIG_OPLUS_SM8250_CHARGER` etc.
- `DEFCONFIG_NAME`: `vendor/kona-perf_defconfig`
- DTB: non-overlay build produces `kona-mtp.dtb` (device tree 19821); dtb.img built from it

## OOS vendor/devicetree layout

OnePlus official builds place the kernel so `arch/arm64/boot/dts/../../../../../../vendor` resolves.
In this workflow the kernel sits at `$GITHUB_WORKSPACE/kernel/msm-4.19`, so the 6-level-up target is
`$GITHUB_WORKSPACE/vendor`. `build-ready` clones the modules_and_devicetree repo, moves its `vendor/`
there, copies its `kernel/msm-4.19/techpack/{camera,display,video}` over the kernel's empty gitlinks,
then verifies the critical symlinks resolve.

Two layout-dependent fixups run before the build:

- **charger include depth** (`Bin/fix_oos_vendor.py`) — the shipped oplus charger drivers include
  kernel headers with four `../`. From `vendor/oplus/kernel/charger/charger_ic/` to the kernel at
  `$GITHUB_WORKSPACE/kernel/msm-4.19` the real distance is five, so four resolves to a
  non-existent `$GITHUB_WORKSPACE/vendor/kernel/msm-4.19` and `oplus_battery_msm8250.c`
  (the driver OP8 actually builds) fails to compile.
- **OPLUS_FEATURE_* gates** (`Bin/fix_oplus_feature_gates.py`) — the top Makefile `-include`s
  `oplus_native_features.mk`, which sets ~230 `OPLUS_FEATURE_*` with plain assignments. Plain
  assignments do not reach kbuild's per-directory sub-makes, so every `$(OPLUS_FEATURE_*)` gate in
  a sub-Makefile evaluated false. `OplusKernelEnvConfig.mk` only compensates for *compiler macros*
  (`-D...`), so `#ifdef` worked in C while Makefile gates silently dropped their objects. The
  script appends one `export` line per required gate to `oplus_native_features.mk` itself, so the
  assignment and the export can never drift apart.

  On OP8 this was a hard link failure, because the *callers* compiled in (their `CONFIG_*`
  prerequisites are `=y`) while the *definitions* were dropped:

  | Dropped object | Undefined symbols | Called from |
  |---|---|---|
  | `drivers/scsi/ufs/ufsfeature.o` | `ufsf_*` (~20), `recordUniproErr`, `io_latency_hist_show` | `ufshcd.c`, `ufs-sysfs.c` |
  | `mm/process_mm_reclaim.o` | `is_reclaim_should_cancel` | `mm/vmscan.c:1231` |
  | `mm/task_mem/` | `update_user_tasklist` | `kernel/fork.c:2326` |
  | `net/oplus_router_boost/` | — (silent feature loss) | — |
  | `techpack/display/oplus/oplus_adfr.o` | — (silent feature loss) | — |

## Credits

[OnePlusOSS](https://github.com/OnePlusOSS) · [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) ·
[SuSFS](https://gitlab.com/simonpunk/susfs4ksu) · [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) ·
[Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard) ·
[JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd)
