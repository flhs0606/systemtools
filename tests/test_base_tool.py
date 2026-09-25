# -*- coding: utf-8 -*-
"""Unit tests for BaseTool and ToolRegistry."""

import pytest
from resources.lib.tools.base_tool import BaseTool, ToolRegistry


class DummySampleTool(BaseTool):
    id = "dummy_sample"
    title_id = 30000
    description_id = 30000
    order = 999

    def __init__(self):
        self.called = False

    def run(self, params):
        self.called = True


def test_tool_registry():
    ToolRegistry.register(DummySampleTool)

    all_tools = ToolRegistry.get_all()
    assert DummySampleTool in all_tools

    instance = ToolRegistry.get("dummy_sample")
    assert instance is not None
    assert instance.id == "dummy_sample"

    # Test dispatching
    dispatched = ToolRegistry.dispatch("dummy_sample", {"param1": "test"})
    assert dispatched is True

    # Test unknown tool dispatching
    assert ToolRegistry.dispatch("non_existent_tool_123", {}) is False


def test_tool_unique_description_ids():
    from resources.lib.tools.disk_benchmark import DiskBenchmarkTool
    from resources.lib.tools.dtb_tool import DtbTool
    from resources.lib.tools.net_speedtest import NetSpeedtestTool
    from resources.lib.tools.ram_cleaner import RamCleanerTool

    assert DiskBenchmarkTool.description_id == 30026
    assert DtbTool.description_id == 30027
    assert NetSpeedtestTool.description_id == 30028
    assert RamCleanerTool.description_id == 30029

