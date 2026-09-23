# -*- coding: utf-8 -*-
"""Unit tests for RAM & cache cleaner tool."""

from unittest.mock import MagicMock, patch

from resources.lib.tools.ram_cleaner import (
    RamCleanerTool,
    format_bytes,
    read_meminfo,
)


def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(100 * 1024 * 1024) == "100.0 MB"
    assert format_bytes(2 * 1024 * 1024 * 1024) == "2.00 GB"


def test_read_meminfo():
    mem = read_meminfo()
    assert "total" in mem
    assert "free" in mem
    assert "available" in mem
    assert "used" in mem
    assert mem["total"] > 0


def test_ram_cleaner_execution():
    tool = RamCleanerTool()
    assert tool.id == "ram_cleaner"
    assert tool.title_id == 30800

    # Test run execution
    with patch.object(tool, "_flush_and_drop_caches"):
        tool.run({})
