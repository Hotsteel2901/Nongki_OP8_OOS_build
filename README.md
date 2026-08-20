# NonGKI_Kernel_Build_OP8

Automated kernel build for **OnePlus 8 (instantnoodle, 4.19.325-cip132-st16)** with **LineageOS 23.2 (Android 16)**.
Formatted after [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) (sample branch).
Chinese docs: [README_cn.md](README_cn.md)

## Integrations
| Component | Note |
|---|---|
| ReSukiSU | KernelSU fork, CONFIG_KSU_SUSFS (inline hook) mode |
| SUSFS v2.2.0 | Official gki v2.2.0 + JackA1ltman's proven 4.19 adaptations (i_state flags / p->state=0 / legacy fsnotify API) |
| Re:Kernel | v8.5 (ReKernel-X), CONFIG_REKERNEL_NETWORK=n |
| DroidSpaces | cgroup prefix hiding + Non-GKI configs (incl. USER_NS) |
| Baseband Guard | partition write protection LSM |

## Usage
1. Fork this repo, enable **Actions** with `Read and write permissions`.
2. Run the `Build Kernel` workflow (or push to trigger).
3. Download the zip artifact and flash it via recovery (AnyKernel3 style).
4. Verify in KernelSU Manager: SUSFS version **2.2.0**, allowlist & modules working.

## Patches (Patches/)
| File | Content | Applied by |
|---|---|---|
| `Patch/susfs_patch_to_4.19.patch` | SUSFS v2.2.0 kernel-side code | patch-susfs action |
| `Patch/resukisu_inline_hooks.patch` | ReSukiSU inline hooks (7 hooks) | custom workflow step |
| `Rekernel/rekernel_extra.patch` | Re:Kernel (driver + binder + signal + registration) | patch-rekernel action |
| `Droidspaces/*` | droidspaces.config + 2 cocci scripts | patch-droidspaces action |

> All patches are generated against kernel commit `4238ee49a84b`; the workflow pins that commit (`git checkout 4238ee49a84b`).
> Regenerate patches after upstream changes:
> ```bash
> git diff <new-base> -- <susfs-files> > Patches/Patch/susfs_patch_to_4.19.patch
> ```

## Key settings (build-oneplus-8-los23-a16.yml)
- `KERNEL_SOURCE/Branch`: LineageOS official repo, `lineage-23.2`
- `MERGE_CONFIG_FILES: vendor/oplus.config` — **required** (schgm-flash.c needs CONFIG_OPLUS_SM8250_CHARGER)
- ReSukiSU stays **latest** (setup.sh git pull each run)
- dtb: custom step concatenates `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` → `dtb.img`; dtbo not packed (stock partition used)

## Deviations from Jack's original (intentional)
- `patch-no-kprobe` removed: its hook scripts target KSU v1.x bool hooks (incompatible with ReSukiSU inline); its selinuxfs static-symbol removal is skipped anyway (CONFIG_KALLSYMS_ALL=y)
- Only the 4.19 susfs patch is kept (fixed device kernel version)
- ReKernel integrated via patch (ReKernel-X v8.5) instead of his rekernel_patches.sh
- HOOK_METHOD kept but inert: ReSukiSU inline hooks come from resukisu_inline_hooks.patch

## Patch Record Archive (Patches/Archive/)

Complete patch records from local development:
- `0000-full-all-changes.patch` — full combined patch set
- `0001-resukisu-susfs.patch` — ReSukiSU+SUSFS v2.2.0 complete integration (namei/namespace/proc etc.)
- `0001-rekernel.patch` / `0001-droidspaces-cgroup-prefix.patch` / `0001-baseband-guard.patch` / `0001-defconfig.patch`
- `README-record.md` — development log (version history / known issues / build notes)

> Note: the workflows actually use the patches under `Patches/Patch/` and `Patches/Rekernel/`;
> `Archive/` is for record only and is not used in builds.

## Credits
[JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) · [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) · [SuSFS](https://gitlab.com/simonpunk/susfs4ksu) · [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) · [Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
