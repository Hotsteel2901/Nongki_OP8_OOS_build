# Nongki_OP8_OOS_build

为 **OnePlus 8 (instantnoodle, 4.19.157-perf+)** 的 **OxygenOS 13.1 (Android 13)** 内核提供自动化编译。
是 [NonGKI_Kernel_Build_OP8](https://github.com/Hotsteel2901/NonGKI_Kernel_Build_OP8) 的衍生版，把内核源从
LineageOS 23.2 (A16) 换成 **一加官方 OnePlus OSS 内核**。

## ⚠️ 与 LineageOS 版本的关键差异

一加 OSS 官方内核（`OnePlusOSS/android_kernel_oneplus_sm8250`，分支 `oneplus/sm8250_t_13.1_op8`，
`4.19.157`）是**更老的 4.19 结构**，且**内核里没有设备树**：

- `arch/arm64/boot/dts/vendor` 是指向 `../../../../../../vendor/qcom/proprietary/devicetree-4.19` 的 symlink
- 有 86+ 个 symlink 指向 `vendor/oplus/kernel/*`（充电、触控、oplus_performance、网络等）
- **这些需要从独立仓库获取：**
  `OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8250`（分支 `oneplus/sm8250_t_13.1_op8`）
- 工作流会 clone 该仓库并按官方布局放置，使 symlink 可解析

## 集成内容

| 组件 | 说明 |
|---|---|
| ReSukiSU | KernelSU 分支, CONFIG_KSU_SUSFS (inline hook) 模式 |
| SUSFS v2.2.0 | 针对 OOS 4.19.157 老结构重新生成（用 `vfs_kern_mount`，无 `ND_STATE`） |
| DroidSpaces | cgroup 前缀隐藏 + Non-GKI 配置 (含 USER_NS) |
| Baseband Guard | 非 GKI / pre-5.1 LSM 风格 (`security_add_hooks_compat`, 无 `DEFINE_LSM`) |

> **不集成 Re:Kernel**：OOS 13.1 自带 binder/冻结监控 **HANS**（`CONFIG_OPLUS_HANS=y`,
> `drivers/staging/android/hans.c`），已覆盖 Re:Kernel 的冻结管理功能，再集成反而冗余
> （且 Re:Kernel 的 `SIGNAL` 枚举与 `hans.h` 冲突）。

## 使用方法

1. **Fork 本仓库** 到你的 GitHub 账号
2. **Settings → Actions → General → Workflow permissions** 选择 `Read and write permissions`
3. 进入 **Actions** 页, 选择 `Build Kernel` 工作流, 点 **Run workflow** (或直接 push 触发)
4. 构建完成后下载 zip, 用 AnyKernel3 方式刷入
5. 刷入后通过 KernelSU Manager 验证

## 补丁说明 (Patches/)

| 文件 | 内容 | 应用时机 |
|---|---|---|
| `Patch/susfs_resukisu_oos_4.19.patch` | SUSFS v2.2.0 (4.19.157) + ReSukiSU inline 7 钩子 | 工作流步骤 |
| `Patch/defconfig_oos.patch` | KSU/SUSFS/BBG/DroidSpaces Non-GKI 配置 | 工作流步骤 |
| `Droidspaces/oos_droidspaces.patch` | cgroup 前缀 + xt_qtaguid panic 修复 | 工作流步骤 |
| Baseband Guard | 构建时 `setup.sh` 动态拉取（非 GKI 路径） | 工作流步骤 |

> 所有 OOS 补丁基于内核提交 `1d2678a3548f`（OOS13.1 最终版, 4.19.157-perf）生成。

## SUSFS 重新生成说明 (OOS 4.19.157)

OP8/LOS 项目的补丁（4.19.325）**无法干净应用到 OOS**（namei/namespace 布局不同）。
OOS 补丁基于 **JackA1ltman 的通用 4.19 补丁**（它针对 OOS 同款的旧 `vfs_kern_mount` 结构），
再针对 OOS 手工修复：

- `fs/namespace.c`: OOS 多了 `CONFIG_OPLUS_SECURE_GUARD` include 块 → hunk#1 手工修
- `fs/notify/fdinfo.c`: OOS 已有部分 SUSFS 签名（3参 show_fdinfo）→ hunk#4 函数体手工修
- `drivers/input/input.c`: OOS 有 `OPLUS_FEATURE_SAUPWK` 块 → input hook 相应放置
- `fs/read_write.c`: OOS 有 `OPLUS_FEATURE_IOMONITOR` 块 → sys_read hook 适配
- `fs/stat.c`: `ksu_handle_stat` 手工补（OOS 的 SUSFS 补丁不含它）

## 关键配置项 (build-oneplus-8-los23-a16.yml)

- `KERNEL_SOURCE/Branch`: 一加 OSS 官方仓库, `oneplus/sm8250_t_13.1_op8`
- `VENDOR_SOURCE/Branch`: `android_kernel_modules_and_devicetree_oneplus_sm8250`, `oneplus/sm8250_t_13.1_op8`
- `MERGE_CONFIG_FILES`: 空 — OOS defconfig 已内嵌 `CONFIG_OPLUS_SM8250_CHARGER` 等
- `DEFCONFIG_NAME`: `vendor/kona-perf_defconfig`
- DTB: 非 overlay 构建生成 `kona-mtp.dtb`（设备树 19821），由此构建 dtb.img

## OOS vendor/devicetree 布局

一加官方构建把内核放在某层级使 `arch/arm64/boot/dts/../../../../../../vendor` 能解析。
本工作流 `device_kernel` 位于 `$GITHUB_WORKSPACE/device_kernel`，其 6 层上级是
`$GITHUB_WORKSPACE`，故 `vendor` 放在 `$GITHUB_WORKSPACE/vendor`。
`build-ready` clone modules_and_devicetree 仓库并把 `vendor/` 移到该处，然后校验关键 symlink。

## 鸣谢

[OnePlusOSS](https://github.com/OnePlusOSS) · [ReSukiSU](https://github.com/ReSukiSU/ReSukiSU) ·
[SuSFS](https://gitlab.com/simonpunk/susfs4ksu) · [Re:Kernel](https://github.com/Sakion-Team/Re-Kernel) ·
[Droidspaces](https://github.com/ravindu644/Droidspaces-OSS) · [Baseband-guard](https://github.com/vc-teahouse/Baseband-guard) ·
[JackA1ltman/NonGKI_Kernel_Build_2nd](https://github.com/JackA1ltman/NonGKI_Kernel_Build_2nd)
