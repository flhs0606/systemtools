# 全皮肤兼容统一 UI 架构实施计划 (Skin-Independent UI Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将插件主菜单交互重构为 100% 皮肤无关的原生详细选择对话框，结合容器生命周期管理、独立副标题文案与安全调用通知，彻底解决第三方皮肤下调不出界面的问题。

**Architecture:** 主菜单调度全面解耦对皮肤媒体窗口（`MyPrograms.xml`）的依赖。当从 Kodi 程序列表启动时（`handle >= 0`）以 `endOfDirectory(succeeded=False)` 立即安全关闭容器防止卡死等待；随后通过 `xbmcgui.Dialog().select(useDetails=True)` 弹出包含独立图标、标题与功能说明副标题的交互菜单，支持操作完成后自动重显菜单与返回键退出。

**Tech Stack:** Python 3 (`xbmc.python >= 3.0.0`), Kodi API (`xbmc`, `xbmcgui`, `xbmcplugin`), pytest.

**Spec:** [docs/superpowers/specs/2026-09-25-skin-independent-ui-enhancement-design.md](docs/superpowers/specs/2026-09-25-skin-independent-ui-enhancement-design.md)

## Global Constraints

- 目标平台兼容 Kodi 19+ (Matrix, Nexus, Omega, Piers) 与 Python 3。
- UI 交互统一使用 Kodi 核心原生详细对话框，保持单一极简设计，不引入复杂外置窗口。
- 零硬编码用户可见文本，所有提示使用 `get_string(string_id)`。
- 遵循原有架构规范：工具继承 `BaseTool` 并通过 `ToolRegistry` 管理，不破坏既有工具签名。

## Review Focus

1. **容器句柄为 -1 时的无容器启动**（来自收藏夹、快捷键）：不能触发 `xbmcplugin.endOfDirectory` 异常，应直接弹出主菜单。
2. **Kodi 18/早期环境不支持 `useDetails` 关键字参数**：`dialog_select_details` 捕获 `TypeError` 并无缝回退到普通 `select`。
3. **工具执行抛出未捕获异常**：`run_tool` 捕获所有 Exception，记录堆栈到日志并弹窗通知，避免界面静默死掉。
4. **用户在主菜单按返回键取消（choice == -1）**：主菜单循环必须安全退出，不能进入死循环。
5. **XML 约束解析**：`resources/settings.xml` 中的 `<allowempty>true</allowempty>` 必须置于 `<constraints>` 内部，防止 Kodi 丢弃设置项。

---

### Task 1: 扩展 Kodi 核心 UI 工具与测试桩 (`kodi_ui.py`, `conftest.py`)

**Files:**
- Modify: `tests/conftest.py`
- Modify: `resources/lib/common/kodi_ui.py`
- Create: `tests/test_kodi_ui.py`

**Interfaces:**
- Produces: `dialog_select_details(title: str, items: list, preselect: int = -1) -> int`

- [ ] **Step 1: 编写测试桩扩展与 failing test**

编辑 `tests/test_kodi_ui.py`：
```python
# -*- coding: utf-8 -*-
"""Unit tests for kodi_ui helpers."""

from unittest.mock import MagicMock, patch
from resources.lib.common.kodi_ui import dialog_select_details


def test_dialog_select_details_normal():
    items = ["item1", "item2"]
    with patch("xbmcgui.Dialog") as mock_dialog_cls:
        mock_dialog = MagicMock()
        mock_dialog.select.return_value = 1
        mock_dialog_cls.return_value = mock_dialog

        idx = dialog_select_details("Select Tool", items, preselect=0)
        assert idx == 1
        mock_dialog.select.assert_called_once_with("Select Tool", items, preselect=0, useDetails=True)


def test_dialog_select_details_fallback_on_type_error():
    items = ["item1", "item2"]
    with patch("xbmcgui.Dialog") as mock_dialog_cls:
        mock_dialog = MagicMock()
        # Simulate older Kodi that does not accept useDetails keyword argument
        def side_effect(title, items, preselect=-1, **kwargs):
            if "useDetails" in kwargs:
                raise TypeError("select() got an unexpected keyword argument 'useDetails'")
            return 0
        mock_dialog.select.side_effect = side_effect
        mock_dialog_cls.return_value = mock_dialog

        idx = dialog_select_details("Select Tool", items)
        assert idx == 0
```

- [ ] **Step 2: 运行测试验证失败**

