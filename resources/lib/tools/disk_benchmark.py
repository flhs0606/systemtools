# -*- coding: utf-8 -*-
"""Tool: Disk Storage Benchmark (Sequential & 4K Random Read/Write with IOPS)."""

import os
import random
import time
from typing import Dict, Optional, Tuple

from ..common.kodi_ui import (
    dialog_browse,
    dialog_select,
    dialog_textviewer,
    get_setting_int,
    get_string,
    progress_dialog,
    translate_path,
)
from ..common.logger import debug, error, info
from ..common.system_exec import run_command
from .base_tool import BaseTool, ToolRegistry

BENCH_FILENAME = ".kodi_disk_bench.tmp"
O_BINARY = getattr(os, "O_BINARY", 0)


@ToolRegistry.register
class DiskBenchmarkTool(BaseTool):
    id = "disk_bench"
    title_id = 30003
    description_id = 30026
    icon = "DefaultHardDisk.png"
    order = 30

    def run(self, params: Dict[str, str]) -> None:
        title = get_string(30003, "Disk Benchmark")
        info("Initiating Disk Benchmark Tool")

        # 1. Choose target path
        target_dir = self._select_target_directory(title)
        if not target_dir:
            return

        # 2. Choose test size
        test_size_mb = self._select_test_size(title)
        if not test_size_mb:
            return

        target_filepath = os.path.join(target_dir, BENCH_FILENAME)
        info(f"Disk Benchmark target: {target_filepath}, size: {test_size_mb} MB")

        # Run benchmarks with progress dialog
        seq_write_mbs = 0.0
        seq_read_mbs = 0.0
        rand_write_iops, rand_write_mbs = 0.0, 0.0
        rand_read_iops, rand_read_mbs = 0.0, 0.0

        try:
            with progress_dialog(title, get_string(30303, "Testing Sequential Write...")) as dp:
                # Step 1: Sequential Write
                dp.update(5, get_string(30303, "Testing Sequential Write..."))
                seq_write_mbs = self._test_sequential_write(target_filepath, test_size_mb, dp)
                if dp.is_canceled():
                    return

                # Flush OS pagecache to eliminate cache inflation before sequential read
                dp.update(28, get_string(30319, "Flushing OS cache to measure true physical read speed..."))
                self._flush_and_evict_cache(target_filepath)
                if dp.is_canceled():
                    return

                # Step 2: Sequential Read
                dp.update(30, get_string(30304, "Testing Sequential Read..."))
                seq_read_mbs = self._test_sequential_read(target_filepath, dp)
                if dp.is_canceled():
                    return

                # Step 3: 4K Random Write
                dp.update(55, get_string(30305, "Testing 4K Random Write..."))
                rand_write_iops, rand_write_mbs = self._test_4k_random_write(target_filepath, test_size_mb, dp)
                if dp.is_canceled():
                    return

                # Flush OS pagecache to eliminate cache inflation before 4K random read
                dp.update(78, get_string(30319, "Flushing OS cache to measure true physical read speed..."))
                self._flush_and_evict_cache(target_filepath)
                if dp.is_canceled():
                    return

                # Step 4: 4K Random Read
                dp.update(80, get_string(30306, "Testing 4K Random Read..."))
                rand_read_iops, rand_read_mbs = self._test_4k_random_read(target_filepath, test_size_mb, dp)
                if dp.is_canceled():
                    return

                dp.update(100, get_string(30307, "Disk benchmark completed"))

        finally:
            # Always ensure temporary benchmark file is cleaned up
            self._cleanup_temp_file(target_filepath)

        # Show Results Report
        report_lines = [
            f"=== {get_string(30308, 'Benchmark Report')} ===",
            "",
            f"{get_string(30309, 'Target: %s') % target_dir}",
            f"{get_string(30310, 'Size: %s MB') % test_size_mb}",
            "--------------------------------------------------",
            f"{get_string(30311, 'Sequential Write: %s MB/s') % f'{seq_write_mbs:.2f}'}",
            f"{get_string(30312, 'Sequential Read: %s MB/s') % f'{seq_read_mbs:.2f}'}",
            "--------------------------------------------------",
            f"{get_string(30313, '4K Random Write: %s MB/s (%s IOPS)') % (f'{rand_write_mbs:.2f}', f'{rand_write_iops:.0f}')}",
            f"{get_string(30314, '4K Random Read: %s MB/s (%s IOPS)') % (f'{rand_read_mbs:.2f}', f'{rand_read_iops:.0f}')}",
            "--------------------------------------------------",
        ]
        dialog_textviewer(title, "\n".join(report_lines))

    def _select_target_directory(self, title: str) -> Optional[str]:
        """Ask user to select benchmark target path."""
        home_path = translate_path("special://home/")
        temp_path = translate_path("special://temp/")

        options = [
            get_string(30316, "Kodi Home (%s)") % home_path,
            get_string(30317, "Kodi Temp (%s)") % temp_path,
            get_string(30318, "Browse Custom Directory (USB / SD / External)..."),
        ]

        idx = dialog_select(get_string(30301, "Select storage directory to benchmark"), options)
        if idx == 0:
            return home_path
        elif idx == 1:
            return temp_path
        elif idx == 2:
            custom = dialog_browse(3, get_string(30301, "Select storage directory to benchmark"), "files", "", False, False, home_path)
            if custom and os.path.isdir(custom):
                return custom
        return None

    def _select_test_size(self, title: str) -> Optional[int]:
        """Ask user to select test file size."""
        default_size = get_setting_int("disk_bench_size", 128)
        sizes = [64, 128, 256, 512]
        labels = [f"{s} MB" + (" (Default)" if s == default_size else "") for s in sizes]

        idx = dialog_select(get_string(30302, "Select test file size"), labels)
        if idx >= 0:
            return sizes[idx]
        return None

    def _test_sequential_write(self, filepath: str, size_mb: int, dp) -> float:
        """Write test file sequentially in 1MB chunks with fsync."""
        block_size = 1024 * 1024  # 1 MB
        total_blocks = size_mb
        # Generate non-repetitive pseudorandom block buffer to avoid compression/zero-fill bypass
        random_bytes = bytearray(os.urandom(64 * 1024) * 16)

        t0 = time.perf_counter()
        fd = os.open(filepath, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | O_BINARY)
        try:
            for i in range(total_blocks):
                if dp.is_canceled():
                    break
                os.write(fd, random_bytes)
                if (i + 1) % 4 == 0:
                    pct = 5 + int(((i + 1) / total_blocks) * 25)
                    dp.update(pct, f"Seq Write: {i + 1}/{total_blocks} MB")
            os.fsync(fd)
        finally:
            os.close(fd)

        elapsed = max(0.001, time.perf_counter() - t0)
        return size_mb / elapsed

    def _test_sequential_read(self, filepath: str, dp) -> float:
        """Read test file sequentially in 1MB chunks."""
        block_size = 1024 * 1024
        file_size = os.path.getsize(filepath)
        size_mb = file_size / (1024 * 1024)

        t0 = time.perf_counter()
        fd = os.open(filepath, os.O_RDONLY | O_BINARY)
        if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED"):
            try:
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
            except Exception:
                pass

        bytes_read = 0
        try:
            while bytes_read < file_size:
                if dp.is_canceled():
                    break
                data = os.read(fd, block_size)
                if not data:
                    break
                bytes_read += len(data)
                del data
                pct = 30 + int((bytes_read / file_size) * 25)
                dp.update(pct, f"Seq Read: {bytes_read / (1024 * 1024):.1f}/{size_mb:.1f} MB")
        finally:
            os.close(fd)

        elapsed = max(0.001, time.perf_counter() - t0)
        return (bytes_read / (1024 * 1024)) / elapsed

    def _test_4k_random_write(self, filepath: str, size_mb: int, dp, ops: int = 1000) -> Tuple[float, float]:
        """Perform 4KB random writes at aligned offsets, calculating IOPS and throughput."""
        block_size = 4096
        total_blocks = (size_mb * 1024 * 1024) // block_size
        if total_blocks < 1:
            return 0.0, 0.0

        random_data = os.urandom(block_size)
        fd = os.open(filepath, os.O_RDWR | O_BINARY)

        t0 = time.perf_counter()
        performed = 0
        try:
            for i in range(ops):
                if dp.is_canceled():
                    break
                offset = random.randint(0, total_blocks - 1) * block_size
                os.lseek(fd, offset, os.SEEK_SET)
                os.write(fd, random_data)
                performed += 1
                if (i + 1) % 50 == 0:
                    pct = 55 + int(((i + 1) / ops) * 25)
                    dp.update(pct, f"4K Random Write: {i + 1}/{ops} ops")
            os.fsync(fd)
        finally:
            os.close(fd)

        elapsed = max(0.001, time.perf_counter() - t0)
        iops = performed / elapsed
        mbs = (performed * block_size / (1024 * 1024)) / elapsed
        return iops, mbs

    def _test_4k_random_read(self, filepath: str, size_mb: int, dp, ops: int = 1000) -> Tuple[float, float]:
        """Perform 4KB random reads at aligned offsets, calculating IOPS and throughput."""
        block_size = 4096
        total_blocks = (size_mb * 1024 * 1024) // block_size
        if total_blocks < 1:
            return 0.0, 0.0

        fd = os.open(filepath, os.O_RDONLY | O_BINARY)
        if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED"):
            try:
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
            except Exception:
                pass

        t0 = time.perf_counter()
        performed = 0
        try:
            for i in range(ops):
                if dp.is_canceled():
                    break
                offset = random.randint(0, total_blocks - 1) * block_size
                os.lseek(fd, offset, os.SEEK_SET)
                data = os.read(fd, block_size)
                if not data:
                    break
                del data
                performed += 1
                if (i + 1) % 50 == 0:
                    pct = 80 + int(((i + 1) / ops) * 20)
                    dp.update(pct, f"4K Random Read: {i + 1}/{ops} ops")
        finally:
            os.close(fd)

        elapsed = max(0.001, time.perf_counter() - t0)
        iops = performed / elapsed
        mbs = (performed * block_size / (1024 * 1024)) / elapsed
        return iops, mbs

    def _flush_and_evict_cache(self, filepath: str) -> None:
        """Purge OS PageCache and file blocks to ensure raw hardware read speed."""
        # 1. Sync dirty blocks to physical storage
        run_command("sync")

        # 2. Tell kernel to drop cached pages of this test file
        if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED") and os.path.exists(filepath):
            try:
                fd = os.open(filepath, os.O_RDONLY | O_BINARY)
                try:
                    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                finally:
                    os.close(fd)
            except Exception as e:
                debug(f"posix_fadvise failed: {e}")

        # 3. Drop system-wide pagecache, dentries and inodes
        drop_path = "/proc/sys/vm/drop_caches"
        if os.path.exists(drop_path):
            try:
                with open(drop_path, "w") as f:
                    f.write("3\n")
                debug("Purged kernel drop_caches=3 for disk benchmark")
            except Exception:
                run_command("sysctl -w vm.drop_caches=3")
                run_command("sh -c 'echo 3 > /proc/sys/vm/drop_caches'")

        time.sleep(0.1)

    def _cleanup_temp_file(self, filepath: str) -> None:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                debug(f"Cleaned up benchmark temp file: {filepath}")
        except Exception as e:
            error(f"Failed to remove benchmark file {filepath}: {e}")
