# -*- coding: utf-8 -*-
"""URL Router and Menu Dispatcher for Kodi System Tools."""

import sys
import urllib.parse
from typing import Dict

from .common.kodi_ui import (
    dialog_textviewer,
    get_addon,
    get_string,
    show_notification,
)
from .common.logger import debug, error, info
from .common.os_detect import get_system_info
from .tools import ToolRegistry

try:
    import xbmcgui
    import xbmcplugin
    _HAS_XBMC = True
except ImportError:
    _HAS_XBMC = False
    xbmcgui = None
    xbmcplugin = None


def parse_params(param_string: str) -> Dict[str, str]:
    """Parse query string '?key=val&...' into a dictionary."""
    if not param_string:
        return {}
    if param_string.startswith("?"):
        param_string = param_string[1:]
    parsed = urllib.parse.parse_qs(param_string)
    return {k: v[0] for k, v in parsed.items()}


def show_main_menu(base_url: str, handle: int) -> None:
    """Render the main toolbox directory items in Kodi."""
    if not (_HAS_XBMC and xbmcplugin and xbmcgui):
        print(f"Main menu rendered (handle: {handle})")
        return

    xbmcplugin.setContent(handle, "executable")

    for tool_cls in ToolRegistry.get_all():
        title = get_string(tool_cls.get_title_id())
        desc = get_string(tool_cls.get_description_id())
        icon = tool_cls.get_icon()

        item = xbmcgui.ListItem(label=title)
        item.setArt({"icon": icon, "thumb": icon})
        item.setInfo("video", {"plot": desc})
        item.setProperty("IsPlayable", "false")

        item_url = f"{base_url}?action={tool_cls.get_id()}"
        xbmcplugin.addDirectoryItem(
            handle=handle,
            url=item_url,
            listitem=item,
            isFolder=False,
        )

    # Add System Info & About Item
    about_title = get_string(30006, "System Information")
    about_item = xbmcgui.ListItem(label=about_title)
    about_item.setArt({"icon": "DefaultAddonInfo.png", "thumb": "DefaultAddonInfo.png"})
    about_item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(
        handle=handle,
        url=f"{base_url}?action=about",
        listitem=about_item,
        isFolder=False,
    )

    xbmcplugin.endOfDirectory(handle)


def show_about_info() -> None:
    """Show Addon & Hardware platform diagnostic information."""
    sys_info = get_system_info()
    addon = get_addon()
    version = addon.getAddonInfo("version") if addon else "1.0.1"
    dual_boot_str = get_string(30016, "Yes") if sys_info.dual_boot_supported else get_string(30017, "No")

    info_lines = [
        f"=== {get_string(30000, 'System Tools')} ===",
        f"Version: {version}",
        "Author: Mephis",
        "License: GPL-2.0-or-later",
        "--------------------------------------------------",
        get_string(30012, "Operating System: %s") % sys_info.os_type,
        get_string(30013, "Architecture: %s") % sys_info.arch,
        get_string(30014, "Hardware/SoC: %s") % sys_info.soc,
        get_string(30015, "Dual-Boot Support: %s") % dual_boot_str,
        get_string(30018, "Python Runtime: %s") % sys.version.split()[0],
        "--------------------------------------------------",
        get_string(30019, "Toolbox Features:"),
        f"  1. {get_string(30001, 'CoreELEC System & Version Switcher')}",
        f"  2. {get_string(30700, 'DTB Protection & Management')}",
        f"  3. {get_string(30800, 'Free System RAM')}",
        f"  4. {get_string(30900, 'Kodi Performance Optimizer')}",
        f"  5. {get_string(30002, 'Network Speed Test')}",
        f"  6. {get_string(30003, 'Disk Benchmark')}",
        f"  7. {get_string(30004, 'Network Configuration')}",
        f"  8. {get_string(30005, 'Clear Kodi Logs')}",
    ]
    dialog_textviewer(get_string(30006, "System Information"), "\n".join(info_lines))


def route(argv: list) -> None:
    """Entry point router."""
    base_url = argv[0] if len(argv) > 0 else ""
    try:
        handle = int(argv[1]) if len(argv) > 1 else -1
    except ValueError:
        handle = -1
    param_string = argv[2] if len(argv) > 2 else ""

    params = parse_params(param_string)
    action = params.get("action", "")

    debug(f"Router handling action: '{action}', params: {params}")

    if not action:
        # Show root toolbox menu
        show_main_menu(base_url, handle)
    elif action == "about":
        show_about_info()
    else:
        dispatched = ToolRegistry.dispatch(action, params)
        if not dispatched:
            error(f"Unknown action requested: {action}")
            show_notification(get_string(30000, "System Tools"), get_string(30020, "Unknown Action: %s") % action)
