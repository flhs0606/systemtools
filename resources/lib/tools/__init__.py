# -*- coding: utf-8 -*-
"""Toolbox tools registry and exports."""

from .base_tool import BaseTool, ToolRegistry
from .disk_benchmark import DiskBenchmarkTool
from .log_cleaner import LogCleanerTool
from .net_config import NetConfigTool
from .net_speedtest import NetSpeedtestTool
from .os_switcher import OsSwitcherTool

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "OsSwitcherTool",
    "NetSpeedtestTool",
    "DiskBenchmarkTool",
    "NetConfigTool",
    "LogCleanerTool",
]
