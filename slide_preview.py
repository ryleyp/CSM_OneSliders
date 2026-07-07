"""Local, best-effort preview rendering for generated PowerPoint files.

The app stays offline. Rendering uses local system tools when they exist:
macOS Quick Look today, and a clear "not available" result otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path


@dataclass
class PreviewResult:
    image_bytes: bytes | None
    method: str
    message: str


def preview_renderer_status() -> dict:
    """Return local preview-renderer availability for diagnostics."""
    qlmanage = shutil.which("qlmanage")
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    pdftoppm = shutil.which("pdftoppm")
    return {
        "platform": platform.system(),
        "quicklook": qlmanage or "",
        "libreoffice": soffice or "",
        "pdftoppm": pdftoppm or "",
        "available": bool(qlmanage and platform.system() == "Darwin"),
    }


def render_pptx_preview(pptx_bytes: bytes, *, size: int = 1400) -> PreviewResult:
    """Render the first slide of a PPTX to PNG bytes when a local renderer exists."""
    status = preview_renderer_status()
    if status["quicklook"] and status["platform"] == "Darwin":
        return _render_with_quicklook(pptx_bytes, status["quicklook"], size=size)

    return PreviewResult(
        image_bytes=None,
        method="",
        message=(
            "PPTX image preview is not available on this machine, so the app is "
            "showing the built-in HTML preview instead."
        ),
    )


def _render_with_quicklook(pptx_bytes: bytes, qlmanage: str, *, size: int) -> PreviewResult:
    with tempfile.TemporaryDirectory(prefix="ea_slide_preview_") as tmp:
        tmp_dir = Path(tmp)
        pptx_path = tmp_dir / "preview.pptx"
        pptx_path.write_bytes(pptx_bytes)

        proc = subprocess.run(
            [qlmanage, "-t", "-s", str(size), "-o", str(tmp_dir), str(pptx_path)],
            capture_output=True,
            text=True,
            timeout=45,
        )
        png_path = tmp_dir / "preview.pptx.png"
        if proc.returncode != 0 or not png_path.exists():
            details = (proc.stderr or proc.stdout or "").strip()
            return PreviewResult(
                image_bytes=None,
                method="macOS Quick Look",
                message=f"PPTX image preview could not be rendered. {details}".strip(),
            )

        return PreviewResult(
            image_bytes=png_path.read_bytes(),
            method="macOS Quick Look",
            message="Rendered locally from the generated PPTX with macOS Quick Look.",
        )
