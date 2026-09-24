# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Testing
Run all tests:
```bash
python -m pytest tests/
```

Run a single test file:
```bash
python -m pytest tests/test_os_switcher.py
python -m pytest tests/test_net_speedtest.py
python -m pytest tests/test_disk_benchmark.py
```

Run a specific test function:
```bash
python -m pytest tests/test_os_switcher.py::test_os_switcher_tar_unpack_and_version_pool
```

Run tests with test coverage:
```bash
python -m pytest --cov=resources.lib tests/
```

### Packaging & Build
Package the addon into an installable Kodi ZIP (`dist/plugin.program.systemtools-<version>.zip`):
```bash
python scripts/package.py
```

Generate 512x512 icon and 1280x720 fanart assets:
```bash
python scripts/generate_icon.py
python scripts/generate_fanart.py
```

### Linting
```bash
flake8 resources/ addon.py tests/
```

### Development Dependencies
```bash
pip install -r requirements-dev.txt
```

---

## Architecture & Code Structure

This project is a Kodi Program Add-on (`plugin.program.systemtools`) targeted at Kodi 19+ (Matrix, Nexus, Omega, Piers) running Python 3 (`xbmc.python >= 3.0.0`). It is optimized for CoreELEC and LibreELEC television box platforms (Amlogic, Rockchip, etc.) as well as Android, Linux, and Windows.

### 1. Execution Flow & Routing
- [addon.py](addon.py): Main Kodi plugin entry point. Prepares `sys.path` and passes `sys.argv` (`[base_url, handle, param_string]`) to `router.route()`.
- [resources/lib/router.py](resources/lib/router.py):
  - When no action is present in URL params: Renders Kodi program menu items using `xbmcplugin.addDirectoryItem()` and closes directory with `xbmcplugin.endOfDirectory()`.
  - When an action is provided (e.g., `?action=os_switch`): Dispatches execution to the corresponding tool via `ToolRegistry.dispatch(action, params)`.

### 2. Modular Tool Registry
All tools inherit from `BaseTool` in [resources/lib/tools/base_tool.py](resources/lib/tools/base_tool.py) and register via `@ToolRegistry.register`:
- `id`: Action identifier matched against URL query string (`?action=<id>`).
- `title_id` & `description_id`: Localization string IDs referencing `strings.po`.
- `icon`: Kodi system icon or resource icon.
- `order`: Display order in the Kodi menu list.
- `run(params)`: Primary entry method for tool execution.

To add a new tool:
1. Create a new module in [resources/lib/tools/](resources/lib/tools/).
2. Define a class inheriting `BaseTool` decorated with `@ToolRegistry.register`.
3. Add corresponding localized strings to `strings.po`.
4. Export the class in [resources/lib/tools/__init__.py](resources/lib/tools/__init__.py).

### 3. Core Modules
- [resources/lib/tools/os_switcher.py](resources/lib/tools/os_switcher.py):
  - **CoreELEC Multi-version Management**:
    - Unpacks CoreELEC `.tar` update archives (releases, test builds, nightlies) using `tarfile` to extract `KERNEL.img`, `SYSTEM`, and checksums.
    - Prompts to delete the source `.tar` archive upon successful extraction to free disk space (or auto-deletes if enabled in settings).
    - Maintains a version pool in `/storage/.ce_versions/<version_name>/` on the ext4 partition, preventing `/flash` FAT partition space exhaustion.
    - Isolates version settings by storing and restoring `guisettings.xml` per version.
    - Injects startup hook in `/storage/.config/autostart.sh` to restore `guisettings.xml` prior to Kodi start, bypassing memory-flush overwrites on exit.
    - Supports backup of the current live `/flash` system to a new version slot.
    - Supports deletion of non-active version slots.
    - Remounts `/flash` read-write (`mount -o remount,rw /flash`), syncs disk, and reboots (`reboot -f`).
    - Respects DTB auto-update protection setting: never overwrites `/flash/dtb.img` if protection is active.
- [resources/lib/tools/dtb_tool.py](resources/lib/tools/dtb_tool.py):
  - **DTB Auto-Update Protection & Management**:
    - Manages `/storage/.config/dtb-autoupdate.conf` (`ENABLE=no` to lock DTB against overwrite on tar upgrades).
    - Backs up current running `/flash/dtb.img` to `/storage/.config/custom_dtb.img`.
    - Restores custom DTB backup back to `/flash/dtb.img`.
    - Reads hardware device tree model from `/proc/device-tree/model`.
