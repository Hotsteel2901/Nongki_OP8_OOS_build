# ReSukiSU-SUSFS Kernel Patch Archive

内核: LineageOS 23.2 (sm8250/kona) 4.19.325-cip132
Base commit: 4238ee49a84b (techpack: audio: tfa98xx-v6: Prevent node being created twice)
内核源码: ~/android_kernel_oneplus_sm8250_official
生成时间: 2026-08-05, 工作树当时状态 (git status 见 0000 头部)
更新记录:
  - 2026-08-05: ReSukiSU 88dbc786 -> 058cdc93 (12 commits, 仅 x86_64/tracepoint/用户态变化, 集成未破坏)
  - 2026-08-05: SUSFS v2.1.0 -> v2.2.0 (官方 gki-android15-6.6@be7b7ef 最新, 2026-06-21 发布),
    构建 #6 Wed Aug 5 16:56:49 UTC 2026
  - 2026-08-05: 【修复】v2.2.0 首版开不了机(黄警告屏后黑屏, recovery 正常)。回退 fs/namei.c
    到原版 (构建 #7)。根因判断: 我移植的 namei.c 查找级 SUS_PATH 隐藏(stat/open 对
    sus 路径返回 ENOENT + 假 dentry)是相对 v2.1.0 的全新行为, 在带真实 sus 配置的
    system 启动中触发异常; v2.1.0/KSUN 从未有查找级隐藏(仅 readdir/proc 列表层),
    回退后行为与已验证的 v2.1.0 一致。fs/namei.c 保持原版, 不再做任何修改。
    附带说明: susfs.c 中 susfs_fake_qstr_name/susfs_open_redirect_spoof_do_sys_openat
    仍定义但无调用方(无害); OPEN_REDIRECT 实际重定向本来就不生效。
  - 2026-08-05: 【最终决定】回退整个 SUSFS 到 v2.1.0 (wagamy/KSUN 版本), 仅保留
    ReSukiSU 更新 (058cdc93)。v2.2.0 集成(含 namei 回退后的 #7 构建)在实机上
    依然黑屏无法开机, 未定位到根因(无 pstore 日志, 崩溃极早)。重建方式:
    KSUN_SUSFS 内核提交 ac5f7e57d3f1 提取全部 v2.1.0 susfs 文件 + 5 处 ReSukiSU
    适配(见下), 构建 #8 Wed Aug 5 18:50 UTC 2026, Image 54835216 B 与用户能正常
    开机的旧 2.1.0 构建字节数完全一致。v2.2.0 不再尝试。
    教训: 4.19 上只做"列表层隐藏"的 v2.1.0 是唯一验证可用的状态;
    v2.2.0 的所有新特性 (UID_SCHEME/open_redirect 重构/2e9 mnt_id/静态键化)
    对 4.19 收益低且引入了无法定位的开机崩溃。
  - 2026-08-06: 【v2.2.0 重做 - 按 JackA1ltman 实证方法】构建 #9 Wed Aug 6 16:57 UTC 2026。
    参考 NonGKI_Kernel_Build_2nd (github.com/JackA1ltman) 的通用 susfs_patch_to_4.19.patch
    (v2.2.0 for 4.19, 15+ 设备 Stable) 重做集成:
      - 直接应用其通用 4.19 补丁 (仅 namespace.c 两个 hunk + task_mmu pagemap hunk 手工修)
      - 关键 4.19 适配: set_nameidata() 里 p->state = 0 (此前黑屏的头号嫌疑!);
        AS_FLAGS_* 存 inode->i_state (非 GKI 的 i_mapping->flags);
        fsnotify 用旧 API (SUSFS_DECL_FSNOTIFY_OPS + m_free);
        namei 层 FUSE+O_CREAT 返回 -EACCES 防护
      - namespace.c: 同 IDA 2e9 (与他们的 LOS 构建一致, 独立 IDA 声明未使用已删);
        钩 vfs_create_mount (本树 fs_context 版, 唯一分配点)
      - 保留 ReSukiSU inline 钩子 (exec/open/read_write/stat/input/reboot/setresuid),
        补回 stat.c ksu_handle_stat + reboot.c + sys.c setresuid (其补丁不含)
      - 构建内存教训: 环境跑在手机本体 (8G), 必须 -j2, 严禁 -j8 (OOM 黑屏卡死)
    若此版仍黑屏: 回退 v2.1.0 包 (build #8 存档) 或按 0001 patch 重放 v2.1.0。
  - 2026-08-06: 【修复 KSU 用户态失效】构建 #9 能开机但管理器"工作中"为假: 授权数/模块数
    全 0, 无法授权。根因: 重建时从 v2.1.0 的 exec.c 做符号替换, 把
    `if (unlikely(!susfs_is_sdcard_android_data_decrypted))` (decrypted 默认 false → 恒真)
    错写成 `if (unlikely(!static_branch_unlikely(&susfs_is_sdcard_android_data_not_decrypted)))`
    (not_decrypted 默认 true → 恒假) -> ksu_handle_execveat 永不执行 -> KernelSU 核心
    exec 处理 (授权/ksud/escape_to_root) 全死。构建 #10 修复为官方 v2.2.0 分支:
    `if (static_branch_unlikely(&not_decrypted)) ksu_handle_execveat; else sucompat;`
    教训: 布尔→静态键替换时注意极性反转 (decrypted=false 与 not_decrypted=true 语义等价,
    不能机械加 !)。

本目录内容与重放顺序（若内核更新破坏集成，按此顺序恢复）:

## 0. 先解包源码（patch 外的外部依赖）
   - KernelSU-src-full.tar.gz      -> 内核根目录解出 KernelSU/ 目录（含 .git, ReSukiSU v4.1.0-058cdc93）
        git clone 自 https://github.com/ReSukiSU-Kernel/ReSukiSU（/tmp/opencode/ReSukiSU 备份）
   - Baseband-guard-src-full.tar.gz -> /root/Baseband-guard/（vc-teahouse/Baseband-guard，已修复 tracing/Makefile 中错误 obj-y += selinux.o）
   - scmversion.hotsteel           -> 复制为内核根 .scmversion（内容: -g4238ee49a84b-hotsteel，覆盖 setlocalversion）

## 1. resukisu-susfs/0001-resukisu-susfs.patch   (14910 行)
   ReSukiSU (CONFIG_KSU_SUSFS 模式) + SUSFS v2.2.0 (4.19, 当前版本)
   来源: 官方 gitlab gki 分支 v2.2.0 源码 + JackA1ltman (NonGKI_Kernel_Build_2nd)
         通用 susfs_patch_to_4.19.patch 的 4.19 适配 (i_state/旧 fsnotify/p->state=0)
   核心 4.19 适配 (勿覆盖):
     - fs/namei.c: set_nameidata() 中 p->state = 0 (必须!);
       lookup_fast/lookup_open/__lookup_slow 假 dentry + link_path_walk 拦截 +
       do_last/lookup_last 状态位 + FUSE+O_CREAT 返回 -EACCES 防护 + OPEN_REDIRECT
       重定向 (set_nameidata 3 参 + old_dfd != -1 守卫)
     - fs/susfs.c: 所有 AS_FLAGS_* 存 inode->i_state (4.19 实证, 非 GKI 的
       i_mapping->flags); fsnotify 用旧 API (SUSFS_DECL_FSNOTIFY_OPS + m_free +
       4.18 版本分支 fsnotify_add_inode_mark); sdcard 监听用 raw_file_name 字符串
     - fs/namespace.c: 同 IDA mnt_id_ida + ida_alloc_min(DEFAULT_KSU_MNT_ID=2e9);
       钩 vfs_create_mount (本树 fs_context 版为唯一分配点, 其 LOS 版钩 vfs_kern_mount);
       static_key susfs_is_sdcard_android_data_not_decrypted
   保留的 ReSukiSU inline 钩子 (其 syscall 法补丁不含, 必须手工补回):
     - fs/stat.c: newfstatat 直连 ksu_handle_stat (CONFIG_KSU 门控)
     - kernel/sys.c: __sys_setresuid 里 ksu_handle_setresuid
     - kernel/reboot.c: ksu_handle_sys_reboot 无条件调用
     - fs/exec.c: ksu_su_compat_enabled 静态键 + susfs_is_sdcard_android_data_not_decrypted
       静态键 (sucompat 选择)
     - fs/open.c / fs/read_write.c / drivers/input/input.c: v2.1.0 静态键形式沿用
   构建注意事项: 本环境跑在手机本体 (8G 内存), 只允许 make -j2 (严禁 -j8, 会 OOM)。

## 2. rekernel/0001-rekernel.patch   (593 行)
   Re:Kernel 集成 (drivers/rekernel/: rekernel.c 333行 + rekernel.h + Kconfig + Makefile,
   drivers/android/binder.c +113, kernel/signal.c +8)
   来源: ~/ReKernel-X/Integrate/patches.sh (须在内核根目录执行; 误从 ~ 执行会在 /root 产生 stray drivers/)
   备注: rekernel.c 的 cfg 全局改 static (与 techpack VL53L1 冲突); rekernel.h 补 include/linux/sched/jobctl.h
   defconfig 部分在 5. 的 patch 中 (CONFIG_REKERNEL=y, CONFIG_REKERNEL_NETWORK=n)

## 3. droidspaces/0001-droidspaces-cgroup-prefix.patch   (16 行)
   DroidSpaces: kernel/cgroup/cgroup.c cgroup_add_file 加前缀 (对 zygote 隐藏非 cgroup 项)
   来源: ~/Droidspaces-OSS/Documentation/Kernel-Configuration.md (Non-GKI 部分)
   defconfig Non-GKI 配置在 5. (SYSVIPC/POSIX_MQUEUE/PID_NS/IPC_NS/CGROUP_DEVICE/CGROUP_PIDS/
   CGROUP_NET_PRIO/DEVTMPFS/BRIDGE_NETFILTER/NF_TABLES/NETFILTER_XT_MATCH_ADDRTYPE/USER_NS;
   xt_qtaguid 补丁不适用 - 本树无此驱动)
   注意: defconfig 原有一行 "# CONFIG_PID_NS is not set" 需改为启用。

## 4. baseband-guard/0001-baseband-guard.patch   (77 行)
   Baseband-guard LSM 集成
   包含: security/Kconfig security/Makefile (security/baseband-guard -> /root/Baseband-guard symlink)
         security/selinux/Makefile (追加 sepatch.txt 内容, ifeq CONFIG_BBG BBG_USE_DEFINE_LSM)
         security/selinux/include/objsec.h (task_security_struct 加 bbg_cred 字段)
         security/selinux/include/bbg_tracing.h (symlink -> ../../baseband-guard/tracing/tracing.h)
   依赖: 第0步解包 Baseband-guard 到 /root/Baseband-guard (symlink 目标)
   注意: 本内核已 backport DEFINE_LSM, BBG 走 BBG_USE_DEFINE_LSM 模式,
         CONFIG_LSM 必须含 baseband_guard 否则 BBG Makefile abort。
   白名单分区 (baseband_guard.h allowlist): boot init_boot vendor_boot vendor_kernel_boot dtbo
         userdata cache metadata misc vbmeta vbmeta_system vbmeta_vendor recovery (+slot后缀+zram)

## 5. defconfig/0001-defconfig.patch   (46 行)
   arch/arm64/configs/vendor/kona-perf_defconfig 全部改动:
   CONFIG_KSU=y + CONFIG_KSU_SUSFS=y (全部 SUSFS 子选项), CONFIG_REKERNEL=y (NETWORK=n),
   Non-GKI DroidSpaces 配置, CONFIG_BBG=y, CONFIG_LSM="...,bpf,baseband_guard"

## 6. 全量参考
   0000-full-all-changes.patch: 全部改动合集 (排除 *.bak 备份文件), 适用于整体重放/对照

## 构建命令 (重放后)
   # 1) 合并配置 (必须含 oplus 片段, 否则 schgm-flash.c 编译失败)
   scripts/kconfig/merge_config.sh -m -O /root/kout \
     arch/arm64/configs/vendor/kona-perf_defconfig arch/arm64/configs/vendor/oplus.config
   cd /root/kout && make ARCH=arm64 CC=clang CLANG_TRIPLE=aarch64-linux-gnu- \
     CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
   # 2) 构建 (在内核根目录, O=/root/kout)
   make O=/root/kout ARCH=arm64 CC=clang CLANG_TRIPLE=aarch64-linux-gnu- \
     CROSS_COMPILE=aarch64-linux-gnu- \
     KCFLAGS="-Wno-visibility -Wno-incompatible-function-pointer-types -Wno-cast-function-type-strict -Wno-deprecated-non-prototype" \
     -j8
   # 3) 产物
   Image:  /root/kout/arch/arm64/boot/Image (54835216 B, v2.1.0)
   dtb:    cat kona.dtb kona-v2.dtb kona-v2.1.dtb > dtb.img (1428199 B, 与官方 DTB_SZ 一致)
   dtbo:   kona-{instantnoodle,instantnoodlep,kebab,lemonades}-overlay.dtbo

## AK3 打包要点 (参考 ~/success-ak3/ 两个可用包)
   anykernel.sh: do.devicecheck=0, BLOCK=boot, IS_SLOT_DEVICE=auto, dump_boot+write_boot
   dtb 命名为 dtb.img; tools 为 Magisk v30.7 arm64 (busybox/magiskboot/magiskpolicy)
   最终包: /root/ReSukiSU-kernel-instantnoodle.zip

## 验证快照
   build-config.kout               : /root/kout/.config (v2.2.0 Jack 版构建 #9)
   System.map.build9-v220-jack     : v2.2.0 Jack 方法构建 #9 (含 p->state=0/i_state 适配)
   System.map.build5-v210-resukiSU-new : v2.1.0 + ReSukiSU 058cdc93 构建 #8 (可开机兜底)
   System.map.build4-v220-nonamei  : v2.2.0 namei 回退版 (#7) - 开不了机, 留档
   System.map.build3-v220          : v2.2.0 首版 (构建 #6) - 开不了机, 留档
   System.map.build2-hotsteel      : 用户可正常开机的旧 v2.1.0 构建 (#4) 备份
   kernel.release: 4.19.325-cip132-st16-perf-g4238ee49a84b-hotsteel
   最终刷机包: /root/ReSukiSU-kernel-instantnoodle.zip (Image 54837264 B, v2.2.0)
   兜底包: 旧 v2.1.0 zip 已覆盖, 需要时按 0001 patch (v2.1.0 存档在 README 历史说明) 重建

## 参考仓库
   - gitlab.com/simonpunk/susfs4ksu : 官方仓库 (/tmp/opencode/susfs4ksu 本地 clone)
     kernel-4.19 分支冻结在 v1.5.5 (2025-02-23); v2.1.0=2026-03-20, v2.2.0=2026-06-21 (仅 gki 分支)
     v2.2.0 源码位于 gki-android15-6.6@be7b7ef (kernel_patches/fs/susfs.c 等 3 文件 + 50_add_susfs patch)
   - ~/android_kernel_oneplus_sm8250_KSUN_SUSFS : wagamy 的 v2.1.0 4.19 backport 参考 (同 base 4238ee49a84b,
     KernelSU-Next v3.1.0 + SUSFS v2.1.0, squash 提交 ac5f7e57d3f1; 注意其独立 IDA 方式已被 v2.2.0 废弃)
   - ~/ReSukiSU_DOC, ~/ReKernel-X, ~/Droidspaces-OSS, ~/Baseband-guard
