# -*- coding: utf-8 -*-
"""Unit tests for CoreELEC DTB protection and management tool."""

import os
from unittest.mock import patch

from resources.lib.tools.dtb_tool import (
    DtbTool,
    is_dtb_protected,
    set_dtb_protection,
)


def test_dtb_protection_toggle(tmp_path):
    config_dir = str(tmp_path / "config")
    os.makedirs(config_dir, exist_ok=True)

    # 1. By default when file does not exist
    assert is_dtb_protected(config_dir) is False

    # 2. Enable protection (writes ENABLE=no)
    assert set_dtb_protection(True, config_dir) is True
    assert is_dtb_protected(config_dir) is True

    conf_file = os.path.join(config_dir, "dtb-autoupdate.conf")
    with open(conf_file, "r") as f:
        content = f.read()
    assert "ENABLE=no" in content

    # 3. Disable protection (writes ENABLE=yes)
    assert set_dtb_protection(False, config_dir) is True
    assert is_dtb_protected(config_dir) is False

    with open(conf_file, "r") as f:
        content = f.read()
    assert "ENABLE=yes" in content


def test_dtb_tool_backup_and_restore(tmp_path):
    config_dir = str(tmp_path / "config")
    flash_dir = str(tmp_path / "flash")
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(flash_dir, exist_ok=True)

    # Create dummy dtb.img in /flash
    live_dtb = os.path.join(flash_dir, "dtb.img")
    with open(live_dtb, "wb") as f:
        f.write(b"CUSTOM_DTB_DATA_123")

    tool = DtbTool(config_dir=config_dir, flash_dir=flash_dir)

    # Backup DTB
    tool._action_backup_dtb("DTB Tool")

    backup_dtb = os.path.join(config_dir, "custom_dtb.img")
    assert os.path.exists(backup_dtb)
    with open(backup_dtb, "rb") as f:
        assert f.read() == b"CUSTOM_DTB_DATA_123"

    # DTB protection should also be auto-enabled on backup
    assert is_dtb_protected(config_dir) is True

    # Modify live DTB to test restore
    with open(live_dtb, "wb") as f:
        f.write(b"OVERWRITTEN_DTB")

    with patch("resources.lib.tools.dtb_tool.dialog_yesno", return_value=True):
        tool._action_restore_dtb("DTB Tool")

    with open(live_dtb, "rb") as f:
        assert f.read() == b"CUSTOM_DTB_DATA_123"
