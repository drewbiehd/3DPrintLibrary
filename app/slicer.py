import re
import subprocess
import zipfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

KNOWN_SLICERS = {
    "OrcaSlicer": [
        r"C:\Program Files\OrcaSlicer\OrcaSlicer.exe",
        r"C:\Program Files (x86)\OrcaSlicer\OrcaSlicer.exe",
        r"C:\Users\{user}\AppData\Local\OrcaSlicer\OrcaSlicer.exe",
    ],
    "Bambu Studio": [
        r"C:\Program Files\Bambu Studio\bambu-studio.exe",
        r"C:\Program Files (x86)\Bambu Studio\bambu-studio.exe",
    ],
    "Snapmaker Luban": [
        r"C:\Program Files\Snapmaker Luban\Snapmaker Luban.exe",
        r"C:\Program Files (x86)\Snapmaker Luban\Snapmaker Luban.exe",
    ],
    "PrusaSlicer": [
        r"C:\Program Files\PrusaSlicer\prusa-slicer.exe",
        r"C:\Program Files (x86)\PrusaSlicer\prusa-slicer.exe",
    ],
    "UltiMaker Cura": [
        r"C:\Program Files\UltiMaker Cura\UltiMaker-Cura.exe",
        r"C:\Program Files\Ultimaker Cura\UltiMaker-Cura.exe",
    ],
    "Creality Print": [
        r"C:\Program Files\Creality Print\Creality Print.exe",
        r"C:\Program Files (x86)\Creality Print\Creality Print.exe",
    ],
    "Chitubox": [
        r"C:\Program Files\CBD-Tech\CHITUBOX\CHITUBOX.exe",
    ],
}

# ── Settings files to STRIP when doing an import ──────────────────────────────
# These contain printer / filament / process profiles that override slicer
# settings when the file is "opened as project".  Everything else — especially
# 3D/3dmodel.model (geometry + all paint_color / face_property triangle
# attributes) and model_settings.config (per-object extruder slot assignments)
# — is kept intact so colors and multi-material structure survive the import.

# Exact filenames to drop (Bambu/Orca and PrusaSlicer variants)
_STRIP_EXACT: set[str] = {
    "Metadata/project_settings.config",   # Bambu / Orca — master profile bundle
    "Metadata/print_profile.config",       # OrcaSlicer alternate name
    "Metadata/slice_info.config",          # last-slice metadata, not needed
    "Metadata/Slic3r_PE.config",           # PrusaSlicer / SuperSlicer profiles
    "Metadata/layer_heights_profile.txt",  # adaptive layer heights
    "Metadata/layer_config_ranges.xml",    # per-layer config overrides
    "Metadata/filament_sequence.json",     # filament usage order
}

# Filename prefixes to drop (numbered per-plate / per-material configs)
_STRIP_PREFIXES: tuple[str, ...] = (
    "Metadata/filament_settings_",   # filament_settings_0.config …
    "Metadata/machine_settings_",    # machine_settings_0.config …
    "Metadata/process_settings_",    # process_settings_0.config …
)

# File extensions to always drop (compiled G-code — large and useless here)
_STRIP_SUFFIXES: tuple[str, ...] = (".gcode",)


def _should_strip(filename: str) -> bool:
    """Return True if this ZIP entry should be omitted from an import copy."""
    if filename in _STRIP_EXACT:
        return True
    for prefix in _STRIP_PREFIXES:
        if filename.startswith(prefix):
            return True
    for suffix in _STRIP_SUFFIXES:
        if filename.endswith(suffix):
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
    """Auto-detect installed slicers. Returns {name: path}."""
    import os
    username = os.environ.get("USERNAME", "")
    found = {}
    for name, paths in KNOWN_SLICERS.items():
        for p in paths:
            resolved = p.replace("{user}", username)
            if Path(resolved).exists():
                found[name] = resolved
                break
    return found
