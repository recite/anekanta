-- From the repository root, run against the database holding the quota-spending collection.
WITH papers AS (
    SELECT value ->> '$.work.id' AS id, value ->> '$.label' AS label
    FROM json_each(CAST(readfile('examples/quota-spending/papers.json') AS TEXT))
), searches AS (
    SELECT citing_id, cited_id,
           CASE outcome
               WHEN 'passages_found' THEN json_array_length(record, '$.passages')
               WHEN 'no_match' THEN 0
               ELSE 'failed'
           END AS mentions
    FROM results WHERE collection = 'quota-spending'
)
SELECT p.label AS "PDF searched",
       MAX(mentions) FILTER (WHERE cited_id = 'doi:10.1111/j.1468-0262.2004.00539.x') AS "Chattopadhyay & Duflo",
       MAX(mentions) FILTER (WHERE cited_id = 'doi:10.1126/science.1212382') AS "Beaman et al.",
       MAX(mentions) FILTER (WHERE cited_id = 'doi:10.1093/wber/lhu001') AS "Gajwani & Zhang",
       MAX(mentions) FILTER (WHERE cited_id = 'doi:10.1086/692114') AS "Pathak & Macours",
       MAX(mentions) FILTER (WHERE cited_id = 'doi:10.1111/rode.12336') AS "Bose & Das",
       MAX(mentions) FILTER (WHERE cited_id = 'doi:10.1016/j.jce.2019.12.003') AS "Deininger et al."
FROM papers AS p LEFT JOIN searches ON p.id = searches.citing_id
GROUP BY p.id, p.label
ORDER BY p.label;
