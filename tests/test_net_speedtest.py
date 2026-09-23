# -*- coding: utf-8 -*-
"""Unit tests for NetSpeedtestTool."""

import os
from unittest.mock import MagicMock, patch
from resources.lib.tools.net_speedtest import NetSpeedtestTool


def test_speedtest_instantiation():
    tool = NetSpeedtestTool()
    assert tool.id == "speedtest"
    assert tool.title_id == 30002


def test_protocol_recognition():
    tool = NetSpeedtestTool()

    # Supported protocols
    assert tool._is_supported_protocol("smb://nas/movies/test.mkv") is True
    assert tool._is_supported_protocol("nfs://192.168.1.100/data/video.mp4") is True
    assert tool._is_supported_protocol("webdav://alist/drive/movie.mkv") is True
    assert tool._is_supported_protocol("http://example.com/video.mp4") is True
    assert tool._is_supported_protocol("/storage/videos/movie.mkv") is True
    assert tool._is_supported_protocol("") is False

    # Protocol naming
    assert "SMB" in tool._get_protocol_name("smb://nas/movie.mkv")
    assert "NFS" in tool._get_protocol_name("nfs://nas/movie.mkv")
    assert "WebDAV" in tool._get_protocol_name("webdav://cloud/movie.mkv")
    proto_local = tool._get_protocol_name("/storage/movie.mkv")
    assert "Local" in proto_local or "本地" in proto_local


def test_stream_speedtest_chunk_reading(tmp_path):
    tool = NetSpeedtestTool()
    dummy_file = str(tmp_path / "test_stream.mkv")

    # Write 5 MB of data
    with open(dummy_file, "wb") as f:
        f.write(b"X" * (5 * 1024 * 1024))

    f_src = tool._open_vfs_file(dummy_file)
    assert f_src is not None

    chunk = tool._read_vfs_chunk(f_src, 1024 * 1024)
    assert len(chunk) == 1024 * 1024

    tool._close_vfs_file(f_src)


def test_measure_latency_mocked():
    tool = NetSpeedtestTool()
    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value = mock_sock
        latency = tool._measure_latency(count=1)
        assert latency >= 0.0


def test_test_download_mocked():
    tool = NetSpeedtestTool()
    mock_dp = MagicMock()
    mock_dp.is_canceled.return_value = False

    fake_data = b"0" * (64 * 1024)
    mock_response = MagicMock()
    mock_response.read.side_effect = [fake_data, fake_data, b""]
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        mbps, mbs = tool._test_download("http://example.com/test", duration=5, dp=mock_dp)
        assert mbps > 0
        assert mbs > 0
