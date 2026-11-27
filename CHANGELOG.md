# Changelog

## Unreleased

- Renamed Autosum to Anekanta. The Python package and command are both named `anekanta`.

- Added an installable CLI for OpenAlex discovery, PDF acquisition, passage extraction, and importing existing reviewed annotations.
- Keyed the PDF text cache by document hash and parser version. Reordering input papers now preserves the attribution of each quotation.
- Added the local 16-paper baseline and the Hayes–Lawless endnote example.
- Added two-author searches for narrative and parenthetical citations, including surnames split across lines.
