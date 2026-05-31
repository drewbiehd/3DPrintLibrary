import os
import re
from pathlib import Path

SUPPORTED_FORMATS = {".3mf", ".stl", ".obj", ".step", ".stp", ".gcode"}

CATEGORY_KEYWORDS = {
    "Tools": [
        "wrench", "screwdriver", "hammer", "drill", "tool", "clamp", "vise", "plier",
        "socket", "hex", "spanner", "saw", "blade", "cutter", "gauge", "level",
        "bit", "chuck", "jig", "fixture", "caliper", "ruler", "grinder", "chisel",
        "workbench", "workholding", "tap", "die", "punch",
    ],
    "Clicker Toys": [
        "fidget", "clicker", "click", "pop", "sensory", "spinner", "cube",
        "tactile", "stress", "marble", "run", "twiddle", "flex", "infinity",
    ],
    "Toys": [
        "toy", "doll", "car", "truck", "robot", "puzzle", "lego",
        "minecraft", "pokemon", "figurine", "character", "statue",
        "action", "play", "dinosaur", "animal", "dragon", "warhammer",
        "train", "boat", "plane", "kite", "pinwheel", "top", "spinner",
    ],
    "Gaming & Tabletop": [
        "miniature", "mini", "terrain", "dungeon", "d&d", "dnd", "pathfinder",
        "tabletop", "wargame", "base", "scenery", "token", "dice", "tower",
        "tray", "insert", "boardgame", "rpg", "fantasy", "scatter",
        "gundam", "mecha", "figure", "bust",
    ],
    "Cosplay & Props": [
        "cosplay", "prop", "sword", "shield", "armor", "helmet", "mask",
        "weapon", "gun", "pistol", "rifle", "anime", "marvel", "dc",
        "mandalorian", "halo", "starwars", "star wars", "batman", "iron man",
        "costume", "gauntlet", "pauldron", "bracer",
    ],
    "Household": [
        "kitchen", "bathroom", "bedroom", "garage", "living", "pantry",
        "toothbrush", "soap", "towel", "spice", "utensil", "cutting",
        "fridge", "cupboard", "door", "window", "curtain", "lamp",
        "shelf", "picture", "photo", "frame", "vase", "bowl", "cup",
        "plate", "pot", "lid", "strainer", "funnel", "kitchen",
    ],
    "Art & Decor": [
        "art", "sculpture", "statue", "bust", "relief", "logo", "sign",
        "wall", "decor", "decoration", "ornament", "planter", "succulent",
        "vase", "lamp", "light", "candle", "geometric", "abstract",
        "lithophane", "low poly", "lowpoly", "portrait", "nameplate",
    ],
    "Gadgets & Electronics": [
        "phone", "tablet", "headphone", "earphone", "speaker", "camera",
        "gopro", "raspberry", "arduino", "pi", "pcb", "circuit",
        "remote", "charger", "dock", "usb", "hdmi", "cable", "wire",
        "keyboard", "mouse", "monitor", "laptop", "computer", "vr",
        "oculus", "quest", "drone", "rc", "controller", "gamepad",
    ],
    "Utility": [
        "holder", "organizer", "stand", "mount", "bracket",
        "container", "case", "tray", "rack", "hook", "clip", "storage",
        "drawer", "cabinet", "desk", "hanger", "basket", "bin", "pocket",
        "key", "card", "pen", "pencil", "ruler", "cord", "management",
        "label", "tag", "nameplate",
    ],
    "Outdoors & Garden": [
        "garden", "outdoor", "planter", "pot", "flower", "plant",
        "birdhouse", "bird", "feeder", "stake", "fence", "hose",
        "sprinkler", "tool shed", "camping", "tent", "fishing", "hiking",
        "bicycle", "bike", "kayak", "boat", "yard", "patio", "bbq",
        "grill", "solar", "rain",
    ],
    "Fashion & Jewelry": [
        "ring", "bracelet", "necklace", "earring", "pendant", "jewelry",
        "jewel", "crown", "tiara", "brooch", "cufflink", "watch",
        "bag", "purse", "wallet", "belt", "buckle", "button", "clasp",
        "sunglasses", "glasses", "hat", "clip", "hairpin", "fashion",
    ],
    "3D Printer Parts": [
        "prusa", "ender", "voron", "bambu", "creality", "anycubic",
        "hotend", "extruder", "nozzle", "bed", "spool", "filament",
        "fan", "duct", "shroud", "cable chain", "x axis", "y axis",
        "z axis", "carriage", "gantry", "enclosure", "chamber",
        "runout", "sensor", "probe", "bltouch", "cr10", "mk3",
    ],
    "Education": [
        "education", "school", "learn", "science", "math", "model",
        "anatomy", "skeleton", "cell", "molecule", "atom", "dna",
        "geography", "map", "globe", "solar system", "planet",
        "history", "museum", "artifact", "fossil", "geology",
    ],
    "Repairs": [
        "repair", "replacement", "spare", "fix", "broken",
        "hinge", "knob", "handle", "cover", "cap", "plug",
        "foot", "feet", "washer", "spacer", "bushing", "gear",
        "bearing", "spring", "latch", "tab",
    ],
}


def detect_category(filename: str) -> str:
    name = Path(filename).stem.lower()
    name = re.sub(r"[_\-\.\d]+", " ", name)

    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name:
                scores[cat] += 2 if kw in name.split() else 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Uncategorized"


def scan_folder(folder_path: str):
    """Yield (path, filename, format, size) for all supported 3D files."""
    folder = Path(folder_path)
    if not folder.exists():
        return
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext in SUPPORTED_FORMATS:
                full_path = Path(root) / fname
                try:
                    size = full_path.stat().st_size
                    yield str(full_path), fname, ext.lstrip(".").upper(), size
                except OSError:
                    continue
