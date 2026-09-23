# -*- coding: utf-8 -*-
"""Unit tests for LogCleanerTool."""

import os
from resources.lib.tools.log_cleaner import LogCleanerTool


def test_log_cleaner_find_and_truncate(tmp_path):
    log_dir = str(tmp_path)
    active_log = os.path.join(log_dir, "kodi.log")
    old_log = os.path.join(log_dir, "kodi.old.log")

    # Create dummy log files
    with open(active_log, "w", encoding="utf-8") as f:
        f.write("Line 1: Log entry\nLine 2: Log entry\n")
    with open(old_log, "w", encoding="utf-8") as f:
        f.write("Old log entry\n")

    tool = LogCleanerTool()
    files = tool._find_log_files(log_dir)

    assert len(files) == 2
    names = [f["name"] for f in files]
    assert "kodi.log" in names
    assert "kodi.old.log" in names

    # Test size formatting
    assert tool._format_size(500) == "500 B"
    assert tool._format_size(2048) == "2.0 KB"
    assert tool._format_size(5 * 1024 * 1024) == "5.00 MB"
