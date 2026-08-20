# NonGKI_Kernel_Build_OP8

基于 [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) 的 sample 分支格式，
为 **OnePlus 8 (instantnoodle, 4.19.325-cip132-st16)** 的 **LineageOS 23.2 (Android 16)** 内核提供自动化编译。

## 集成内容

| 组件 | 说明 |
|---|---|
| ReSukiSU | KernelSU 分支, CONFIG_KSU_SUSFS (inline hook) 模式 |
| SUSFS v2.2.0 | 官方 gki v2.2.0 + JackA1ltman 实证的 4.19 适配 (i_state 标志位 / p->state=0 / 旧 fsnotify API) |
| Re:Kernel | v8.5 (ReKernel-X), CONFIG_REKERNEL_NETWORK=n |
| DroidSpaces | cgroup 前缀隐藏 + Non-GKI 配置 (含 USER_NS) |
| Baseband Guard | 分区写保护 LSM |

## 使用方法

1. **Fork 本仓库** 到你自己的 GitHub 账号
2. **Settings → Actions → General → Workflow permissions** 选择 `Read and write permissions`
3. 进入 **Actions** 页, 选择 `Build Kernel` 工作流, 点 **Run workflow** (或直接 push 触发)
4. 构建完成后在 **Actions → 本次运行 → Artifacts** 下载 zip, 用 AnyKernel3 方式刷入:
   - 重启到 recovery (fastboot boot recovery 或按键进入)
   - Apply update → 选择下载的 zip
   - 或 `adb sideload xxx.zip`
5. 刷入后通过 KernelSU Manager 验证: 版本显示 **SUSFS 2.2.0**, 授权/模块功能正常.

## 补丁说明 (Patches/)

| 文件 | 内容 | 应用时机 |
|---|---|---|
| `Patches/Patch/susfs_patch_to_4.19.patch` | SUSFS v2.2.0 全部内核侧代码 (susfs.c/namei/namespace/proc/statfs/mm/kallsyms/avc/cmdline 等) | patch-susfs 动作 |
| `Patches/Patch/resukisu_inline_hooks.patch` | ReSukiSU inline 模式必需的 7 个钩子 (exec/open/read_write/stat/input/reboot/setresuid) | 工作流自定义步骤 |
| `Patches/Rekernel/rekernel_extra.patch` | Re:Kernel (drivers/rekernel/ + binder + signal + Kconfig/Makefile 注册) | patch-rekernel 动作 |
| `Patches/Droidspaces/*` | droidspaces.config (配置) + cgroup 前缀 cocci + xt_qtaguid panic 修复 cocci | patch-droidspaces 动作 |

> 注意: 所有补丁基于内核提交 **`4238ee49a84b`** 生成。工作流会自动 `git checkout 4238ee49a84b`
> 固定该提交以保证补丁干净应用。若 LineageOS 上游有重大更新导致补丁失败, 请基于新提交重新生成补丁:
> ```bash
> git diff <新base> -- <susfs相关文件> > Patches/Patch/susfs_patch_to_4.19.patch
> ```

## 关键配置项 (build-oneplus-8-los23-a16.yml)

- `KERNEL_SOURCE/Branch`: LineageOS 官方仓库 `lineage-23.2`
- `MERGE_CONFIG_FILES: vendor/oplus.config` — **必须保留** (schgm-flash.c 需要 CONFIG_OPLUS_SM8250_CHARGER)
- `KERNELSU_AUTO_FORK: resukisu` — 自动获取最新 ReSukiSU
- dtb: 构建后自定义步骤拼接 `kona.dtb + kona-v2.dtb + kona-v2.1.dtb` → `dtb.img` (与官方 DTB_SZ 一致)
- dtbo: 不打包 (NEED_DTBO=false, 沿用系统分区的 dtbo)

## 与 Jack 原版格式的差异（有意为之）

- `patch-no-kprobe` 步骤/动作已移除: 其 `susfs_inline_hook_patches.sh` 面向 KSU v1.x
  bool 钩子与旧版 selinux 修改, 与 ReSukiSU inline 模式不兼容 (seccomp filter_count
  在 4.19 上由 kernel_compat.mk 条件编译排除, 无需补丁); 其 selinuxfs 静态符号移除
  部分因本内核 CONFIG_KALLSYMS_ALL=y 而跳过, 无实际作用
- 仅保留 4.19 版本的 susfs 补丁 (设备内核版本固定, 无需 4.4/4.9/5.4 等)
- ReKernel 直接用补丁集成 (ReKernel-X v8.5), 不使用其 rekernel_patches.sh 脚本
- HOOK_METHOD 变量保留但无实际作用: ReSukiSU inline 钩子由 resukisu_inline_hooks.patch 提供

## 补丁记录存档 (Patches/Archive/)

开发过程中的完整补丁记录: `0000-full-all-changes.patch` (全量合集)、
`0001-resukisu-susfs.patch` (ReSukiSU+SUSFS v2.2.0 完整集成)、
`0001-rekernel.patch` / `0001-droidspaces-cgroup-prefix.patch` /
`0001-baseband-guard.patch` / `0001-defconfig.patch` 及 `README.md` (开发记录)。
工作流实际使用 `Patches/Patch/` 与 `Patches/Rekernel/`, Archive 仅存档。

## 已知限制

- 构建需要 x86_64 环境 (GitHub Actions 默认 runner 即可)
- SUSFS v2.2.0 的 OPEN_REDIRECT 实际重定向在 4.19 上不生效 (架构限制, 与官方一致)
- 若使用本地构建 (非 GitHub Actions), 内存 ≥ 8G 且用 `make -j2` (手机本体构建严禁 -j8)

## 鸣谢

- [JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd) — 项目格式与 4.19 移植方法
- [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) / [SuSFS](https://gitlab.com/simonpunk/susfs4ksu) / [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) / [Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) / [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