运行：`python -m pytest tests/test_kodi_ui.py`
预期结果：FAIL，报错 `ImportError: cannot import name 'dialog_select_details' from 'resources.lib.common.kodi_ui'`

- [ ] **Step 3: 更新 mock 并在 `kodi_ui.py` 中实现 `dialog_select_details`**

在 `tests/conftest.py` 中更新 `MockDialog` 的 `select` 方法以支持 `useDetails` 参数：
```python
    def select(self, heading, list_items, preselect=-1, useDetails=False):
        return 0 if list_items else -1
```

在 `resources/lib/common/kodi_ui.py` 中新增函数：
```python
def dialog_select_details(title, items, preselect=-1):
    """Single-selection dialog that renders icons and a second text line.

    ``useDetails=True`` (Kodi 18+) makes the built-in dialog show
    ``ListItem`` label / label2 / art.
    Older Kodi builds that do not support the keyword argument fall back gracefully.
    """
    if _HAS_XBMC and xbmcgui:
        dialog = xbmcgui.Dialog()
        try:
            return dialog.select(title, items, preselect=preselect, useDetails=True)
        except TypeError:
            return dialog.select(title, items)
    return 0 if items else -1
```

- [ ] **Step 4: 运行测试验证通过**

运行：`python -m pytest tests/test_kodi_ui.py`
预期结果：PASS (2 passed)

- [ ] **Step 5: 提交更改**

```bash
git add tests/conftest.py resources/lib/common/kodi_ui.py tests/test_kodi_ui.py
git commit -m "feat(ui): 新增原生详细选择对话框支持 dialog_select_details"
```

---

### Task 2: 完善国际化语言包与工具独立副标题描述 (`strings.po`, `tools/*`)

**Files:**
- Modify: `resources/language/resource.language.zh_cn/strings.po`
- Modify: `resources/language/resource.language.en_gb/strings.po`
- Modify: `resources/lib/tools/disk_benchmark.py`
- Modify: `resources/lib/tools/dtb_tool.py`
- Modify: `resources/lib/tools/net_speedtest.py`
- Modify: `resources/lib/tools/ram_cleaner.py`
- Test: `tests/test_base_tool.py`

**Interfaces:**
- Consumes: PO strings 30022~30029
- Produces: `tool_cls.get_description_id()` 返回各工具专属副标题 ID

- [ ] **Step 1: 编写 failing test**

在 `tests/test_base_tool.py` 中添加对各工具独立描述 ID 的校验：
```python
def test_tool_unique_description_ids():
    from resources.lib.tools import ToolRegistry
    from resources.lib.tools.disk_benchmark import DiskBenchmarkTool
    from resources.lib.tools.dtb_tool import DtbTool
    from resources.lib.tools.net_speedtest import NetSpeedtestTool
    from resources.lib.tools.ram_cleaner import RamCleanerTool

    assert DiskBenchmarkTool.description_id == 30026
    assert DtbTool.description_id == 30027
    assert NetSpeedtestTool.description_id == 30028
    assert RamCleanerTool.description_id == 30029
```

- [ ] **Step 2: 运行测试验证失败**

运行：`python -m pytest tests/test_base_tool.py::test_tool_unique_description_ids`
预期结果：FAIL，`assert 30003 == 30026`

- [ ] **Step 3: 更新工具定义与 strings.po**

修改 `resources/lib/tools/disk_benchmark.py`：
`description_id = 30026`

修改 `resources/lib/tools/dtb_tool.py`：
`description_id = 30027`

修改 `resources/lib/tools/net_speedtest.py`：
`description_id = 30028`

修改 `resources/lib/tools/ram_cleaner.py`：
`description_id = 30029`

在 `resources/language/resource.language.zh_cn/strings.po` 尾部添加：
```po
msgctxt "#30020"
msgid "Unknown Action: %s"
msgstr "未知操作：%s"

msgctxt "#30022"
msgid "Add-on, platform and hardware information"
msgstr "查看插件、平台与硬件信息"

msgctxt "#30023"
msgid "Tool failed: %s"
msgstr "工具执行失败：%s"

msgctxt "#30026"
msgid "Sequential & 4K random read/write benchmark"
msgstr "顺序读写与 4K 随机读写 (IOPS) 测试"

msgctxt "#30027"
msgid "Keep a custom device tree from being overwritten on update"
msgstr "防止 tar 升级覆盖你的定制设备树"

msgctxt "#30028"
msgid "LAN / cloud drive bitrate and WAN bandwidth test"
msgstr "局域网 / 网盘码率与外网带宽测速"

msgctxt "#30029"
msgid "Flush to disk, drop kernel caches, purge Kodi caches"
msgstr "刷盘同步 + 释放内核缓存 + 清理 Kodi 缓存"
```

