import re
import subprocess
import zipfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Slicer profiles ───────────────────────────────────────────────────────────
# Each entry: display name → dict with
#   exe       : the executable filename(s) to look for inside an install folder
#   reg_names : substrings to match against registry DisplayName values
#   hints     : extra hardcoded candidate paths (use {pf}, {pf86}, {local},
#               {roaming}, {user} as placeholders resolved at runtime)

SLICER_PROFILES: dict[str, dict] = {
    "OrcaSlicer": {
        "exe": ["OrcaSlicer.exe"],
        "reg_names": ["OrcaSlicer", "Orca Slicer"],
        "hints": [
            r"{pf}\OrcaSlicer\OrcaSlicer.exe",
            r"{pf86}\OrcaSlicer\OrcaSlicer.exe",
            r"{local}\OrcaSlicer\OrcaSlicer.exe",
            r"{local}\Programs\OrcaSlicer\OrcaSlicer.exe",
        ],
    },
    "Bambu Studio": {
        "exe": ["bambu-studio.exe", "BambuStudio.exe"],
        "reg_names": ["Bambu Studio", "BambuStudio"],
        "hints": [
            r"{pf}\Bambu Studio\bambu-studio.exe",
            r"{pf86}\Bambu Studio\bambu-studio.exe",
            r"{local}\Bambu Studio\bambu-studio.exe",
            r"{local}\Programs\Bambu Studio\bambu-studio.exe",
        ],
    },
    "PrusaSlicer": {
        "exe": ["prusa-slicer.exe", "PrusaSlicer.exe"],
        "reg_names": ["PrusaSlicer", "Prusa Slicer"],
        "hints": [
            r"{pf}\PrusaSlicer\prusa-slicer.exe",
            r"{pf86}\PrusaSlicer\prusa-slicer.exe",
            r"{local}\PrusaSlicer\prusa-slicer.exe",
        ],
    },
    "UltiMaker Cura": {
        "exe": ["UltiMaker-Cura.exe", "Cura.exe"],
        "reg_names": ["UltiMaker Cura", "Ultimaker Cura", "Cura"],
        "hints": [
            r"{pf}\UltiMaker Cura\UltiMaker-Cura.exe",
            r"{pf}\Ultimaker Cura\UltiMaker-Cura.exe",
            r"{pf86}\UltiMaker Cura\UltiMaker-Cura.exe",
            r"{local}\Programs\Cura\UltiMaker-Cura.exe",
        ],
    },
    "Snapmaker Luban": {
        "exe": ["Snapmaker Luban.exe", "snapmaker-luban.exe"],
        "reg_names": ["Snapmaker Luban", "Luban"],
        "hints": [
            r"{pf}\Snapmaker Luban\Snapmaker Luban.exe",
            r"{pf86}\Snapmaker Luban\Snapmaker Luban.exe",
            r"{local}\Programs\Snapmaker Luban\Snapmaker Luban.exe",
        ],
    },
    "Creality Print": {
        "exe": ["Creality Print.exe", "CrealityPrint.exe"],
        "reg_names": ["Creality Print"],
        "hints": [
            r"{pf}\Creality Print\Creality Print.exe",
            r"{pf86}\Creality Print\Creality Print.exe",
            r"{local}\Creality Print\Creality Print.exe",
        ],
    },
    "Chitubox": {
        "exe": ["CHITUBOX.exe"],
        "reg_names": ["CHITUBOX", "Chitubox"],
        "hints": [
            r"{pf}\CBD-Tech\CHITUBOX\CHITUBOX.exe",
            r"{pf86}\CBD-Tech\CHITUBOX\CHITUBOX.exe",
            r"{local}\Programs\CHITUBOX\CHITUBOX.exe",
        ],
    },
    "Lychee Slicer": {
        "exe": ["Lychee Slicer.exe", "lychee-slicer.exe"],
        "reg_names": ["Lychee Slicer", "LycheeSlicer"],
        "hints": [
            r"{pf}\Lychee Slicer\Lychee Slicer.exe",
            r"{local}\Programs\Lychee Slicer\Lychee Slicer.exe",
        ],
    },
    "FlashPrint": {
        "exe": ["FlashPrint.exe"],
        "reg_names": ["FlashPrint", "Flash Print"],
        "hints": [
            r"{pf}\FlashForge\FlashPrint\FlashPrint.exe",
            r"{pf86}\FlashForge\FlashPrint\FlashPrint.exe",
            r"{pf}\FlashPrint\FlashPrint.exe",
        ],
    },
    "Anycubic Photon Workshop": {
        "exe": ["PhotonWorkshop.exe", "Photon Workshop.exe"],
        "reg_names": ["Photon Workshop", "AnycubicPhotonWorkshop"],
        "hints": [
            r"{pf}\Anycubic\Photon Workshop\PhotonWorkshop.exe",
            r"{pf86}\Anycubic\Photon Workshop\PhotonWorkshop.exe",
        ],
    },
    "ideaMaker": {
        "exe": ["ideaMaker.exe"],
        "reg_names": ["ideaMaker", "IdeaMaker"],
        "hints": [
            r"{pf}\Raise3D\ideaMaker\ideaMaker.exe",
            r"{pf86}\Raise3D\ideaMaker\ideaMaker.exe",
        ],
    },
    "Simplify3D": {
        "exe": ["Simplify3D.exe"],
        "reg_names": ["Simplify3D"],
        "hints": [
            r"{pf}\Simplify3D\Simplify3D.exe",
            r"{pf86}\Simplify3D\Simplify3D.exe",
        ],
    },
    "SuperSlicer": {
        "exe": ["superslicer.exe", "SuperSlicer.exe"],
        "reg_names": ["SuperSlicer", "Super Slicer"],
        "hints": [
            r"{pf}\SuperSlicer\superslicer.exe",
            r"{local}\SuperSlicer\superslicer.exe",
        ],
    },
}

