import re
import threading
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

THUMB_DIR = Path.home() / ".3dprintlibrary" / "thumbnails"
THUMB_SIZE = (240, 240)
_search_lock = threading.Lock()
# Cap STL file size to avoid freezing on huge meshes (50 MB)
STL_SIZE_LIMIT = 50 * 1024 * 1024


def get_thumb_path(file_path: str) -> Path:
    import hashlib
    h = hashlib.md5(file_path.encode()).hexdigest()
    return THUMB_DIR / f"{h}.png"


def extract_3mf_thumbnail(file_path: str):
    import zipfile
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            names = z.namelist()
            candidates = [
                n for n in names
                if "thumbnail" in n.lower() and n.lower().endswith((".png", ".jpg", ".jpeg"))
            ]
            # Also check standard paths even without 'thumbnail' in name
            for std in ("Metadata/thumbnail.png", "thumbnail.png", ".thumbnail/thumbnail.png"):
                if std in names and std not in candidates:
                    candidates.insert(0, std)
            for candidate in candidates:
                try:
                    data = z.read(candidate)
                    if PIL_AVAILABLE:
                        img = Image.open(BytesIO(data)).convert("RGB")
                        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                        return img
                except Exception:
                    continue
    except Exception:
        pass
    return None


def render_stl_thumbnail(file_path: str):
    """Render STL to thumbnail via matplotlib. Returns PIL Image or None."""
    try:
        import os
        if os.path.getsize(file_path) > STL_SIZE_LIMIT:
            return None

        from stl import mesh as stl_mesh
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        import numpy as np

        m = stl_mesh.Mesh.from_file(file_path)
        vectors = m.vectors

        # Subsample for large meshes
        if len(vectors) > 30000:
            idx = np.random.choice(len(vectors), 30000, replace=False)
            vectors = vectors[idx]

        fig = plt.figure(figsize=(2.4, 2.4), dpi=100, facecolor="#1e2d3d")
        ax = fig.add_subplot(111, projection="3d", facecolor="#1e2d3d")

        poly = Poly3DCollection(vectors, alpha=0.88)
        poly.set_facecolor("#4a9eff")
        poly.set_edgecolor("#1a4a7a")
        ax.add_collection3d(poly)

        pts = m.points.flatten()
        mid = (pts.max() + pts.min()) / 2
        rng = max((pts.max() - pts.min()) / 2, 0.001)
        ax.set_xlim(mid - rng, mid + rng)
        ax.set_ylim(mid - rng, mid + rng)
        ax.set_zlim(mid - rng, mid + rng)

        ax.view_init(elev=30, azim=45)
        ax.set_axis_off()
        fig.tight_layout(pad=0)

        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight",
                    facecolor="#1e2d3d", pad_inches=0)
        plt.close(fig)
        buf.seek(0)

        if PIL_AVAILABLE:
            img = Image.open(buf).convert("RGB")
            img.thumbnail(THUMB_SIZE, Image.LANCZOS)
            return img
    except Exception:
        pass
    return None


def search_image_online(filename: str):
    """Search DuckDuckGo images for a preview. Returns PIL Image or None."""
    try:
        from duckduckgo_search import DDGS
        import requests

        name = Path(filename).stem
        name = re.sub(r"[_\-\.\d]+", " ", name).strip()
        if len(name) < 3:
            return None
        query = f"{name} 3d print"

        with _search_lock:
            with DDGS() as ddgs:
                results = list(ddgs.images(query, max_results=5))

        for r in results:
            try:
                resp = requests.get(
                    r["image"], timeout=6,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                if resp.status_code == 200 and PIL_AVAILABLE:
                    img = Image.open(BytesIO(resp.content)).convert("RGB")
                    img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                    return img
            except Exception:
                continue
    except Exception:
        pass
    return None


def save_thumbnail(img, file_path: str) -> str | None:
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    thumb_path = get_thumb_path(file_path)
    try:
        img.save(str(thumb_path), "PNG")
        return str(thumb_path)
    except Exception:
        return None


def get_or_create_thumbnail(
    file_path: str, fmt: str,
    enable_3d_render: bool = True,
    enable_search: bool = True,
) -> str | None:
    thumb_path = get_thumb_path(file_path)
    if thumb_path.exists():
        return str(thumb_path)

    img = None

    if fmt == "3MF":
        img = extract_3mf_thumbnail(file_path)

    if img is None and enable_search and fmt in ("STL", "OBJ"):
        img = search_image_online(Path(file_path).name)

    if img is None and enable_3d_render and fmt == "STL":
        img = render_stl_thumbnail(file_path)

    if img:
        return save_thumbnail(img, file_path)

    return None


def clear_thumbnail(file_path: str):
    thumb_path = get_thumb_path(file_path)
    if thumb_path.exists():
        thumb_path.unlink()
