# -*- coding: utf-8 -*-
"""Unit tests for URL routing and parameter parsing."""

from resources.lib.router import parse_params


def test_parse_params():
    assert parse_params("") == {}
    assert parse_params("?") == {}
    assert parse_params("?action=speedtest") == {"action": "speedtest"}
    assert parse_params("action=speedtest&sub=start") == {"action": "speedtest", "sub": "start"}
    assert parse_params("?action=disk_bench&size=128") == {"action": "disk_bench", "size": "128"}