# ── Settings files to STRIP when doing an import ──────────────────────────────
# We use a KEEP-LIST approach instead of a blocklist of exact names, because
# slicer forks (Snapmaker Orca, Bambu Studio, PrusaSlicer, SuperSlicer …) all
# name their profile bundles slightly differently and add new ones over time.
#
# Rule: inside Metadata/, drop EVERY *.config file EXCEPT the handful that hold
# model structure (object/extruder/color assignments). That guarantees no
# printer / filament / process profile survives, no matter what a fork calls it,
# while the geometry + painted-color data (which lives in 3D/*.model and
# model_settings.config) is preserved.

# The ONLY .config files we keep — these describe the model, not the printer.
_KEEP_CONFIG_BASENAMES: set[str] = {
    "model_settings.config",        # per-object extruder slots, modifier flags
    "Slic3r_PE_model.config",       # PrusaSlicer equivalent of the above
    "cut_information.config",        # cut/connector geometry (model data)
}

# File extensions to always drop (compiled G-code — large and useless here)
_STRIP_SUFFIXES: tuple[str, ...] = (".gcode", ".gcode.md5")

# Non-.config settings artefacts to drop by exact name.
_STRIP_EXACT: set[str] = {
    "Metadata/layer_heights_profile.txt",  # adaptive layer heights
    "Metadata/layer_config_ranges.xml",    # per-layer config overrides
    "Metadata/filament_sequence.json",     # filament usage order
}


def _should_strip(filename: str) -> bool:
    """Return True if this ZIP entry should be omitted from an import copy."""
    norm = filename.replace("\\", "/")
    base = norm.rsplit("/", 1)[-1]

    if norm in _STRIP_EXACT:
        return True

    for suffix in _STRIP_SUFFIXES:
        if norm.endswith(suffix):
            return True

    # Any .config file is a settings bundle UNLESS it's an explicit keeper.
    if base.endswith(".config") and base not in _KEEP_CONFIG_BASENAMES:
        return True

    return False


