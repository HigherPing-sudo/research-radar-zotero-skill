import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from extract_paper_figures import export_figures


@unittest.skipUnless(importlib.util.find_spec("pymupdf"), "optional PyMuPDF dependency unavailable")
class FigureExportTests(unittest.TestCase):
    def setUp(self):
        import pymupdf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = self.root / "source.pdf"
        document = pymupdf.open()
        page = document.new_page(width=200, height=200)
        page.draw_rect(pymupdf.Rect(50, 50, 150, 150), color=(1, 0, 0), fill=(1, 0, 0))
        document.save(self.pdf)
        document.close()
        self.output = self.root / "figures"
        self.regions = [{"id": "Figure1", "page": 1, "clip": [40, 40, 160, 160]}]

    def test_vector_figure_geometry_provenance_and_idempotence(self):
        import pymupdf
        report = export_figures(self.pdf, self.output, self.regions, 144)
        pix = pymupdf.Pixmap(self.output / "Figure1.png")
        self.assertEqual((pix.width, pix.height), (240, 240))
        self.assertEqual(pix.pixel(120, 120), (255, 0, 0))
        self.assertEqual(pix.pixel(1, 1), (255, 255, 255))
        self.assertEqual(report, json.loads((self.output / "figures.json").read_text(encoding="utf-8")))
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        self.assertEqual(export_figures(self.pdf, self.output, self.regions, 144), report)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir()})

    def test_invalid_region_does_not_leave_partial_output(self):
        for change in [{"page": 0}, {"page": 2}, {"clip": [-1, 0, 20, 20]},
                       {"clip": [10, 10, 10, 20]}, {"id": "../escape"}, {"clip": [0, 0, 999, 999]}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                export_figures(self.pdf, self.output, self.regions + [{**self.regions[0], "id": "Other", **change}])
            self.assertFalse(self.output.exists())

    def test_user_modified_figure_is_preserved(self):
        export_figures(self.pdf, self.output, self.regions)
        path = self.output / "Figure1.png"
        path.write_bytes(b"user annotation")
        with self.assertRaises(FileExistsError):
            export_figures(self.pdf, self.output, self.regions)
        self.assertEqual(path.read_bytes(), b"user annotation")

    def test_duplicate_ids_and_changed_provenance_are_rejected(self):
        with self.assertRaises(ValueError):
            export_figures(self.pdf, self.output, self.regions * 2)
        export_figures(self.pdf, self.output, self.regions)
        manifest = self.output / "figures.json"
        manifest.write_text("{}", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            export_figures(self.pdf, self.output, self.regions)
        self.assertEqual(manifest.read_text(encoding="utf-8"), "{}")


if __name__ == "__main__":
    unittest.main()
