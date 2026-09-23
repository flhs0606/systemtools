# -*- coding: utf-8 -*-
"""Pytest fixtures and Kodi mocks for testing outside Kodi runtime."""

import os
import sys
from unittest.mock import MagicMock

# Ensure addon root and resources/lib are in sys.path
ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ADDON_ROOT not in sys.path:
    sys.path.insert(0, ADDON_ROOT)

LIB_DIR = os.path.join(ADDON_ROOT, "resources", "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)


class MockVfsFile:
    """Mock xbmcvfs.File that reads from real file on disk if present."""
    def __init__(self, path, mode="r"):
        self._path = path
        self._mode = mode
        if isinstance(path, str) and os.path.exists(path):
            self._file = open(path, "rb" if "b" in mode or mode == "r" else "r")
        else:
            self._file = None

    def readBytes(self, size):
        if self._file:
            return self._file.read(size)
        return b""

    def read(self, size=-1):
        if self._file:
            return self._file.read(size)
        return b""

    def size(self):
        if isinstance(self._path, str) and os.path.exists(self._path):
            return os.path.getsize(self._path)
        return 0

    def close(self):
        if self._file:
            self._file.close()


# Install mock Kodi modules if not present
if "xbmc" not in sys.modules:
    mock_xbmc = MagicMock()
    mock_xbmc.LOGDEBUG = 0
    mock_xbmc.LOGINFO = 1
    mock_xbmc.LOGWARNING = 2
    mock_xbmc.LOGERROR = 3
    sys.modules["xbmc"] = mock_xbmc

if "xbmcaddon" not in sys.modules:
    mock_xbmcaddon = MagicMock()
    addon_instance = MagicMock()
    addon_instance.getLocalizedString.return_value = ""
    addon_instance.getSetting.return_value = ""
    addon_instance.getSettingInt.return_value = 10
    addon_instance.getSettingBool.return_value = False
    mock_xbmcaddon.Addon.return_value = addon_instance
    sys.modules["xbmcaddon"] = mock_xbmcaddon

if "xbmcgui" not in sys.modules:
    mock_xbmcgui = MagicMock()
    dialog_instance = MagicMock()
    dialog_instance.yesno.return_value = True
    dialog_instance.select.return_value = 0
    dialog_instance.input.return_value = "192.168.1.100"
    dialog_instance.browse.side_effect = lambda t, h, s, m="", u=False, f=False, default="": default
    dialog_instance.browseSingle.side_effect = lambda t, h, s="", m="", u=False, f=False, default="": default
    mock_xbmcgui.Dialog.return_value = dialog_instance

    dp_instance = MagicMock()
    dp_instance.iscanceled.return_value = False
    mock_xbmcgui.DialogProgress.return_value = dp_instance
    sys.modules["xbmcgui"] = mock_xbmcgui

if "xbmcvfs" not in sys.modules:
    mock_xbmcvfs = MagicMock()
    mock_xbmcvfs.translatePath.side_effect = lambda p: p.replace("special://home/", "/tmp/kodi_home/").replace("special://logpath/", "/tmp/kodi_log/")
    mock_xbmcvfs.File = MockVfsFile
    mock_xbmcvfs.exists.side_effect = lambda p: os.path.exists(p) if isinstance(p, str) else False
    sys.modules["xbmcvfs"] = mock_xbmcvfs

if "xbmcplugin" not in sys.modules:
    mock_xbmcplugin = MagicMock()
    sys.modules["xbmcplugin"] = mock_xbmcplugin
