import os
import re
from pathlib import Path

SUPPORTED_FORMATS = {".3mf", ".stl", ".obj", ".step", ".stp", ".gcode"}

# ── Parent-category keywords ───────────────────────────────────────────────────
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Tools": [
        "wrench", "screwdriver", "hammer", "drill", "tool", "clamp", "vise", "plier",
        "socket", "hex", "spanner", "saw", "blade", "cutter", "gauge", "level",
        "bit", "chuck", "jig", "fixture", "caliper", "ruler", "grinder", "chisel",
        "workbench", "workholding", "tap", "die", "punch",
    ],
    "Toys": [
        "toy", "doll", "robot", "lego", "minecraft", "figurine",
        "play", "dinosaur", "animal", "dragon", "train", "boat", "plane",
        "kite", "pinwheel", "top", "fidget", "clicker", "click", "pop", "sensory",
        "spinner", "cube", "marble", "flexi", "articulated", "flexible", "bendy",
        "print in place", "pip", "snake", "fish", "figure", "character", "hero",
        "vehicle", "car", "truck", "puzzle", "brain", "teaser", "maze",
    ],
    "Gaming & Tabletop": [
        "miniature", "mini", "terrain", "dungeon", "d&d", "dnd", "pathfinder",
        "tabletop", "wargame", "base", "scenery", "token", "dice", "tower",
        "insert", "boardgame", "rpg", "fantasy", "scatter",
        "gundam", "mecha", "bust", "warhammer", "40k",
    ],
    "Cosplay & Props": [
        "cosplay", "prop", "sword", "shield", "armor", "helmet", "mask",
        "weapon", "gun", "pistol", "rifle", "anime", "marvel", "dc",
        "mandalorian", "halo", "starwars", "star wars", "batman", "iron man",
        "costume", "gauntlet", "pauldron", "bracer",
    ],
    "Household": [
        "kitchen", "bathroom", "bedroom", "garage", "living", "pantry",
        "toothbrush", "soap", "towel", "spice", "utensil",
        "fridge", "cupboard", "door", "window", "curtain", "lamp",
        "picture", "photo", "frame", "vase", "bowl", "cup",
        "plate", "pot", "lid", "strainer", "funnel",
    ],
    "Art & Decor": [
        "art", "sculpture", "statue", "bust", "relief", "logo", "sign",
        "decor", "decoration", "ornament", "planter", "succulent",
        "lamp", "light", "candle", "geometric", "abstract",
        "lithophane", "low poly", "lowpoly", "portrait", "nameplate",
    ],
    "Gadgets & Electronics": [
        "phone", "tablet", "headphone", "earphone", "speaker", "camera",
        "gopro", "raspberry", "arduino", "pi", "pcb", "circuit",
        "remote", "charger", "dock", "usb", "hdmi",
        "keyboard", "mouse", "monitor", "laptop", "computer", "vr",
        "oculus", "quest", "drone", "rc", "controller", "gamepad",
    ],
    "Utility": [
        "holder", "organizer", "stand", "mount", "bracket",
        "container", "case", "tray", "rack", "hook", "clip", "storage",
        "drawer", "cabinet", "desk", "hanger", "basket", "bin", "pocket",
        "key", "card", "pen", "pencil", "cord", "management",
        "label", "tag",
    ],
    "Outdoors & Garden": [
        "garden", "outdoor", "planter", "pot", "flower", "plant",
        "birdhouse", "bird", "feeder", "stake", "fence", "hose",
        "camping", "tent", "fishing", "hiking",
        "bicycle", "bike", "kayak", "yard", "patio", "bbq",
        "grill", "solar", "rain",
    ],
    "Fashion & Jewelry": [
        "ring", "bracelet", "necklace", "earring", "pendant", "jewelry",
        "jewel", "crown", "tiara", "brooch", "cufflink", "watch",
        "bag", "purse", "wallet", "belt", "buckle", "button", "clasp",
        "sunglasses", "glasses", "hat", "hairpin", "fashion",
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

# ── Subcategory keywords — keyed by (parent, subcategory) ─────────────────────
SUBCATEGORY_KEYWORDS: dict[tuple[str, str], list[str]] = {
    # Toys
    ("Toys", "Clicker Toys"):       ["fidget", "clicker", "click", "pop", "sensory",
                                     "stress", "tactile", "twiddle"],
    ("Toys", "Flexi & Articulated"): ["flexi", "articulated", "flexible", "bendy",
                                      "print in place", "pip", "dragon", "snake", "fish",
                                      "articulate"],
    ("Toys", "Action Figures"):     ["figure", "character", "hero", "marvel", "dc",
                                     "batman", "spiderman", "figurine", "action"],
    ("Toys", "Vehicles"):           ["car", "truck", "train", "boat", "plane", "vehicle",
                                     "bus", "tank", "helicopter", "rocket"],
    ("Toys", "Puzzles"):            ["puzzle", "brain", "teaser", "cube", "maze",
                                     "lock", "trick", "jigsaw"],
    ("Toys", "Animals & Creatures"): ["animal", "dinosaur", "cat", "dog", "bird",
                                       "lion", "tiger", "elephant", "horse", "creature"],
    # Gaming & Tabletop
    ("Gaming & Tabletop", "Miniatures"):       ["miniature", "mini", "bust", "warhammer",
                                                "40k", "d&d", "dnd", "figure"],
    ("Gaming & Tabletop", "Terrain & Scenery"): ["terrain", "scenery", "dungeon",
                                                  "castle", "wall", "tower", "tree",
                                                  "hill", "scatter", "base"],
    ("Gaming & Tabletop", "Dice & Accessories"): ["dice", "d20", "d6", "d12", "d4",
                                                   "tower", "tray"],
    ("Gaming & Tabletop", "Board Game Inserts"): ["insert", "organizer", "token",
                                                   "board", "game", "storage"],
    # Cosplay & Props
    ("Cosplay & Props", "Weapons & Props"):   ["sword", "gun", "pistol", "rifle",
                                               "shield", "weapon", "prop"],
    ("Cosplay & Props", "Armor & Wearables"): ["armor", "helmet", "gauntlet",
                                               "pauldron", "bracer", "chest",
                                               "wearable", "costume"],
    ("Cosplay & Props", "Movie & TV"):        ["mandalorian", "halo", "starwars",
                                               "batman", "iron man", "marvel",
                                               "dc", "anime"],
    # Household
    ("Household", "Kitchen"):          ["kitchen", "spice", "utensil", "pot", "lid",
                                        "strainer", "funnel", "cup", "bowl", "plate"],
    ("Household", "Bathroom"):         ["bathroom", "toothbrush", "soap", "towel",
                                        "shower", "toilet", "mirror"],
    ("Household", "Storage & Org"):    ["storage", "organizer", "drawer", "cabinet",
                                        "shelf", "bin", "rack", "pantry"],
    ("Household", "Garage & Workshop"): ["garage", "workshop", "tool", "pegboard",
                                          "workbench", "clamp", "vise"],
    # Art & Decor
    ("Art & Decor", "Sculptures & Busts"): ["sculpture", "statue", "bust", "figure",
                                             "relief", "portrait"],
    ("Art & Decor", "Wall Art"):       ["wall", "art", "decor", "sign", "logo",
                                        "nameplate", "lithophane", "frame"],
    ("Art & Decor", "Vases & Planters"): ["vase", "planter", "pot", "succulent",
                                           "flower", "plant"],
    # Tools
    ("Tools", "Hand Tools"):     ["wrench", "screwdriver", "hammer", "plier",
                                   "socket", "hex", "spanner"],
    ("Tools", "Workshop & Jigs"): ["jig", "fixture", "clamp", "vise", "workholding",
                                    "workbench", "chuck"],
    ("Tools", "Measuring"):      ["caliper", "ruler", "gauge", "level", "measure",
                                   "template"],
    # 3D Printer Parts
    ("3D Printer Parts", "Bambu / Orca"):    ["bambu", "orca", "x1", "p1", "a1"],
    ("3D Printer Parts", "Prusa"):           ["prusa", "mk3", "mk4", "mini", "xl"],
    ("3D Printer Parts", "Creality / Ender"): ["creality", "ender", "cr10", "cr-10",
                                               "k1", "sermoon"],
    ("3D Printer Parts", "Voron"):           ["voron", "trident", "switchwire",
                                              "v0", "v2"],
    ("3D Printer Parts", "General Upgrades"): ["hotend", "extruder", "nozzle",
                                                "fan", "duct", "shroud", "enclosure",
                                                "spool", "runout"],
    # Gadgets & Electronics
    ("Gadgets & Electronics", "Phone & Tablet"):   ["phone", "tablet", "iphone",
                                                    "android", "ipad", "stand"],
    ("Gadgets & Electronics", "PC & Peripherals"): ["keyboard", "mouse", "monitor",
                                                     "pc", "computer", "hdmi", "usb"],
    ("Gadgets & Electronics", "Arduino & Pi"):     ["arduino", "raspberry", "pi",
                                                    "esp32", "esp8266", "pcb",
                                                    "circuit"],
    ("Gadgets & Electronics", "Audio"):            ["speaker", "headphone", "earphone",
                                                    "audio", "amp", "microphone"],
}


def _score_keywords(name: str, keywords: list[str]) -> int:
    words = name.split()
    score = 0
    for kw in keywords:
        if kw in name:
            score += 2 if kw in words else 1
    return score


def detect_category(filename: str) -> tuple[str, str]:
    """
    Return (parent_category, subcategory) for a filename.
    subcategory is "" if no subcategory matched.
    """
    name = Path(filename).stem.lower()
    name = re.sub(r"[_\-\.\d]+", " ", name).strip()

    # 1 — Score all parent categories
    parent_scores = {cat: _score_keywords(name, kws)
                     for cat, kws in CATEGORY_KEYWORDS.items()}
    best_parent = max(parent_scores, key=parent_scores.get)
    if parent_scores[best_parent] == 0:
        return "Uncategorized", ""

    # 2 — Within the winning parent, score its subcategories
    sub_scores = {
        sub: _score_keywords(name, kws)
        for (cat, sub), kws in SUBCATEGORY_KEYWORDS.items()
        if cat == best_parent
    }
    if sub_scores:
        best_sub = max(sub_scores, key=sub_scores.get)
        if sub_scores[best_sub] > 0:
            return best_parent, best_sub

    return best_parent, ""


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
