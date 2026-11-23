"""Tests de la documentation : le site (docs/) et les README.

Lancement :  python -m unittest tools.test_site
"""

import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gen_site  # noqa: E402
import snapshots  # noqa: E402

READMES = ["README.md", "README.fr.md", "README.es.md"]


class SiteTest(unittest.TestCase):
    def test_pages_up_to_date(self):
        """Les six pages sont celles que fabrique tools/gen_site.py (relancer
        le script après avoir changé ses textes ou ceux de lang.py)."""
        for path, text in gen_site.pages().items():
            with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), text, path)

    def test_site_images_exist(self):
        for path in gen_site.pages():
            with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
                text = fh.read()
            base = os.path.dirname(os.path.join(ROOT, path))
            for src in re.findall(r'(?:src|poster)="([^"]+)"', text):
                if src.startswith("http"):
                    continue
                src = src.split("?")[0]            # (?v=1.0 : version, pour le cache)
                self.assertTrue(os.path.isfile(os.path.normpath(os.path.join(base, src))), (path, src))

    def test_every_snapshot_is_on_the_site(self):
        """Chaque capture de tools/snapshots.py est montrée par le site, dans
        les trois langues."""
        for lang in ("en", "fr", "es"):
            home, man, _ = gen_site.PAGES[lang]
            text = ""
            for path in (home, man):
                with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
                    text += fh.read()
            for _, web, _ in snapshots.SCENES:
                self.assertIn("img/%s/%s" % (lang, web), text, (lang, web))


class ReadmeTest(unittest.TestCase):
    def test_readme_images_exist(self):
        for name in READMES:
            with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
                text = fh.read()
            images = re.findall(r'<img src="([^"]+)"', text)
            self.assertGreater(len(images), 8, name)
            for src in images:
                self.assertTrue(os.path.isfile(os.path.join(ROOT, src)), (name, src))

    def test_readmes_describe_the_five_panels(self):
        for name, words in (("README.fr.md", ["f1 — SONG", "f2 — MOTIF", "f3 — INST", "f4 — SAMPLE", "f5 — DISQUE"]),
                            ("README.md", ["f1 — SONG", "f2 — PATTERN", "f3 — INST", "f4 — SAMPLE", "f5 — DISK"]),
                            ("README.es.md", ["f1 — TEMA", "f2 — PATRON", "f3 — INST", "f4 — SAMPLE", "f5 — DISCO"])):
            with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
                text = fh.read()
            for w in words:
                self.assertIn(w, text, (name, w))


if __name__ == "__main__":
    unittest.main()
