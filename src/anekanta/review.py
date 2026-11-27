"""Import an existing source-checked annotation against an acquired document."""

import json
import sys

from anekanta.contracts import VALIDATOR, load_manifest
from anekanta.pdf_text import read_pdf


def run(args):
    """Emit the reviewed record when the target, citing work, and PDF hash agree."""
    manifest = load_manifest(args.manifest)
    record = json.loads(args.record.read_text(encoding="utf-8"))
    VALIDATOR.validate(record)
    if not record["passages"] or any(
        p["review"] != "source_checked" for p in record["passages"]
    ):
        raise ValueError("A review record must contain source-checked passages")
    if record["cited_work"]["id"] != manifest["cited_work"]["id"]:
        raise ValueError("Review is for a different cited work")
    for paper in manifest["papers"]:
        if (
            paper["citing_work"]["id"] == record["citing_work"]["id"]
            and "path" in paper
        ):
            folder = args.manifest.parent.resolve()
            path = (folder / paper["path"]).resolve()
            root = (folder / manifest.get("source_root", ".")).resolve()
            _, digest = read_pdf(path)
            if digest != paper["sha256"] or digest != record["source"]["sha256"]:
                raise ValueError("Review is for a different PDF")
            location = path.relative_to(root) if path.is_relative_to(root) else path
            record["source"]["location"] = str(location)
            sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")
            return 0
    raise ValueError("Manifest has no acquired PDF for this reviewed citing work")