在 `resources/language/resource.language.en_gb/strings.po` 尾部添加：
```po
msgctxt "#30020"
msgid "Unknown Action: %s"
msgstr "Unknown Action: %s"

msgctxt "#30022"
msgid "Add-on, platform and hardware information"
msgstr "Add-on, platform and hardware information"

msgctxt "#30023"
msgid "Tool failed: %s"
msgstr "Tool failed: %s"

msgctxt "#30026"
msgid "Sequential & 4K random read/write benchmark"
msgstr "Sequential & 4K random read/write benchmark"

msgctxt "#30027"
msgid "Keep a custom device tree from being overwritten on update"
msgstr "Keep a custom device tree from being overwritten on update"

msgctxt "#30028"
msgid "LAN / cloud drive bitrate and WAN bandwidth test"
msgstr "LAN / cloud drive bitrate and WAN bandwidth test"

msgctxt "#30029"
msgid "Flush to disk, drop kernel caches, purge Kodi caches"
msgstr "Flush to disk, drop kernel caches, purge Kodi caches"
```

- [ ] **Step 4: 运行测试验证通过**

运行：`python -m pytest tests/test_base_tool.py`
预期结果：PASS

- [ ] **Step 5: 提交更改**

```bash
git add resources/language/ resources/lib/tools/ tests/test_base_tool.py
git commit -m "feat(i18n): 补全工具专属描述ID及中英文多语言文案"
```

---

### Task 3: 重构 URL 路由层与容器生命周期调度 (`router.py`, `test_router.py`)

**Files:**
- Modify: `resources/lib/router.py`
- Modify: `tests/test_router.py`

**Interfaces:**
- Produces:
  - `close_container(handle: int) -> None`
  - `menu_entries() -> List[Tuple[str, str, str, str]]`
  - `run_tool(action: str) -> None`
  - `show_dialog_menu(reason: str = "") -> None`
  - `show_main_menu(base_url: str, handle: int) -> None`
  - `route(argv: List[str]) -> None`

- [ ] **Step 1: 编写路由与生命周期 failing tests**

在 `tests/test_router.py` 中追加测试用例：
```python
from unittest.mock import MagicMock, patch
from resources.lib.router import close_container, menu_entries, run_tool, show_main_menu, route


def test_close_container_with_valid_handle():
    with patch("xbmcplugin.endOfDirectory") as mock_end:
        close_container(10)
        mock_end.assert_called_once_with(10, succeeded=False, updateListing=False, cacheToDisc=False)


def test_close_container_with_negative_handle():
    with patch("xbmcplugin.endOfDirectory") as mock_end:
        close_container(-1)
        mock_end.assert_not_called()


def test_menu_entries_completeness():
    entries = menu_entries()
    assert len(entries) >= 7  # All registered tools + system info
    actions = [e[0] for e in entries]
    assert "speedtest" in actions
    assert "kodi_optimizer" in actions
    assert "about" in actions


def test_run_tool_error_handling():
    with patch("resources.lib.tools.ToolRegistry.dispatch", side_effect=RuntimeError("Simulated error")), \
         patch("resources.lib.common.kodi_ui.show_notification") as mock_notify:
        run_tool("speedtest")
        mock_notify.assert_called_once()
        assert "speedtest" in mock_notify.call_args[0][1]


def test_route_dispatches_main_menu_and_closes_container():
    with patch("resources.lib.router.close_container") as mock_close, \
         patch("resources.lib.router.show_dialog_menu") as mock_menu:
        route(["plugin://plugin.program.systemtools/", "5", ""])
        mock_close.assert_called_once_with(5)
        mock_menu.assert_called_once()


def test_route_direct_action():
    with patch("resources.lib.router.run_tool") as mock_run:
        route(["plugin://plugin.program.systemtools/", "-1", "?action=speedtest"])
        mock_run.assert_called_once_with("speedtest")
```

- [ ] **Step 2: 运行测试验证失败**

运行：`python -m pytest tests/test_router.py`
预期结果：FAIL，提示 `close_container`, `menu_entries`, `run_tool` 不存在或未导入。

- [ ] **Step 3: 重构 `resources/lib/router.py`**

