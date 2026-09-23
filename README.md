# Kodi 系统工具箱 (plugin.program.systemtools)

专为 Kodi (Matrix 19 / Nexus 20 / Omega 21 / Piers 22) 及各类嵌入式机顶盒系统（CoreELEC、LibreELEC、Android、外贸电视盒子、Linux、Windows）设计的全功能系统工具箱插件。

## 主要功能

### 1. CoreELEC 多版本管理与切换 (CoreELEC Version Switcher)
- **从 .tar 升级包导入新版本**：支持选择任意版本的 CoreELEC `.tar` 升级包（如不同大版本、测试版、Nightly 构建等），纯 Python `tarfile` 流式解包自动提取 `KERNEL.img`、`SYSTEM` (SquashFS) 及对应 MD5 校验文件。
- **解包后按需删除原始 TAR 文件**：解包提取完成后，弹窗询问是否删除原始 `.tar` 安装包（释放约 250MB~350MB 存储空间，亦可在设置中开启自动删除），防止重复占用宝贵磁盘空间。
- **持久化版本池 (/storage/.ce_versions/)**：版本池存储在容量充足的 ext4 数据分区，彻底避免 `/flash` FAT 引导分区（通常仅 512MB）因多镜像存储而溢出损坏。
- **配置隔离与开机自动恢复**：各版本独立保存配套的 `guisettings.xml`。通过 `/storage/.config/autostart.sh` 开机钩子，在系统引导、Kodi 启动前精准还原对应版本的设置；切换时使用 `sync && reboot -f` 极速重启，避免 Kodi 退出时内存设置反向覆盖目标配置。
- **当前系统一键备份**：支持将当前正在运行的 `/flash` 镜像与 Kodi 运行配置备份为新的独立版本槽位，随时可一键回退。
- **已保存版本管理**：随时查看所有版本、一键切换已保存版本、或删除不需要的历史版本释放存储空间。
- **系统电源管理**：支持一键重启切换至内置 Android 系统、常规重启与关机。

### 2. 全协议视频流测速与网络测速 (Network Speed Test)
- **局域网 / 网盘全协议测速**：
  - 基于 Kodi 原生 `xbmcvfs`，全面覆盖 `smb://`、`nfs://`、`webdav://`、`dav://`、`http://`、`https://`、`ftp://` 及本地挂载路径。
  - 选择任意大文件视频（建议 ≥1GB），采用 1MB 分块读取，**随读随弃，零内存缓存**。
  - 引入 **前 2 秒传输连接稳定期机制**，排除建立握手初期的低速波动，精准统计稳定期后的最高速度、最低速度。
  - 智能计算 **网络稳定度 (Stability Rate)**，提供 4K 蓝光原盘流畅度评级（卡顿风险预警 / 蓝光全速评估）。
  - 测速完成后自动调用垃圾回收与 Kodi 缓存清理 (`ClearCache`)。
- **互联网外网宽带测速**：
  - 测试 TCP 延迟 (Ping)、公网 CDN 多线程下载带宽与上传带宽。

### 3. 存储读写测速 (Disk Benchmark)
- 支持测试机顶盒内置存储 (eMMC)、SD 卡、U盘、外置移动硬盘或 NAS 挂载路径。
- **顺序写入与读取** (MB/s)。
- **4K 随机写入与读取** (MB/s 及 IOPS 吞吐量)。
- 强制同步 (`fsync` / `O_SYNC` / `O_BINARY`) 避免系统缓存误报真实磁盘性能。
- 退出与异常时通过 `finally` 安全自动清理临时测试文件。

### 4. 系统网络配置 (Network Configuration)
- 查看网卡接口（eth0、wlan0）、当前 IP、子网掩码、网关、DNS。
- 支持一键切换 DHCP 自动获取或配置静态 IP / 网关 / DNS。
- 针对 CoreELEC / LibreELEC 的 ConnMan 服务及通用 Linux `ip` 指令无缝集成。

### 5. Kodi 日志管理与一键清理 (Kodi Log Cleaner)
- 自动定位 Kodi 日志目录 (`special://logpath/`)。
- 一键查看最近运行日志 (Tail Viewer)。
- 一键清空 `kodi.log`，清理 `kodi.old.log` 及崩溃日志 (`kodi_crashlog*`)。
- 支持清理前自动备份 (`.bak`)。

---

## 安装与打包

### 打包为 Kodi 安装包 (ZIP)
```bash
python scripts/package.py
```
生成安装包位于 `dist/plugin.program.systemtools-1.0.0.zip`。

### 在 Kodi 中安装
1. 打开 Kodi -> **设置 (Settings)** -> **插件 (Add-ons)**。
2. 开启 **未知来源 (Unknown sources)**。
3. 选择 **从 Zip 文件安装 (Install from zip file)**。
4. 浏览并选择 `dist/plugin.program.systemtools-1.0.0.zip` 即可完成安装。

---

## 开发者指令

### 安装开发依赖
```bash
pip install -r requirements-dev.txt
```

### 运行单元测试
```bash
python -m pytest tests/
```

### 运行单项测试
```bash
python -m pytest tests/test_os_switcher.py
python -m pytest tests/test_net_speedtest.py
```

### 运行测试覆盖率
```bash
python -m pytest --cov=resources.lib tests/
```

### 代码检查
```bash
flake8 resources/ addon.py tests/
```
