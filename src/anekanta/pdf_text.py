"""Shared text extraction for the CSV and JSON commands."""

import hashlib
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

import pdfminer
from pdfminer.high_level import extract_text


def cached_text(pdf_bytes, digest, directory=None, *, force=False):
    """Cache the raw, page-delimited text independently of the search query."""
    if directory is None:
        return extract_text(BytesIO(pdf_bytes))
    directory = Path(directory) / f"pdfminer-{pdfminer.__version__}-defaults-v1"
    directory.mkdir(parents=True, exist_ok=True)
    cache_file = directory / f"{digest}.txt"
    if cache_file.exists() and not force:
        return cache_file.read_text(encoding="utf-8")
    text = extract_text(BytesIO(pdf_bytes))
    with NamedTemporaryFile(dir=directory, delete=False) as stream:
        pending = Path(stream.name)
        try:
            stream.write(text.encode("utf-8"))
            stream.close()
            pending.replace(cache_file)
        finally:
            pending.unlink(missing_ok=True)
    return text


def read_pdf(path):
    """Read a PDF and hash the bytes used for extraction."""
    data = Path(path).read_bytes()
    return data, hashlib.sha256(data).hexdigest()
