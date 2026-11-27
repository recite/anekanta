# Anekanta

What do later authors cite a paper for? One author may borrow its research design, another may report a finding, and a third may challenge its conclusion. Anekanta builds a database of citing passages, linking each quotation to the paper, PDF version, and page where it appeared. A reader can then ask what each passage attributes to the source and whether the source supports that attribution.

Consider Chattopadhyay and Duflo’s study of women leading village councils in India. Later authors cite it for the design of the quota system, for changes in political participation, and for what happened to roads and water. Those uses call for different checks. Table V reports more drinking-water facilities built or repaired in villages with reserved leadership in both states. The share of roads in good condition was 18 percentage points higher in West Bengal and 8 points lower in Rajasthan. A summary saying that women leaders invested more in water and roads loses the state distinction and changes what was measured. [Original study, Table V](https://doi.org/10.1111/j.1468-0262.2004.00539.x) · [A worked comparison of citing passages](https://www.gojiberries.io/motivated-citations-2/)

*Anekānta* means many-sidedness. The project began as Autosum in 2015. Its focus is how authors use a source and what a reader would reasonably infer from their words. The software locates candidate passages. Judging accuracy requires reading the passage alongside the relevant evidence in the cited work. [Motivated Citations](https://www.gojiberries.io/motivated-citations/) · [Documentation](https://recite.github.io/anekanta/)

## Start with a collection of papers on village quotas

How do papers about women leading Indian village councils cite one another? The running example searches 25 documents for mentions of six works on public goods, employment, and education. To explore the saved passages from a checkout, run the following commands with uv and the SQLite shell installed.

```sh
uv run anekanta load testout/quota-spending.jsonl --db citations.sqlite --collection quota-spending
sqlite3 -csv -header citations.sqlite < examples/quota-spending/matrix.sql
```

The matrix shows 121 candidate mentions across 18 PDFs. Read across Brown, Mitra, and Singh’s row and five of the six focal works appear. On page 6 two citations share a clause about an employment guarantee. One source reports greater demand for work, another reports more days worked. Whether either supports a claim about insurance depends on what happened when a shock hit. [Explore the collection, source passages, and paper-by-paper matrix](docs/quota-spending.md) · [Read Brown, Mitra, and Singh, p. 6](https://www.isid.ac.in/~acegd/acegd2025/papers/AruniMitra.pdf#page=6)

## Try the extractor on 16 bundled PDFs

With [uv](https://docs.astral.sh/uv/) installed, run the following commands. The repository includes the PDFs for this example.

```sh
git clone https://github.com/recite/anekanta.git
cd anekanta
uv run anekanta extract testdata/iyengar-2012.json --author Iyengar --year 2012 > passages.jsonl
```

The extractor finds eight candidate mentions across five of the 16 PDFs. Each line of output describes one PDF, including its identifier, file hash, search method, and outcome. Each match has a quotation, a PDF page, and a review status. A paper with zero matches gets its own record, as does a paper that could not be read. Compare your output with the [saved results](https://raw.githubusercontent.com/recite/anekanta/master/testout/iyengar-2012.jsonl).

For a two-author work, supply the surnames in publication order, for example `--author Chattopadhyay --coauthor Duflo --year 2004`. This matches both “Chattopadhyay and Duflo (2004)” and “(Chattopadhyay & Duflo, 2004).” Check the bibliography when a year has a suffix such as 2004b. The authors may have published more than one paper that year.

## Follow a citation from discovery to review

Hayes and Lawless cite *Affect, Not Ideology* through an endnote. To follow that citation, run these commands from the repository root.

```sh
uv run anekanta discover 10.1093/poq/nfs038 --citing-doi 10.1017/s1537592714003156 --output run/discovery.json
uv run anekanta acquire run/discovery.json --local-manifest testdata/iyengar-2012.json --offline --output run/manifest.json
uv run anekanta extract run/manifest.json --author Iyengar --year 2012 > run/candidates.jsonl
uv run anekanta import-review run/manifest.json schema/examples/hayes-lawless.json > run/reviewed.jsonl
```

1. **Discover citing works.** OpenAlex supplies the works and their identifiers. Omit `--citing-doi` to request all citing works. Each page saves the works found so far and the cursor for the next request. Set `OPENALEX_API_KEY` to page beyond the first response. Use `--max-pages N` to limit a run and `--resume` to continue it. [OpenAlex authentication](https://help.openalex.org/api/authentication/)
2. **Acquire the PDFs.** The example uses a local catalog and verifies each file’s hash. Online acquisition also tries open-access PDF links from OpenAlex. The resulting manifest records unavailable sources. To process an unfinished discovery run, pass `--allow-partial`.
3. **Extract candidate passages.** The author-and-year search returns `no_match` for Hayes and Lawless. It can miss endnotes, numbered references, and citations split over pages. Use `--cache DIRECTORY` to reuse parsed text when comparing searches. The command writes one result per input and returns exit status 1 if any paper failed.
4. **Import a checked passage.** A reader traced note 40 on printed page 98 (PDF page 4) to the reference on printed page 110 (PDF page 16). The import verifies that the existing annotation identifies the same citing work, cited work, and PDF. Here `source_checked` records that the reader located the passage and its citation. Its accuracy as a description of the cited study is a separate judgment. [Checked annotation](https://raw.githubusercontent.com/recite/anekanta/master/schema/examples/hayes-lawless.json)

## Build a citation database

Use `anekanta load` to keep a collection of search results in SQLite. The database retains the citing and cited work IDs, the PDF version, the method, the page and quotation for each candidate, and every search that failed or returned no matches. New OpenAlex discovery runs also retain available author names and identifiers, publication year, and venue. Older and local records can omit these fields.

From the checkout, load the bundled results and count passages by work. Python supplies SQLite. The query below uses the SQLite command-line client.

```sh
uv run anekanta load testout/iyengar-2012.jsonl --db citations.sqlite --collection iyengar-2012 --source-root .
sqlite3 citations.sqlite "SELECT citing_id, COUNT(*) FROM passages WHERE collection = 'iyengar-2012' GROUP BY citing_id;"
```

Each collection preserves a particular export. Loading the same bytes under the same name and source root a second time leaves it unchanged. Give a revised export its own collection name. Use the `results` table to count searched PDFs, the `passages` view to inspect occurrences, and the `work_metadata` view to recover the available attributes on either side of a citation. Counts across exports can include the same paper or passage more than once.

A study of miscitation can sample these records and attach judgments about what each source supports. A study of selective citation also needs to identify relevant works the author could have cited, including those omitted. Those decisions belong to the study design.

## When several papers are cited together

A sentence can cite three papers for one claim. Check what each contributes. One may supply the estimate, another the method, and a third a result from a different population. The [Same Same project](https://github.com/recite/samesame) describes recording each claim once per cited work. The [miscitation study design](https://github.com/recite/miscitations) asks whether a careful reader would likely be misled by the attribution.

## Development and earlier work

The package supports Python 3.10 and later. Run `make ci` for tests, lint, and type checks, or `make ci-docker` on a standard Python image. On Python 3.13 or later, `make docs` builds the Sphinx documentation with the Furo theme. The documentation includes this README directly.

The wheel includes the discovery, acquisition, and result schemas. Build it with `uv build` and install it with `uv tool install path/to/the-built-wheel.whl`. The sample PDFs and reviewed annotation live in the repository.

The original [Google Scholar and CSV scripts](https://github.com/recite/anekanta/tree/master/scripts) and [arXiv workflow](https://github.com/recite/anekanta/tree/master/arxiv) are available alongside the package. The [original instructions](https://raw.githubusercontent.com/recite/anekanta/a1dde5b1117fde9cc548b36e04521c4c89100b9f/Readme.md) document their formats.
