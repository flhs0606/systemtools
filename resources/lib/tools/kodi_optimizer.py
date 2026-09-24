# -*- coding: utf-8 -*-
"""Tool: Kodi Performance and Rendering Optimizer.

Optimizes SQLite databases and advancedsettings.xml specifically engineered
for large media libraries (tens of thousands of titles) and Mali GPU hardware:
1. SQLite WAL Mode: Configures PRAGMA journal_mode=WAL and synchronous=NORMAL
   across all media databases to enable non-blocking concurrent reads and writes.
2. AdvancedSettings Tuning:
   - Disables asynchronous texture uploads (<asynctextureupload>false</asynctextureupload>)
     to eliminate multithreaded EGL context contention and blocking glFinish() calls.
   - Disables runtime minified mipmap generation (<minifiedmipmapping>false</minifiedmipmapping>)
     to prevent expensive glGenerateMipmap() calls on the main render thread.
   - Enforces cost-reduction dirty region tracking (<algorithmdirtyregions>2</algorithmdirtyregions>)
     to avoid full-viewport redraws when scrolling posters.
   - Caps thumbnail cache resolution (<imageres>540</imageres>, <fanartres>720</fanartres>)
     to conserve RAM and GPU VRAM.
   - Expands SQLite memory page cache (<cache_size>-32768</cache_size>) to keep
     large B-Tree indexes resident in memory.
"""

import glob
import os
import shutil
import sqlite3
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from ..common.kodi_ui import (
    dialog_ok,
    dialog_select,
    dialog_textviewer,
    dialog_yesno,
    get_string,
    progress_dialog,
    show_notification,
    translate_path,
)
from ..common.logger import debug, error, info
from ..common.system_exec import run_command
from .base_tool import BaseTool, ToolRegistry

try:
    import xbmc
    _HAS_XBMC = True
except ImportError:
    _HAS_XBMC = False
    xbmc = None

DEFAULT_CE_USERDATA = "/storage/.kodi/userdata"


def get_default_userdata_dir() -> str:
    """Detect the active Kodi userdata path."""
    if os.path.isdir(DEFAULT_CE_USERDATA):
        return DEFAULT_CE_USERDATA
    try:
        translated = translate_path("special://userdata/")
        if os.path.isdir(translated):
            return translated
    except Exception:
        pass
    return DEFAULT_CE_USERDATA


def update_xml_element(parent: ET.Element, tag: str, text: str) -> None:
    """Helper to update or create a child element with specified text."""
    elem = parent.find(tag)
    if elem is None:
        elem = ET.SubElement(parent, tag)
    elem.text = text


def get_database_files(db_dir: str) -> List[str]:
    """Find all SQLite database files in the Database directory."""
    if not os.path.isdir(db_dir):
        return []
    db_files = glob.glob(os.path.join(db_dir, "*.db"))
    return sorted([f for f in db_files if not f.endswith(".bak")])


def backup_file(file_path: str) -> str:
    """Create a backup copy with .bak extension if not already existing."""
    bak_path = f"{file_path}.bak"
    if not os.path.exists(bak_path) and os.path.exists(file_path):
        try:
            shutil.copy2(file_path, bak_path)
            info(f"Created backup: {bak_path}")
        except Exception as e:
            error(f"Failed to backup {file_path}: {e}")
    return bak_path