def strip_3mf_settings(three_mf_path: str) -> str | None:
    """
    Produce a temp 3MF file that is identical to *three_mf_path* except that
    all printer / filament / process config entries are removed.

    What is KEPT (so the import is lossless for the modeller):
      • 3D/3dmodel.model — all geometry AND every paint_color / face_property /
        custom_supports / custom_seam attribute on <triangle> elements (this is
        where OrcaSlicer/Bambu store brush-painted color sections)
      • Metadata/model_settings.config — per-object extruder slot assignments
        and modifier-mesh flags
      • Metadata/plate_*.json — plate layout / object positions
      • Thumbnails, relationship files, content-type manifest

    What is STRIPPED (so the slicer uses YOUR current settings):
      • project_settings.config / print_profile.config — printer + filament +
        process profiles that would override everything when opened as a project
      • filament_settings_*.config, machine_settings_*.config,
        process_settings_*.config — per-slot profile overrides
      • slice_info.config, layer_heights_profile.txt, *.gcode — artefacts from
        the last slice, not relevant to importing

    Returns the temp file path on success, or None if the ZIP couldn't be read.
    """
    try:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".3mf",
            prefix="3dpl_import_",
            delete=False,
        )
        tmp_path = tmp.name
        tmp.close()

        with zipfile.ZipFile(three_mf_path, "r") as src:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as dst:
                for item in src.infolist():
                    if not _should_strip(item.filename):
                        dst.writestr(item, src.read(item.filename))

        return tmp_path

    except Exception:
        return None


def inspect_3mf(three_mf_path: str) -> dict:
    """
    Quick scan of a 3MF to report what model features it contains.
    Used by the UI to show an informational badge on cards — not for gating
    behaviour (since import mode now preserves all of these).

    Returns:
      has_painted_colors  : bool
      has_multi_extruder  : bool
      has_modifiers       : bool
      object_count        : int
    """
    NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    result = {
        "has_painted_colors": False,
        "has_multi_extruder": False,
        "has_modifiers": False,
        "object_count": 0,
    }

    try:
        with zipfile.ZipFile(three_mf_path, "r") as z:
            names = z.namelist()

            # ── geometry / paint data lives in the .model file ──────────
            for mf in (n for n in names if n.endswith(".model")):
                try:
                    root = ET.fromstring(z.read(mf))
                except ET.ParseError:
                    continue

                objects = list(root.iter(f"{{{NS}}}object"))
                result["object_count"] += len(objects)

                for tri in root.iter(f"{{{NS}}}triangle"):
                    # paint_color is the Bambu/Orca face-painting attribute
                    if tri.get("paint_color") or tri.get("pid") or tri.get("p1"):
                        result["has_painted_colors"] = True
                        break

            # ── extruder assignments and modifier flags in model_settings ─
            for cfg_name in ("Metadata/model_settings.config",
                             "Metadata/Slic3r_PE_model.config"):
                if cfg_name not in names:
                    continue
                try:
                    text = z.read(cfg_name).decode("utf-8", errors="ignore")
                    ids = set(re.findall(r'extruder(?:_id)?=["\'](\d+)["\']', text))
                    if len(ids) > 1:
                        result["has_multi_extruder"] = True
                    if "modifier" in text.lower():
                        result["has_modifiers"] = True
                except Exception:
                    pass

    except Exception:
        pass

    return result


def open_in_slicer(
    file_path: str,
    slicer_exe: str,
    import_mode: bool = False,
) -> str | None:
    """
    Send *file_path* to the slicer at *slicer_exe*.

    import_mode=True  (default for 3MF from the UI button)
        Creates a settings-stripped copy of the 3MF and sends that.
        Geometry, painted colors, multi-material assignments, and modifier
        meshes are all preserved.  Printer / filament / process profiles are
        removed so the slicer keeps your current settings.

    import_mode=False  (right-click → "Open as Project")
        Passes the original file unchanged.  The slicer loads everything —
        colors AND printer/filament settings — exactly as saved.

    Returns None on success, or an error string on failure.
    """
    send_path = file_path

    if import_mode and file_path.lower().endswith(".3mf"):
        stripped = strip_3mf_settings(file_path)
        if stripped:
            send_path = stripped
        # If stripping failed, fall back to the original file

    try:
        subprocess.Popen([slicer_exe, send_path])
        return None
    except FileNotFoundError:
        return f"Slicer not found: {slicer_exe}"
    except Exception as e:
        return str(e)


