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

This build is **stock** — no root (KernelSU/ReSukiSU) or SUSFS. Only these are integrated:

| Component | Note |
|---|---|
| DroidSpaces | cgroup prefix hiding + Non-GKI configs (incl. USER_NS) |
| Baseband Guard | non-GKI / pre-5.1 LSM style (`security_add_hooks_compat`, no `DEFINE_LSM`) |

> Re:Kernel is **not** integrated: OOS 13.1 already ships its own binder/freeze monitor
> **HANS** (`CONFIG_OPLUS_HANS=y`, `drivers/staging/android/hans.c`), which covers the same
> freeze-management role, so Re:Kernel would be redundant (and its enum clashed with `hans.h`).

## Usage

1. Fork this repo, enable **Actions** with `Read and write permissions`.
2. Run the `Build Kernel` workflow (or push to trigger).
3. Download the zip artifact and flash via recovery (AnyKernel3 style).

## Patches (Patches/)

| File | Content | Applied by |
|---|---|---|
| `Patch/defconfig_oos.patch` | BBG/DroidSpaces Non-GKI configs | workflow step |
| `Droidspaces/oos_droidspaces.patch` | cgroup prefix + xt_qtaguid panic fix | workflow step |
| Baseband Guard | fetched at build time via `setup.sh` (non-GKI path) | workflow step |

> All OOS patches are generated against kernel commit `1d2678a3548f` (OOS13.1 final, 4.19.157-perf).

## Patch Record Archive (Patches/Archive/)

Complete dev record and re-generation guide (in English): `Patches/Archive/README.md`
- `0001-defconfig-oos.patch` / `0001-droidspaces-oos.patch`
- Documents the non-obvious OOS facts (devicetree symlink depth, techpack from
  modules_and_devicetree, no Re:Kernel/HANS, clang-19 KCFLAGS quoting) and every
  build error + fix so the next person can pick up where we left off.
- Note: this archive predates the stock (no-root) switch and still documents the
  now-removed SUSFS+ReSukiSU work for history; see `Patches/Archive/README.md`.

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

[OnePlusOSS](https://github.com/OnePlusOSS) · [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) ·
[Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard) ·
[JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd)