- [resources/lib/tools/ram_cleaner.py](resources/lib/tools/ram_cleaner.py):
  - **One-Click System RAM & Cache Cleaner**:
    - Flushes dirty blocks with `sync`, drops pagecache/dentries/inodes via `/proc/sys/vm/drop_caches` (`echo 3 > ...`).
    - Purges Kodi internal texture/stream caches with `ClearCache` and runs Python `gc.collect()`.
    - Reads `/proc/meminfo` to display memory stats and amount of RAM freed.
- [resources/lib/tools/kodi_optimizer.py](resources/lib/tools/kodi_optimizer.py):
  - **Kodi Database & Mali GPU Rendering Optimizer**:
    - Configures SQLite databases with `PRAGMA journal_mode = WAL` and `PRAGMA synchronous = NORMAL` for non-blocking concurrent reads/writes on large media libraries.
    - Tunes `advancedsettings.xml` (`asynctextureupload=false`, `minifiedmipmapping=false`, `algorithmdirtyregions=2`, `imageres=540`, `fanartres=720`, `cache_size=-32768`) to eliminate EGL driver stalls and GPU dropped frames.
    - Creates `.bak` backups before modifying files and provides one-click restoration.
- [resources/lib/tools/net_speedtest.py](resources/lib/tools/net_speedtest.py):
  - **LAN & Cloud Drive Video Stream Benchmark**: Reads files over `smb://`, `nfs://`, `webdav://`, `dav://`, `http://`, `https://`, `ftp://`, and local mounts using `xbmcvfs.File`. 1MB chunked reading with zero memory retention. Features a 2-second stabilization period, tracking real-time MB/s, Mbps, max/min speeds, and network stability rate `(min_speed / max_speed) * 100%`, with 4K Blu-ray streaming ratings. Runs `gc.collect()` and `ClearCache` on exit.
  - **Internet WAN Speed Test**: Measures public TCP DNS ping latency, CDN download, and upload throughput.
- [resources/lib/tools/disk_benchmark.py](resources/lib/tools/disk_benchmark.py): Storage benchmarking with sequential read/write (1MB chunks) and 4K random read/write (4096-byte blocks with IOPS calculation) using `os.open` (`O_BINARY`) and `os.fsync`. Cleans up temp test file in `finally` block.
- [resources/lib/tools/net_config.py](resources/lib/tools/net_config.py): Views interface status (IP, mask, gateway, DNS), configures DHCP or static network parameters via `connmanctl` (CoreELEC/LibreELEC) or Linux `ip`/`route` commands.
- [resources/lib/tools/log_cleaner.py](resources/lib/tools/log_cleaner.py): Discovers logs in `special://logpath/`, provides log tail viewer, truncate/clear for `kodi.log`, removal of `kodi.old.log` and crashlogs, with optional backup before truncation.

### 4. Hardware & Kodi Abstraction Layer
- [resources/lib/common/kodi_ui.py](resources/lib/common/kodi_ui.py): Wrapper functions for `xbmcgui.Dialog`, progress dialog context manager, localized string lookup (`get_string`), and settings access.
- [resources/lib/common/os_detect.py](resources/lib/common/os_detect.py): Detects CoreELEC, LibreELEC, Android, Linux, Windows, macOS, and identifies SoC hardware (Amlogic, Rockchip, Allwinner, Raspberry Pi).
- [resources/lib/common/system_exec.py](resources/lib/common/system_exec.py): Subprocess execution with timeout handling and platform-specific reboot mechanisms.
- [resources/lib/common/logger.py](resources/lib/common/logger.py): Logs through `xbmc.log` when inside Kodi, falls back to `sys.stderr` outside Kodi.

### 5. Kodi Mocking & Testing
- [tests/conftest.py](tests/conftest.py): Mocks `xbmc`, `xbmcgui`, `xbmcaddon`, `xbmcvfs`, and `xbmcplugin` into `sys.modules`. Includes realistic file-reading VFS mock so tests can run in pure Python without Kodi installed.

### 6. Internationalization
- Language files are GNU Gettext PO format in [resources/language/resource.language.en_gb/strings.po](resources/language/resource.language.en_gb/strings.po) and [resources/language/resource.language.zh_cn/strings.po](resources/language/resource.language.zh_cn/strings.po). String IDs use numeric range 30000+.