在 `resources/lib/router.py` 中实现：
1. `close_container(handle)`：若 `handle >= 0` 且 `xbmcplugin` 可用，调用 `xbmcplugin.endOfDirectory(handle, succeeded=False, updateListing=False, cacheToDisc=False)`。
2. `menu_entries()`：生成 `(action, label, description, icon)` 列表，包含注册工具与 `about` 条目。
3. `run_tool(action)`：包裹 `ToolRegistry.dispatch`，捕获异常并调用 `show_notification`。
4. `show_dialog_menu(reason)`：事件循环生成 `ListItem`（设置 label、label2、art），调用 `dialog_select_details`。用户选择动作则执行 `run_entry(action)` 并循环重显菜单；取消或关闭则退出。
5. `show_main_menu(base_url, handle)`：关闭容器（若 `handle >= 0`）并直接调用 `show_dialog_menu`。
6. `route(argv)`：分发 `action in ("menu", "dialog", "root", "")`、`about` 及直接 `run_tool(action)`。

- [ ] **Step 4: 运行测试验证通过**

运行：`python -m pytest tests/test_router.py`
预期结果：PASS (all tests passing)

- [ ] **Step 5: 提交更改**

```bash
git add resources/lib/router.py tests/test_router.py
git commit -m "refactor(router): 统一采用原生详细对话框主菜单并增强容器管理与异常通知"
```

---

### Task 4: 修正配置规范、元数据与打包构建脚本 (`settings.xml`, `addon.xml`, `package.py`)

**Files:**
- Modify: `resources/settings.xml`
- Modify: `addon.xml`
- Modify: `scripts/package.py`

**Interfaces:**
- Produces: 符合规范的 `settings.xml` 和 `addon.xml`，以及自动忽略本地 `plugin.program.systemtools` 参考目录的 `package.py`。

- [ ] **Step 1: 修正 `resources/settings.xml` 约束嵌套**

将 `resources/settings.xml` 中第 25-30 行的 `custom_speedtest_url`：
```xml
                <setting id="custom_speedtest_url" type="string" label="30605" help="30606">
                    <level>1</level>
                    <constraints>
                        <allowempty>true</allowempty>
                    </constraints>
                    <default></default>
                    <control type="edit" format="string"/>
                </setting>
```
确保 `<allowempty>` 包含在 `<constraints>` 中。

- [ ] **Step 2: 更新 `addon.xml` 元数据与版本号**

修改 `addon.xml`：
- 版本号递增至 `1.0.3`。
- 在 `<extension point="xbmc.addon.metadata">` 内部添加 `<language>en_GB zh_CN</language>`。

- [ ] **Step 3: 优化 `scripts/package.py` 排除规则**

在 `scripts/package.py` 的 `EXCLUDE_PATTERNS` 列表中增加：
```python
    r"^plugin\.program\.systemtools",
```
防止当前目录下的参考文件夹或历史构建被误打入正式安装包 ZIP 中。

- [ ] **Step 4: 运行现有全部单元测试**

运行：`python -m pytest tests/`
预期结果：PASS (全部 35+ 个用例通过)

- [ ] **Step 5: 提交更改**

```bash
git add resources/settings.xml addon.xml scripts/package.py
git commit -m "fix(meta): 规范 settings.xml 约束配置，更新 addon.xml 语言标签并优化打包排除规则"
```

---

### Task 5: 整体集成验证与构建打包

**Files:**
- Output: `dist/plugin.program.systemtools-1.0.3.zip`

- [ ] **Step 1: 运行全量代码风格检查**

运行：`flake8 resources/ addon.py tests/`
预期结果：无任何警告与报错 (exit code 0)。

- [ ] **Step 2: 运行测试覆盖率校验**

运行：`python -m pytest --cov=resources.lib tests/`
预期结果：全部测试通过，覆盖率保持高水平。

- [ ] **Step 3: 执行打包脚本生成发行包**

运行：`python scripts/package.py`
预期结果：
- 成功输出 `dist/plugin.program.systemtools-1.0.3.zip`。
- 检查 ZIP 包结构：确保顶层目录为 `plugin.program.systemtools/`，包含 `addon.xml`、`resources/`，且不包含测试、参考文件夹等无关文件。

- [ ] **Step 4: 提交最终文档或说明更新**

更新 `README.md` 与更新日志，提交至 git。
```bash
git add README.md
git commit -m "docs: 更新 README 说明，记录 1.0.3 全皮肤兼容原生对话框主菜单升级"
```
