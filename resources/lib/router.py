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
    version = addon.getAddonInfo("version") if addon else "1.0.0"

    info_lines = [
        "=== Kodi System Toolbox ===",
        f"Version: {version}",
        f"Author: Mephis",
        "License: GPL-2.0-or-later",
        "--------------------------------------------------",
        f"Operating System: {sys_info.os_type}",
        f"Architecture: {sys_info.arch}",
        f"Hardware/SoC: {sys_info.soc}",
        f"Dual-Boot Support: {'Yes' if sys_info.dual_boot_supported else 'No'}",
        f"Python Runtime: {sys.version.split()[0]}",
        "--------------------------------------------------",
        "Features Included:",
        "  1. Switch OS (CoreELEC / LibreELEC / Android)",
        "  2. Network Speed Test (Ping, Download, Upload)",
        "  3. Disk Benchmark (Sequential & 4K Random IOPS)",
        "  4. Network Configuration (IP, Gateway, DNS)",
        "  5. Kodi Log Viewer & Cleaner",
    ]
    dialog_textviewer("About & System Info", "\n".join(info_lines))


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
            show_notification("System Tools", f"Unknown action: {action}")
