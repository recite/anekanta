import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "testdata/iyengar-2012.json"
SCHEMA = ROOT / "src/anekanta/schemas/paper-result.schema.json"


class LocalExtractionTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.manifest = json.loads(PILOT.read_text())
        self.papers = self.manifest["papers"]
        for paper in self.papers:
            paper["path"] = str(PILOT.parent / paper["path"])

    def invoke(self, name, *args):
        return subprocess.run(
            [sys.executable, ROOT / "scripts" / name, *args],
            cwd=self.work,
            capture_output=True,
            text=True,
        )

    def extract(self, papers, expected_exit=0):
        self.manifest["papers"] = papers
        path = self.work / "manifest.json"
        path.write_text(json.dumps(self.manifest))
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "anekanta",
                "extract",
                path,
                "--author",
                "Iyengar",
                "--year",
                "2012",
                "--cache",
                "cache",
            ],
            cwd=self.work,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == expected_exit, proc.stderr
        validator = Draft202012Validator(json.loads(SCHEMA.read_text()))
        rows = [json.loads(line) for line in proc.stdout.splitlines()]
        for row in rows:
            validator.validate(row)
        assert len(rows) == len(papers)
        return rows

    def test_reordering_and_inserting_before_cached_papers(self):
        first, second = self.papers[3], self.papers[12]
        a, b = self.extract([first, second])
        assert any(
            p["location"]["pdf_page"] == 25
            and "affective conflict between the parties" in p["quote"]
            for p in a["passages"]
        )
        assert a["source"]["sha256"] == first["sha256"]
        _, again_b, again_a = self.extract([self.papers[0], second, first])
        assert (again_a, again_b) == (a, b)

    def test_missing_and_swapped_files_with_a_warm_cache(self):
        good, wrong, missing = self.papers[:3]
        self.extract([good])
        wrong["path"] = good["path"]
        missing["path"] = str(self.work / "absent.pdf")
        a, b, c = self.extract([wrong, missing, good], expected_exit=1)
        assert a["outcome"] == "extraction_failed"
        assert wrong["sha256"] in a["detail"]
        assert b["outcome"] == "source_unavailable"
        assert (a["passages"], b["passages"]) == ([], [])
        assert c["source"]["sha256"] == good["sha256"]

    def test_legacy_csv_cache_follows_document(self):
        def extract_csv(papers):
            with (self.work / "input.csv").open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["pdf_path"])
                writer.writerows([p["path"]] for p in papers)
            proc = self.invoke(
                "autosumpdf.py",
                "-i",
                "input.csv",
                "-o",
                "output.csv",
                "-a1",
                "Iyengar",
                "-y",
                "2012",
            )
            assert proc.returncode == 0, proc.stderr
            with (self.work / "output.csv").open() as stream:
                return list(csv.DictReader(stream))

        first, second = self.papers[3], self.papers[12]
        a, b = extract_csv([first, second])
        assert (a["status"], b["status"]) == ("OK", "OK")
        assert a["founds"] != b["founds"]
        assert extract_csv([second, first]) == [b, a]
