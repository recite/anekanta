"""Validate pipeline artifacts with the schemas shipped in the wheel."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ASSETS = Path(__file__).parent / "schemas"
SCHEMA = json.loads((ASSETS / "paper-result.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def validate(name, value):
    """Validate an input using bundled schema references."""
    schema_path = ASSETS / name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    registry = Registry().with_resource(
        "paper-result.schema.json", Resource.from_contents(SCHEMA)
    )
    Draft202012Validator(schema, registry=registry).validate(value)


def validate_manifest(manifest):
    """Reject invalid inventories and ambiguous paper or source identities."""
    validate("manifest.schema.json", manifest)
    papers = manifest["papers"]
    if len({p["citing_work"]["id"] for p in papers}) != len(papers):
        raise ValueError("duplicate citing work ID in manifest")
    hashes = [p["sha256"] for p in papers if "sha256" in p]
    if len(set(hashes)) != len(hashes):
        raise ValueError("duplicate PDF hash in manifest")


def load_manifest(path):
    """Read and validate the acquisition inventory."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    return manifest
