# -*- coding: utf-8 -*-
"""Unit tests for OS and platform detection."""

from resources.lib.common.os_detect import OSType, SystemInfo, get_system_info


def test_system_info_detection():
    info = get_system_info()
    assert info is not None
    assert info.os_type in [
        OSType.WINDOWS,
        OSType.LINUX,
        OSType.DARWIN,
        OSType.COREELEC,
        OSType.LIBREELEC,
        OSType.ANDROID,
        OSType.UNKNOWN,
    ]
    assert isinstance(info.arch, str)
    assert isinstance(info.soc, str)
    assert isinstance(info.dual_boot_supported, bool)


def test_system_info_dict():
    info = SystemInfo()
    d = info.to_dict()
    assert "os_type" in d
    assert "arch" in d
    assert "soc" in d
    assert "dual_boot_supported" in d
