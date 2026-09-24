# -*- coding: utf-8 -*-
"""Unit tests for Kodi Performance Optimizer tool."""

import os
import sqlite3
import xml.etree.ElementTree as ET

from resources.lib.tools.kodi_optimizer import (
    KodiOptimizerTool,
    backup_file,
    get_database_files,
)


def create_dummy_db(db_path: str):
    """Helper to create a test SQLite database."""
    conn = sqlite3.connect(db_path, isolation_level=None)
    cur = conn.cursor()
    cur.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, title TEXT);")
    cur.execute("INSERT INTO test (title) VALUES ('Movie 1');")
    # Set default journal_mode to delete
    cur.execute("PRAGMA journal_mode = DELETE;")
    cur.execute("PRAGMA synchronous = FULL;")
    conn.close()


def test_optimize_databases(tmp_path):
    userdata = str(tmp_path / "userdata")
    db_dir = os.path.join(userdata, "Database")
    os.makedirs(db_dir, exist_ok=True)

    db1 = os.path.join(db_dir, "MyVideos119.db")
    db2 = os.path.join(db_dir, "Textures13.db")
    create_dummy_db(db1)
    create_dummy_db(db2)

    tool = KodiOptimizerTool(userdata_path=userdata)

    # Run database optimizations
    count = tool.optimize_databases()
    assert count == 2

    # Verify backups exist
    assert os.path.exists(f"{db1}.bak")
    assert os.path.exists(f"{db2}.bak")

    # Verify WAL mode on db1
    conn = sqlite3.connect(db1)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    j_mode = cur.fetchone()[0]
    conn.close()

    assert j_mode.lower() == "wal"


def test_optimize_advancedsettings(tmp_path):
    userdata = str(tmp_path / "userdata")
    os.makedirs(userdata, exist_ok=True)

    tool = KodiOptimizerTool(userdata_path=userdata)
    tool.optimize_advancedsettings()

    as_path = os.path.join(userdata, "advancedsettings.xml")
    assert os.path.exists(as_path)

    tree = ET.parse(as_path)
    root = tree.getroot()
    assert root.tag == "advancedsettings"

    # Verify <gui> settings
    gui = root.find("gui")
    assert gui is not None
    assert gui.findtext("asynctextureupload") == "false"
    assert gui.findtext("minifiedmipmapping") == "false"
    assert gui.findtext("algorithmdirtyregions") == "2"
    assert gui.findtext("imageres") == "720"
    assert gui.findtext("fanartres") == "1080"

    # Verify <videodatabase> settings
    vdb = root.find("videodatabase")
    assert vdb is not None
    assert vdb.findtext("cache_size") == "-32768"


def test_get_status_report(tmp_path):
    userdata = str(tmp_path / "userdata")
    db_dir = os.path.join(userdata, "Database")
    os.makedirs(db_dir, exist_ok=True)

    db_file = os.path.join(db_dir, "MyVideos119.db")
    create_dummy_db(db_file)

    tool = KodiOptimizerTool(userdata_path=userdata)
    tool.optimize_databases()
    tool.optimize_advancedsettings()

    report = tool.get_status_report()
    assert "MyVideos119.db" in report
    assert "asynctextureupload" in report
    assert "algorithmdirtyregions" in report


def test_restore_backups(tmp_path):
    userdata = str(tmp_path / "userdata")
    db_dir = os.path.join(userdata, "Database")
    os.makedirs(db_dir, exist_ok=True)

    db_file = os.path.join(db_dir, "MyVideos119.db")
    create_dummy_db(db_file)

    # Create an initial advancedsettings.xml so a .bak is produced during optimization
    as_file = os.path.join(userdata, "advancedsettings.xml")
    with open(as_file, "w", encoding="utf-8") as f:
        f.write("<advancedsettings><gui><imageres>1080</imageres></gui></advancedsettings>")

    tool = KodiOptimizerTool(userdata_path=userdata)
    tool.optimize_databases()
    tool.optimize_advancedsettings()

    # Now restore from backup
    restored = tool.restore_backups()
    assert restored >= 2  # db and advancedsettings