@ToolRegistry.register
class KodiOptimizerTool(BaseTool):
    id = "kodi_optimizer"
    title_id = 30900
    description_id = 30901
    icon = "DefaultAddonProgram.png"
    order = 16

    def __init__(self, userdata_path: Optional[str] = None):
        self.userdata_path = userdata_path if userdata_path else get_default_userdata_dir()

    def run(self, params: Dict[str, str]) -> None:
        title = get_string(30900, "Kodi Performance Optimizer")
        info(f"Kodi Optimizer invoked on userdata: {self.userdata_path}")

        options = [
            f"1. {get_string(30902, 'Apply All Performance Optimizations')}",
            f"2. {get_string(30903, 'View Current Optimization Status')}",
            f"3. {get_string(30904, 'Restore Configurations from Backup (.bak)')}",
        ]

        idx = dialog_select(title, options)
        if idx == 0:
            self._action_apply_optimizations(title)
        elif idx == 1:
            self._action_view_status(title)
        elif idx == 2:
            self._action_restore_backups(title)

    def _action_apply_optimizations(self, title: str) -> None:
        # Prompt user for thumbnail resolution preset
        preset_title = get_string(30921, "Select Thumbnail Quality Preset")
        presets = [
            get_string(30922, "1080p Full HD (Recommended, 1:1 pixel crisp, 720p/1080p)"),
            get_string(30923, "Low VRAM Saver (Fast, for low RAM or huge libraries, 540p/720p)"),
            get_string(30924, "4K Ultra HD (For 4GB RAM devices and 4K UI skins, 1080p/2160p)"),
        ]
        p_idx = dialog_select(preset_title, presets)
        if p_idx < 0:
            return

        if p_idx == 0:
            imageres, fanartres = 720, 1080
        elif p_idx == 1:
            imageres, fanartres = 540, 720
        else:
            imageres, fanartres = 1080, 2160

        os.makedirs(self.userdata_path, exist_ok=True)
        db_dir = os.path.join(self.userdata_path, "Database")
        os.makedirs(db_dir, exist_ok=True)

        try:
            with progress_dialog(title, get_string(30905, "Optimizing SQLite databases...")) as dp:
                # 1. Optimize SQLite databases
                dp.update(10, get_string(30905, "Optimizing SQLite databases..."))
                db_count = self.optimize_databases(dp)

                # 2. Optimize advancedsettings.xml with chosen quality preset
                dp.update(70, get_string(30906, "Optimizing advancedsettings.xml..."))
                self.optimize_advancedsettings(imageres=imageres, fanartres=fanartres)

                dp.update(100, get_string(30204, "Completed"))
                time.sleep(0.5)

            msg = get_string(
                30907,
                "Optimizations applied successfully! Restart Kodi/system to take effect. Reboot now?",
            )
            if dialog_yesno(title, msg):
                self._do_restart()

        except Exception as e:
            error(f"Optimization failed: {e}")
            dialog_ok(title, f"Optimization failed: {e}")

    def _action_view_status(self, title: str) -> None:
        report_text = self.get_status_report()
        dialog_textviewer(get_string(30911, "Optimization Status Report"), report_text)

    def _action_restore_backups(self, title: str) -> None:
        confirm_msg = get_string(
            30919,
            "Are you sure you want to restore all databases and settings from .bak backups?",
        )
        if not dialog_yesno(title, confirm_msg):
            return

        restored_count = self.restore_backups()
        if restored_count == 0:
            dialog_ok(title, get_string(30909, "No backup (.bak) files found to restore."))
            return

        show_notification(title, get_string(30920, "Restored %d files successfully.") % restored_count)
        reboot_msg = get_string(
            30910,
            "Backups restored successfully! Restart Kodi to apply. Reboot now?",
        )
        if dialog_yesno(title, reboot_msg):
            self._do_restart()

    def optimize_databases(self, dp=None) -> int:
        """Apply WAL mode, synchronous=NORMAL, and PRAGMA optimize to all SQLite databases."""
        db_dir = os.path.join(self.userdata_path, "Database")
        db_files = get_database_files(db_dir)

        if not db_files:
            info(f"No SQLite database files found in {db_dir}")
            return 0

        total = len(db_files)
        info(f"Optimizing {total} SQLite databases in {db_dir}...")

        for i, db_path in enumerate(db_files):
            if dp and dp.is_canceled():
                break

            db_name = os.path.basename(db_path)
            backup_file(db_path)

            if dp:
                pct = int(10 + (i / max(1, total)) * 55)
                dp.update(pct, f"Optimizing {db_name} (WAL mode)...")

            try:
                conn = sqlite3.connect(db_path, timeout=10.0, isolation_level=None)
                cur = conn.cursor()
                cur.execute("PRAGMA journal_mode = WAL;")
                cur.execute("PRAGMA synchronous = NORMAL;")
                cur.execute("PRAGMA optimize;")
                conn.close()
                info(f"Optimized {db_name}: journal_mode=WAL, synchronous=NORMAL")
            except Exception as e:
                error(f"Failed to optimize {db_name}: {e}")

        return total

    def optimize_advancedsettings(self, imageres: int = 720, fanartres: int = 1080) -> None:
        """Safely merge Mali GPU and SQLite cache optimizations into advancedsettings.xml."""
        as_path = os.path.join(self.userdata_path, "advancedsettings.xml")
        backup_file(as_path)

        root = None
        if os.path.exists(as_path):
            try:
                tree = ET.parse(as_path)
                root = tree.getroot()
            except Exception as e:
                debug(f"Parsing existing advancedsettings.xml failed ({e}), creating fresh root.")
                root = None

        if root is None or root.tag != "advancedsettings":
            root = ET.Element("advancedsettings")

        # 1. Update <gui> section
        gui_elem = root.find("gui")
        if gui_elem is None:
            gui_elem = ET.SubElement(root, "gui")

        # Disable async texture upload to eliminate multithreaded EGL context contention and driver stalls
        update_xml_element(gui_elem, "asynctextureupload", "false")
        # Disable runtime minified mipmapping to eliminate main-thread glGenerateMipmap() calls
        update_xml_element(gui_elem, "minifiedmipmapping", "false")
        # Enforce dirty region solver algorithm 2: COST_REDUCTION (partial updates)
        update_xml_element(gui_elem, "algorithmdirtyregions", "2")
        update_xml_element(gui_elem, "bufferagepartialredraw", "1")
        update_xml_element(gui_elem, "maxdirtyregions", "4")
        # Cap thumbnail cache sizes to save memory while preserving crisp 1080p UI resolution
        update_xml_element(gui_elem, "imageres", str(imageres))
        update_xml_element(gui_elem, "fanartres", str(fanartres))

        # 2. Update <videodatabase> section
        vdb_elem = root.find("videodatabase")
        if vdb_elem is None:
            vdb_elem = ET.SubElement(root, "videodatabase")

        if vdb_elem.find("connecttimeout") is None:
            update_xml_element(vdb_elem, "connecttimeout", "5")
        # Allocate 32MB page cache for SQLite database index lookups (-32768 KB)
        update_xml_element(vdb_elem, "cache_size", "-32768")

        # Format XML nicely with indentation
        try:
            ET.indent(root, space="  ", level=0)
        except AttributeError:
            pass

        out_tree = ET.ElementTree(root)
        out_tree.write(as_path, encoding="utf-8", xml_declaration=True)
        info(f"Optimized advancedsettings.xml written to {as_path}")

    def get_status_report(self) -> str:
        """Generate formatted diagnostic report of databases and settings."""
        lines = [f"=== {get_string(30911, 'Optimization Status Report')} ===", ""]

        db_dir = os.path.join(self.userdata_path, "Database")
        db_files = get_database_files(db_dir)

        opt_str = get_string(30912, "Optimal (WAL)")
        def_str = get_string(30913, "Default (Lock-Prone)")
        not_set_str = get_string(30917, "Not set")

        lines.append(f"[1] {get_string(30914, 'Databases (%d detected):') % len(db_files)}")
        for db_path in db_files:
            name = os.path.basename(db_path)
            try:
                conn = sqlite3.connect(db_path, timeout=5.0, isolation_level=None)
                cur = conn.cursor()
                cur.execute("PRAGMA journal_mode;")
                j_mode = cur.fetchone()[0]
                cur.execute("PRAGMA synchronous;")
                sync_val = cur.fetchone()[0]
                conn.close()

                sync_desc = {0: "OFF", 1: "NORMAL", 2: "FULL", 3: "EXTRA"}.get(sync_val, str(sync_val))
                tag = f"[{opt_str}]" if j_mode.upper() == "WAL" else f"[{def_str}]"
                lines.append(f"  * {name:<20}: journal={j_mode:<5} sync={sync_desc:<7} {tag}")
            except Exception as e:
                lines.append(f"  * {name:<20}: [Error: {e}]")

        lines.append("")
        as_path = os.path.join(self.userdata_path, "advancedsettings.xml")
        lines.append(f"[2] {get_string(30915, 'Rendering & Cache Settings (%s):') % 'advancedsettings.xml'}")

        if not os.path.exists(as_path):
            lines.append(f"  * {get_string(30916, 'File does not exist (using Kodi hardcoded defaults).')}")
        else:
            try:
                tree = ET.parse(as_path)
                root = tree.getroot()
                gui = root.find("gui")
                if gui is not None:
                    async_up = gui.findtext("asynctextureupload", not_set_str)
                    min_mip = gui.findtext("minifiedmipmapping", not_set_str)
                    dirty = gui.findtext("algorithmdirtyregions", not_set_str)
                    imageres = gui.findtext("imageres", not_set_str)
                    fanartres = gui.findtext("fanartres", not_set_str)

                    lines.append(f"  * asynctextureupload    : {async_up:<10} ({get_string(30918, 'Optimal')}: false)")
                    lines.append(f"  * minifiedmipmapping    : {min_mip:<10} ({get_string(30918, 'Optimal')}: false)")
                    lines.append(f"  * algorithmdirtyregions : {dirty:<10} ({get_string(30918, 'Optimal')}: 2)")
                    lines.append(f"  * imageres / fanartres  : {imageres} / {fanartres} ({get_string(30918, 'Optimal')}: 720 / 1080)")

                vdb = root.find("videodatabase")
                if vdb is not None:
                    cache_size = vdb.findtext("cache_size", not_set_str)
                    lines.append(f"  * videodatabase/cache_size : {cache_size:<10} ({get_string(30918, 'Optimal')}: -32768)")
            except Exception as e:
                lines.append(f"  * [Parse Error: {e}]")

        return "\n".join(lines)

    def restore_backups(self) -> int:
        """Restore all databases and advancedsettings.xml from .bak files."""
        db_dir = os.path.join(self.userdata_path, "Database")
        bak_files = glob.glob(os.path.join(db_dir, "*.db.bak"))

        as_path = os.path.join(self.userdata_path, "advancedsettings.xml")
        as_bak = f"{as_path}.bak"
        if os.path.exists(as_bak):
            bak_files.append(as_bak)

        if not bak_files:
            return 0

        restored = 0
        for bak in bak_files:
            orig = bak[:-4]
            try:
                shutil.copy2(bak, orig)
                info(f"Restored: {orig} from {bak}")
                restored += 1
            except Exception as e:
                error(f"Failed to restore {orig}: {e}")

        return restored

    def _do_restart(self) -> None:
        """Restart Kodi or reboot system."""
        run_command("sync")
        if _HAS_XBMC and xbmc:
            try:
                xbmc.restart()
                return
            except Exception:
                pass
        run_command("reboot -f")
