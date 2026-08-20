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
| `Patch/susfs_resukisu_oos_4.19.patch` | SUSFS v2.2.0 (4.19.157) + ReSukiSU inline hooks (7 hooks) | workflow step |
| `Patch/defconfig_oos.patch` | KSU/SUSFS/BBG/DroidSpaces Non-GKI configs | workflow step |
| `Droidspaces/oos_droidspaces.patch` | cgroup prefix + xt_qtaguid panic fix | workflow step |
| Baseband Guard | fetched at build time via `setup.sh` (non-GKI path) | workflow step |

> All OOS patches are generated against kernel commit `1d2678a3548f` (OOS13.1 final, 4.19.157-perf).

## SUSFS re-generation notes (OOS 4.19.157)

The OP8/LOS patch (4.19.325) does **not** apply cleanly to OOS (different namei/namespace layout).
The OOS patch is based on **JackA1ltman's generic 4.19 patch** which targets the older
`vfs_kern_mount` structure that OOS shares, then manually fixed for OOS:

- `fs/namespace.c`: OOS has an extra `CONFIG_OPLUS_SECURE_GUARD` include block → hunk#1 fixed manually
- `fs/notify/fdinfo.c`: OOS already had partial SUSFS signatures (3-arg show_fdinfo) → hunk#4 body fixed manually
- `drivers/input/input.c`: OOS has `OPLUS_FEATURE_SAUPWK` block → input hook placed accordingly
- `fs/read_write.c`: OOS has `OPLUS_FEATURE_IOMONITOR` block → sys_read hook adapted
- `fs/stat.c`: `ksu_handle_stat` added manually (SUSFS patch doesn't include it for OOS)

## Key settings (build-oneplus-8-los23-a16.yml)

- `KERNEL_SOURCE/Branch`: OnePlus OSS repo, `oneplus/sm8250_t_13.1_op8`
- `VENDOR_SOURCE/Branch`: `android_kernel_modules_and_devicetree_oneplus_sm8250`, `oneplus/sm8250_t_13.1_op8`
- `MERGE_CONFIG_FILES`: empty — OOS defconfig already embeds `CONFIG_OPLUS_SM8250_CHARGER` etc.
- `DEFCONFIG_NAME`: `vendor/kona-perf_defconfig`
- DTB: non-overlay build produces `kona-mtp.dtb` (device tree 19821); dtb.img built from it

## OOS vendor/devicetree layout

OnePlus official builds place the kernel so `arch/arm64/boot/dts/../../../../../../vendor` resolves.
In this workflow `device_kernel` sits at `$GITHUB_WORKSPACE/device_kernel`, so the 6-level-up target is
`$GITHUB_WORKSPACE/vendor`. `build-ready` clones the modules_and_devicetree repo and moves its `vendor/`
there, then verifies the critical symlinks resolve.

## Credits

[OnePlusOSS](https://github.com/OnePlusOSS) · [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) ·
[SuSFS](https://gitlab.com/simonpunk/susfs4ksu) · [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) ·
[Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard) ·
[JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd)
