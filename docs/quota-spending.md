# How papers on India’s village quotas cite one another

India reserves some village council presidencies for women. Researchers have used that policy to study drinking water, roads, employment, girls’ schooling, and political participation. What happens when a later author brings those studies together in one sentence?

## Three papers on jobs and insurance

Bose and Das studied a rural employment guarantee in Uttar Pradesh. They found greater demand for work under female leaders and no difference in employment generation. Deininger, Nagarajan, and Singh reported more days worked by households holding job cards in their study. On PDF page 4, Deininger and colleagues cite Bose and Das and distinguish the demand result from employment received. [Bose and Das](https://doi.org/10.1111/rode.12336) · [Deininger, Nagarajan, and Singh](https://doi.org/10.1016/j.jce.2019.12.003)

Brown, Mitra, and Singh cite both studies on PDF page 6 in a clause about providing jobs as insurance against shocks. Under a reading about **work received**, one study supplies affirmative evidence. Under a reading about **better insurance**, the comparison would have to show how employment responded to a shock under different leaders. Neither cited result makes that comparison. The distinction matters because the last words of the clause can also describe the program’s purpose. [Brown, Mitra, and Singh, September 2025 version, p. 6](https://www.isid.ac.in/~acegd/acegd2025/papers/AruniMitra.pdf#page=6) · [Same Same’s six reviewed groups](https://github.com/recite/samesame/blob/3cdb8ef7520efa9876bdcd3887be19c1a945c4c4/pilot/README.md)

## How the collection was assembled

The quota-spending project designates a PDF for each of 23 study entries. We took those 23 versions and added Goyal (2024) on participation and Beaman et al. (2012) on aspirations. From those 25 documents we selected six works for citation searches covering public goods, employment, and education. Each search checks the other 24 PDFs, including earlier papers. The 2005 and 2010 Bardhan entries have separate PDF versions. The selection describes this collection of documents. Estimating patterns across political science would require a different sampling design. [Study register at the version used](https://github.com/in-rolls/quota_spending/tree/706f9a67cd1a34016d22b5332d1e4860f62f605c/lit/studies) · {download}`Download the 25-document catalog <../examples/quota-spending/papers.json>`

## What the searches found

Across 144 searches, 28 document–target pairs yielded candidates, 98 returned no match, and 18 failed because three PDFs yielded no readable text. There were 121 candidate mentions across 18 distinct documents. Chattopadhyay and Duflo accounted for 100 mentions in 17 documents, including 24 mentions in Raabe and colleagues alone. The search counts repeated mentions and can pick up bibliography entries. A large count says how often the search matched, without telling us what the paper argued.

Read across a row to see which works a document mentions. Read down a column to see where a work turns up. A blank marks the focal paper’s own PDF, which the search omits. A zero means that the author/year search found nothing. *Failed* means the extractor could not read the PDF.

```{csv-table}
:file: ../examples/quota-spending/counts.csv
:header-rows: 1
```

Eight extracted sentences matched more than one focal work, across three citing documents. These are places to start reading. Brown and colleagues’ page 6 sentence mentions Beaman, Bose, and Deininger, but only the last two references belong to the clause about jobs as insurance. Conversely, a group can include works outside the six focal searches.

## Follow a citation the search missed

In the Beaman et al. (2012) row the Chattopadhyay and Duflo column reads zero. Turn to PDF page 5. The authors credit earlier research on water infrastructure with the marker **(27, 33)**. Reference 27 on PDF page 7 gives the title and publication details for Chattopadhyay and Duflo. Reference 33 on page 8 identifies a second study. Anekanta’s checked record preserves the original group marker and links the passage to reference 27. [Beaman et al.](https://doi.org/10.1126/science.1212382) · {download}`Checked passage and bibliography entry <../schema/examples/beaman-water.json>`

Same Same follows both numbered references. Chattopadhyay and Duflo report more drinking-water investments in reserved councils in the two districts they studied. The second paper adds a multistate survey that finds more taps and hand pumps. The papers share an author and some geography. Counting two references conceals both the additional evidence and the overlap.

The link also changes how one might read Bose and Das. On PDF page 2 they cite Beaman et al. for spending on works benefiting women. On page 11 they cite the same paper for a possible role-model effect. Beaman and colleagues studied girls’ aspirations and schooling directly. When they discuss water investment, they credit prior studies. One pair of papers thus gives us two distinct attributions, and one of those leads back to an earlier source.

## Reproduce the collection

From the Anekanta checkout, use the saved search results to build the database and print the matrix. The SQLite shell command uses SQLite 3.38 or later. The checkout includes everything needed for this step. {download}`Search results, one JSON object per line <../testout/quota-spending.jsonl>` · {download}`Matrix as CSV <../examples/quota-spending/counts.csv>`

```sh
uv run anekanta load testout/quota-spending.jsonl --db citations.sqlite --collection quota-spending
sqlite3 -csv -header citations.sqlite < examples/quota-spending/matrix.sql
```

To inspect each citing passage, this query starts with the exact wording on the source page.

```sql
SELECT source_location, pdf_page, cited_id, passage_id, quote
FROM passages
WHERE collection = 'quota-spending'
ORDER BY source_location, pdf_page, passage_id;
```

To repeat extraction, supply the directory containing the 25 PDF versions in the catalog. The example checks their file hashes, writes one manifest per focal work, reuses extracted page text across searches, and saves a fresh export. The original PDFs are held separately. The manual import reads the checked annotation and verifies its work IDs and PDF hash against the manifest.

```sh
uv run python examples/quota-spending/extract.py /path/to/quota_spending/lit/papers run/quota-collection
cmp testout/quota-spending.jsonl run/quota-collection/quota-spending.jsonl
uv run anekanta import-review run/quota-collection/chattopadhyay_duflo_2004_ecta.json schema/examples/beaman-water.json > run/quota-collection/checked.jsonl
uv run anekanta load run/quota-collection/checked.jsonl --db citations.sqlite --collection quota-water-checked
```
