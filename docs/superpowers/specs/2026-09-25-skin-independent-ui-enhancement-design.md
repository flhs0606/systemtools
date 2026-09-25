# 设计规范：全皮肤兼容的系统工具箱统一 UI 架构

## 1. 概述与设计背景

### 1.1 现状与问题
当前系统工具箱插件采用 Kodi 传统的 `plugin://` 目录列表流（通过 `xbmcplugin.addDirectoryItem` 与 `xbmcplugin.endOfDirectory`）呈现主菜单。在 Kodi 架构中，该列表由当前激活皮肤的媒体视图窗口（如 `MyPrograms.xml`）承载并渲染。
* **跨皮肤缺陷**：Kodi 不支持跨皮肤回退窗口 XML（`CSkinInfo::GetSkinPath` 仅在当前皮肤内部解析）。在很多第三方皮肤（如精简皮肤、定制第三方皮肤、部分外贸盒默认皮肤）中，程序插件列表窗口被裁减或缺少列表视图，导致用户在 Kodi 中点击插件图标时**没有任何反应、白屏或无限加载**。
* **启动通道多样性**：用户可能从「程序插件列表」启动（Kodi 会分配 `handle >= 0` 的容器），也可能从「收藏夹」、「皮肤自定义快捷按钮」或 `RunPlugin(...)` 启动（此时无容器，`handle = -1`）。原插件无法可靠处理这些不同启动入口。

### 1.2 目标与决策
打造一个**单一、最兼容、最美观且完全皮肤无关**的主菜单交互界面：
* 采用 Kodi 核心 C++ 原生详细对话框：`xbmcgui.Dialog().select(useDetails=True)`。
* 彻底摆脱对皮肤 `MyPrograms.xml` 的依赖，杜绝第三方面板纹理缺失或合成失败（Mali/GLES 显卡下的黑屏/白字悬浮）风险。
* 继承用户当前皮肤的原生色彩、字体、磨砂材质与光标焦点，天然具备最高颜值与原生感。
* 正确管理容器生命周期，无论何种启动途径均秒级响应。

---

## 2. 核心架构与交互流程

### 2.1 容器生命周期管理 (`close_container`)
* 当 `handle >= 0`（从 Kodi 程序插件列表等有容器入口进入）：
  若不填充原生目录项，必须显式调用：
  ```python
  xbmcplugin.endOfDirectory(handle, succeeded=False, updateListing=False, cacheToDisc=False)
  ```
  通知 Kodi 媒体窗口放弃等待目录项并撤销加载动画（Spinner），防止界面悬挂转圈。
* 当 `handle < 0`（从快捷方式、收藏夹、RunPlugin 等无容器入口进入）：
  直接进入 UI 调度，无需执行容器收尾。

### 2.2 主菜单交互循环 (`show_dialog_menu`)
主菜单采用交互式事件循环：
1. 组装菜单条目：遍历 `ToolRegistry.get_all()` 获取所有已注册工具，外加「系统信息」条目。
2. 为每个条目构建带有图标、主标题（`label`）与独立功能说明副标题（`label2`）的 `ListItem`。
3. 弹出 `dialog_select_details(title, items)`。
4. 若用户选择某一工具，执行对应工具；执行完毕后**自动重新回到主菜单**，方便用户连续进行系统维护。
5. 若用户按遥控器返回键（Back）或取消，循环结束并优雅退出。

### 2.3 安全调度与故障隔离 (`run_tool`)
工具执行入口增加统一异常捕获：
* 捕获并记录完整异常堆栈（`logger.error`）。
* 调用 `show_notification` 弹出友好的 Kodi Toast 提示（如 `工具执行失败：%s`），彻底杜绝插件崩溃或静默死亡。

---

## 3. 详细组件变动与改造清单

### 3.1 `resources/lib/common/kodi_ui.py`
新增 `dialog_select_details(title, items, preselect=-1)`：
* 优先调用 `xbmcgui.Dialog().select(title, items, preselect=preselect, useDetails=True)`。
* 针对可能不支持 `useDetails` 参数的旧版 Kodi 核心环境进行 `TypeError` 捕获，平滑回退至基础 `select(title, items)`。

### 3.2 `resources/lib/router.py`
* 重构 `show_main_menu` / `show_dialog_menu`：统一以 `show_dialog_menu` 作为唯一核心 UI。
* 新增 `close_container(handle)`：规范关闭无用容器句柄。
* 统一工具菜单数据结构 `menu_entries()`：返回 `(action, label, description, icon)`。
* 路由分发强化：
  * 空参数 / `?action=menu` / `?action=dialog` / `?action=root`：关闭容器（若有）并弹出主菜单对话框。
  * `?action=about`：展示诊断信息。
  * `?action=<tool_id>`：通过 `run_tool` 安全分发。
* 废弃设置项 `use_builtin_window` 与 `use_native_list`，保持极简零配置。

### 3.3 工具副标题描述与国际化 (`strings.po`)
消除主副标题文案重复，为各工具配置独立的 `description_id`：
* `resources/lib/tools/disk_benchmark.py`: `description_id = 30026`（"顺序读写与 4K 随机读写 (IOPS) 测试"）
* `resources/lib/tools/dtb_tool.py`: `description_id = 30027`（"防止 tar 升级覆盖你的定制设备树"）
* `resources/lib/tools/net_speedtest.py`: `description_id = 30028`（"局域网 / 网盘码率与外网带宽测速"）
* `resources/lib/tools/ram_cleaner.py`: `description_id = 30029`（"刷盘同步 + 释放内核缓存 + 清理 Kodi 缓存"）
* `resources/language/resource.language.zh_cn/strings.po` 与 `en_gb/strings.po`：
  * 补全 30022（系统信息说明）、30023（工具执行失败提示）、30026~30029（工具详细副标题）。

### 3.4 基础规范修正
* `resources/settings.xml`：将 `<allowempty>true</allowempty>` 规范移入 `<constraints>` 节点内，符合 Kodi XML 校验标准。
* `addon.xml`：
  * 增加 `<language>en_GB zh_CN</language>` 声明。
  * 版本号更新为 `1.0.3`。
* `scripts/package.py`：在 `EXCLUDE_PATTERNS` 中加入 `^plugin\.program\.systemtools`，防止临时参考目录被误打入发布 ZIP。

---

## 4. 测试与验证策略

1. **测试桩（Mock）增强 (`tests/conftest.py`)**：
   * 在 mock 的 `xbmcgui.Dialog.select` 中支持接收 `useDetails=True` 关键字参数。
   * 确保 `xbmcplugin.endOfDirectory` mock 正确记录 `succeeded=False` 调用。
2. **单元测试 (`tests/test_router.py`)**：
   * 测试 `menu_entries()`：验证包含了所有注册工具与关于条目，且文案与图标非空。
   * 测试容器关闭逻辑：验证当 `handle >= 0` 时调用了 `endOfDirectory(handle, succeeded=False)`。
   * 测试主菜单循环与用户退出。
   * 测试 `run_tool` 遇到未知 action 及异常抛出时的 notification 捕获。
   * 测试 URL 参数解析（`?action=menu`, `?action=dialog`, `?action=about`, etc.）。
3. **回归测试**：
   * 运行完整的 `pytest tests/` 确保所有既有 29 个测试用例和新增用例 100% 通过。
