# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Testing
```bash
# Run all unit tests
python -m pytest tests/

# Run a single test file or specific test
python -m pytest tests/test_kodi_optimizer.py
python -m pytest tests/test_kodi_optimizer.py::test_optimize_databases

# Run tests with coverage
python -m pytest --cov=resources.lib tests/
```

### Linting & Packaging
```bash
# Code style check
flake8 resources/ addon.py tests/

# Package addon into dist/ ZIP
python scripts/package.py

# Generate icon and fanart assets
python scripts/generate_icon.py
python scripts/generate_fanart.py
```

---

## Architecture & Development Conventions

This project is a Kodi Program Add-on (`plugin.program.systemtools`) targeted at Kodi 19+ (Matrix, Nexus, Omega, Piers) running Python 3 (`xbmc.python >= 3.0.0`). It supports embedded Linux (CoreELEC, LibreELEC on Amlogic, Rockchip, Allwinner) as well as Android, Linux, Windows, and macOS.

### 1. Execution Flow & Routing
- [addon.py](addon.py): Kodi entry point. Configures `sys.path` and dispatches `sys.argv` to [resources/lib/router.py](resources/lib/router.py).
- [resources/lib/router.py](resources/lib/router.py):
  - Without action parameter: Dynamically builds the main menu directory from registered tools and calls `xbmcplugin.endOfDirectory()`.
  - With action parameter (`?action=<tool_id>`): Dispatches to `ToolRegistry.dispatch(action, params)`.

### 2. Modular Tool Pattern ([resources/lib/tools/](resources/lib/tools/))
All functional modules are independent tools subclassing `BaseTool` in [resources/lib/tools/base_tool.py](resources/lib/tools/base_tool.py):
- Register using `@ToolRegistry.register(id=..., title_id=..., description_id=..., icon=..., order=...)`.
- Implement `run(params)` as the main execution entry.
- Export new tools in [resources/lib/tools/__init__.py](resources/lib/tools/__init__.py) to ensure they are loaded and registered.

### 3. Common Utilities ([resources/lib/common/](resources/lib/common/))
- [kodi_ui.py](resources/lib/common/kodi_ui.py): Wrapper for `xbmcgui.Dialog`, progress dialog context manager, localized string lookup (`get_string`), and addon settings.
- [os_detect.py](resources/lib/common/os_detect.py): Platform and SoC hardware detection (Amlogic, Rockchip, Allwinner, Raspberry Pi, etc.).
- [system_exec.py](resources/lib/common/system_exec.py): Subprocess execution with timeout handling and platform reboot mechanisms.
- [logger.py](resources/lib/common/logger.py): Unified logger (`xbmc.log` in Kodi, fallback to `sys.stderr` outside Kodi).

### 4. Testing & Mocks ([tests/conftest.py](tests/conftest.py))
- Kodi APIs (`xbmc`, `xbmcgui`, `xbmcaddon`, `xbmcvfs`, `xbmcplugin`) are fully mocked in [tests/conftest.py](tests/conftest.py), allowing all unit tests to run in a standard Python environment without Kodi installed.

### 5. Internationalization (i18n)
- GNU Gettext PO files are located in [resources/language/resource.language.en_gb/strings.po](resources/language/resource.language.en_gb/strings.po) and [resources/language/resource.language.zh_cn/strings.po](resources/language/resource.language.zh_cn/strings.po).
- String IDs use numeric range `30000+`.
- Zero hardcoded user-facing strings: all UI text must use `get_string(string_id)`.
