"""Render explicitly selected PDF figure regions, including vector plots, to PNG.

Requires the optional PyMuPDF package. Region coordinates are PDF points as
reported by PyMuPDF, with a top-left origin; page numbers are one-based.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def export_figures(pdf_path: Path, output_dir: Path, regions: list[dict], dpi: int = 180) -> dict:
    try:
        import pymupdf
    except ImportError as exc:
        raise RuntimeError("Install the optional PDF dependency: python -m pip install PyMuPDF") from exc
    if not isinstance(dpi, int) or not 72 <= dpi <= 600:
        raise ValueError("dpi must be an integer between 72 and 600")
    if not isinstance(regions, list) or not regions:
        raise ValueError("regions must be a nonempty JSON list")
    pdf_path = Path(pdf_path).resolve()
    output_dir = Path(output_dir).resolve()
    prepared = []
    seen = set()
    with pymupdf.open(pdf_path) as document:
        if document.needs_pass:
            raise ValueError("The source PDF is encrypted")
        for region in regions:
            identifier = region.get("id", "")
            if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", identifier):
                raise ValueError("Each id must be a safe filename containing letters, digits, underscores or hyphens")
            if identifier in seen:
                raise ValueError(f"Duplicate figure id: {identifier}")
            seen.add(identifier)
            number = region.get("page")
            if type(number) is not int or not 1 <= number <= len(document):
                raise ValueError(f"Invalid one-based page for {identifier}")
            page = document[number - 1]
            coords = region.get("clip")
            if not isinstance(coords, list) or len(coords) != 4 or any(type(v) not in (int, float) for v in coords):
                raise ValueError(f"clip must contain four PDF-point coordinates for {identifier}")
            rect = pymupdf.Rect(coords)
            if rect.is_empty or rect.is_infinite or not page.rect.contains(rect):
                raise ValueError(f"clip must be a nonempty rectangle within page {number}: {identifier}")
            pix = page.get_pixmap(dpi=dpi, clip=rect, alpha=False)
            data = pix.tobytes("png")
            path = output_dir / f"{identifier}.png"
            if path.exists() and path.read_bytes() != data:
                raise FileExistsError(f"Existing figure differs; choose a new id or inspect it before replacement: {path}")
            prepared.append((path, data, {
                "id": identifier, "file": path.name, "page": number,
                "clip": list(rect), "dpi": dpi, "width": pix.width, "height": pix.height,
                "sha256": hashlib.sha256(data).hexdigest(),
            }))
    report = {
        "source_pdf": pdf_path.name,
        "source_pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "figures": [entry for _, _, entry in prepared],
    }
    manifest = output_dir / "figures.json"
    manifest_data = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if manifest.exists() and manifest.read_bytes() != manifest_data:
        raise FileExistsError(f"Existing provenance differs; inspect it or choose a separate output directory: {manifest}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, data, _ in prepared:
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(data)
    if not manifest.exists():
        with manifest.open("xb") as stream:
            stream.write(manifest_data)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--regions", required=True, type=Path, help="JSON list: [{id, page, clip:[x0,y0,x1,y1]}]")
    parser.add_argument("--dpi", type=int, default=180)
    args = parser.parse_args(argv)
    try:
        regions = json.loads(args.regions.read_text(encoding="utf-8-sig"))
        report = export_figures(args.pdf, args.output_dir, regions, args.dpi)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Figure extraction failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