def detect_slicers() -> dict[str, str]:
    """
    Auto-detect installed slicers using three strategies, tried in order:

    1. Windows Registry — reads HKLM and HKCU Uninstall keys to find the
       InstallLocation of any registered application whose DisplayName matches
       a known slicer.  Most reliable: works regardless of where the user chose
       to install.

    2. Hardcoded path hints — checks the common default install directories for
       each slicer (Program Files, Program Files (x86), AppData\\Local …).

    3. Common drive roots — scans C:\\ and D:\\ top-level folders for any
       directory whose name matches a slicer, then looks for the expected .exe
       inside.  Catches portable / custom installs.

    Returns {display_name: absolute_exe_path} for every slicer found.
    """
    import os

    found: dict[str, str] = {}

    # ── Resolve environment-variable placeholders ──────────────────────────
    pf     = os.environ.get("ProgramFiles",         r"C:\Program Files")
    pf86   = os.environ.get("ProgramFiles(x86)",    r"C:\Program Files (x86)")
    local  = os.environ.get("LOCALAPPDATA",         "")
    roaming = os.environ.get("APPDATA",             "")
    user   = os.environ.get("USERPROFILE",          "")

    def _resolve(p: str) -> str:
        return (p.replace("{pf}",     pf)
                  .replace("{pf86}",  pf86)
                  .replace("{local}", local)
                  .replace("{roaming}", roaming)
                  .replace("{user}",  user))

    # ── Strategy 1: Windows Registry ──────────────────────────────────────
    try:
        import winreg

        reg_roots = [
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        def _read_str(key, value_name: str) -> str:
            try:
                return winreg.QueryValueEx(key, value_name)[0] or ""
            except OSError:
                return ""

        for hive, subkey in reg_roots:
            try:
                root_key = winreg.OpenKey(hive, subkey)
            except OSError:
                continue

            idx = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(root_key, idx)
                    idx += 1
                except OSError:
                    break

                try:
                    sub_key = winreg.OpenKey(root_key, sub_name)
                except OSError:
                    continue

                display_name  = _read_str(sub_key, "DisplayName")
                install_loc   = _read_str(sub_key, "InstallLocation").strip().rstrip("\\")
                install_loc2  = _read_str(sub_key, "InstallDir").strip().rstrip("\\")

                for slicer_name, profile in SLICER_PROFILES.items():
                    if slicer_name in found:
                        continue
                    # Check if registry DisplayName matches any of our keywords
                    dn_lower = display_name.lower()
                    if not any(kw.lower() in dn_lower for kw in profile["reg_names"]):
                        continue

                    # Try each known exe inside the install folder
                    for folder in filter(None, [install_loc, install_loc2]):
                        for exe in profile["exe"]:
                            candidate = Path(folder) / exe
                            if candidate.exists():
                                found[slicer_name] = str(candidate)
                                break
                        if slicer_name in found:
                            break

                winreg.CloseKey(sub_key)

            winreg.CloseKey(root_key)

    except Exception:
        pass  # winreg unavailable (non-Windows), skip

    # ── Strategy 2: Hardcoded path hints ──────────────────────────────────
    for slicer_name, profile in SLICER_PROFILES.items():
        if slicer_name in found:
            continue
        for hint in profile.get("hints", []):
            candidate = Path(_resolve(hint))
            if candidate.exists():
                found[slicer_name] = str(candidate)
                break

    # ── Strategy 3: Scan common drive roots ───────────────────────────────
    # Check top-level dirs on C:\ and D:\ for folder names that look like
    # a slicer, then see if the expected .exe is inside.
    scan_roots = [Path("C:\\"), Path("D:\\")]
    for slicer_name, profile in SLICER_PROFILES.items():
        if slicer_name in found:
            continue
        for root in scan_roots:
            if not root.exists():
                continue
            try:
                for entry in root.iterdir():
                    if not entry.is_dir():
                        continue
                    entry_lower = entry.name.lower()
                    if not any(kw.lower() in entry_lower
                               for kw in profile["reg_names"]):
                        continue
                    for exe in profile["exe"]:
                        candidate = entry / exe
                        if candidate.exists():
                            found[slicer_name] = str(candidate)
                            break
                    if slicer_name in found:
                        break
            except PermissionError:
                continue

    return found
