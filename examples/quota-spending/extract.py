"""Run the six author/year searches against the pinned quota-spending collection."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main():
    """Save one result per focal work and candidate citing document."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    catalog = json.loads(Path(__file__).with_name("papers.json").read_text())
    for paper in catalog:
        path = args.pdf_dir / paper["file"]
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != paper["sha256"]
        ):
            parser.error(f"Expected the cataloged PDF version at {path}")

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output) as staging:
        stage = Path(staging)
        source_root = os.path.relpath(args.pdf_dir.resolve(), output)
        result = stage / "quota-spending.jsonl"
        with result.open("wb") as stream:
            for target in catalog:
                if "search" not in target:
                    continue
                manifest = {
                    "source_root": source_root,
                    "cited_work": target["work"],
                    "papers": [
                        {
                            "citing_work": paper["work"],
                            "path": str(Path(source_root) / paper["file"]),
                            "sha256": paper["sha256"],
                        }
                        for paper in catalog
                        if paper["work"]["id"] != target["work"]["id"]
                    ],
                }
                path = output / Path(target["file"]).with_suffix(".json")
                pending = stage / path.name
                pending.write_text(json.dumps(manifest, indent=2) + "\n")
                pending.replace(path)
                command = [
                    sys.executable,
                    "-m",
                    "anekanta",
                    "extract",
                    str(path),
                    "--cache",
                    str(output / "cache"),
                ]
                for name, value in target["search"].items():
                    command.extend([f"--{name}", value])
                run = subprocess.run(  # noqa: S603 -- fixed interpreter and module
                    command, stdout=subprocess.PIPE, check=False
                )
                # Exit 1 includes a record for every PDF the extractor couldn't read.
                if run.returncode not in (0, 1):
                    run.check_returncode()
                records = [json.loads(line) for line in run.stdout.splitlines()]
                if [r["citing_work"] for r in records] != [
                    p["citing_work"] for p in manifest["papers"]
                ]:
                    raise ValueError(f"Incomplete search for {target['label']}")
                stream.write(run.stdout)
                sys.stderr.write(f"{target['label']}: {len(records)} searched\n")
        result.replace(output / result.name)


if __name__ == "__main__":
    main()
