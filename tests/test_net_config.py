# -*- coding: utf-8 -*-
"""Unit tests for NetConfigTool."""

from resources.lib.tools.net_config import NetConfigTool


def test_ip_validation():
    tool = NetConfigTool()

    assert tool._is_valid_ipv4("192.168.1.1") is True
    assert tool._is_valid_ipv4("10.0.0.1") is True
    assert tool._is_valid_ipv4("255.255.255.0") is True
    assert tool._is_valid_ipv4("1.1.1.1") is True

    assert tool._is_valid_ipv4("256.1.1.1") is False
    assert tool._is_valid_ipv4("192.168.1") is False
    assert tool._is_valid_ipv4("not_an_ip") is False
    assert tool._is_valid_ipv4("") is False


def test_netmask_to_cidr():
    tool = NetConfigTool()

    assert tool._netmask_to_cidr("255.255.255.0") == 24
    assert tool._netmask_to_cidr("255.255.0.0") == 16
    assert tool._netmask_to_cidr("255.0.0.0") == 8
    assert tool._netmask_to_cidr("255.255.255.255") == 32
