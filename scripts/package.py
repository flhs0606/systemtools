#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Packaging script to create installable Kodi addon zip file."""

import os
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_XML = os.path.join(ADDON_DIR, "addon.xml")
DIST_DIR = os.path.join(ADDON_DIR, "dist")

EXCLUDE_PATTERNS = [
    r"^\.git",
    r"^\.pytest_cache",
    r"^\.superpowers",
    r"^tests",
    r"^scripts",
    r"^dist",
    r"^build",
    r"^docs",
    r"^plugin\.program\.systemtools",
    r"^__pycache__",
    r"\.py[cod]$",
    r"^\.coverage",
    r"^\.vscode",
    r"^\.idea",
    r"requirements.*\.txt$",
    r"pyproject\.toml$",
    r"CLAUDE\.md$",
    r"\.tmp$",
]


def get_addon_metadata():
    if not os.path.exists(ADDON_XML):
        raise FileNotFoundError(f"Missing {ADDON_XML}")
    tree = ET.parse(ADDON_XML)
    root = tree.getroot()
    addon_id = root.attrib.get("id")
    version = root.attrib.get("version")
    return addon_id, version


def is_excluded(rel_path):
    parts = rel_path.replace("\\", "/").split("/")
    for pattern in EXCLUDE_PATTERNS:
        compiled = re.compile(pattern)
        if compiled.search(rel_path.replace("\\", "/")):
            return True
        for part in parts:
            if compiled.search(part):
                return True
    return False


def build_zip():
    addon_id, version = get_addon_metadata()
    os.makedirs(DIST_DIR, exist_ok=True)
    zip_filename = f"{addon_id}-{version}.zip"
    zip_path = os.path.join(DIST_DIR, zip_filename)

    print(f"Building Kodi addon package: {zip_filename}")
    print(f"Addon ID: {addon_id}, Version: {version}")

    created_dirs = set()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Explicitly write root addon directory entry with standard 0o755 permissions
        root_dir_entry = f"{addon_id}/"
        zinfo_root = zipfile.ZipInfo(root_dir_entry)
        zinfo_root.external_attr = 0o755 << 16
        zf.writestr(zinfo_root, "")
        created_dirs.add(root_dir_entry)

        for root, dirs, files in os.walk(ADDON_DIR):
            dirs[:] = [d for d in dirs if not is_excluded(os.path.relpath(os.path.join(root, d), ADDON_DIR))]
            # Write directory entries
            for d in dirs:
                rel_d = os.path.relpath(os.path.join(root, d), ADDON_DIR)
                archive_dir = os.path.join(addon_id, rel_d).replace("\\", "/") + "/"
                if archive_dir not in created_dirs:
                    zinfo_d = zipfile.ZipInfo(archive_dir)
                    zinfo_d.external_attr = 0o755 << 16
                    zf.writestr(zinfo_d, "")
                    created_dirs.add(archive_dir)

            for file in sorted(files):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, ADDON_DIR)
                if is_excluded(rel_path):
                    continue

                archive_name = os.path.join(addon_id, rel_path).replace("\\", "/")
                with open(abs_path, "rb") as f:
                    file_data = f.read()

                zinfo = zipfile.ZipInfo(archive_name)
                zinfo.date_time = time.localtime(os.path.getmtime(abs_path))[:6]
                zinfo.compress_type = zipfile.ZIP_DEFLATED
                zinfo.external_attr = 0o644 << 16  # standard file permissions
                zf.writestr(zinfo, file_data)
                print(f"  + {archive_name}")

    print(f"\nPackage created successfully: {zip_path}")
    print(f"Size: {os.path.getsize(zip_path) / 1024:.1f} KB")
    return zip_path


if __name__ == "__main__":
    build_zip()
