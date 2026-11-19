-- 10_gkg_org_mentions.sql
-- News coverage and average tone per account from GDELT's Global Knowledge Graph in BigQuery.
-- GDELT tags every article with the organizations it mentions (V2Organizations).
--
-- COST: GDELT tables are large. This query reads only 5 columns of the last N days
-- (partitioned by day), but still scans tens of GB. ALWAYS dry-run and cap bytes:
--   bq query --use_legacy_sql=false --dry_run < 10_gkg_org_mentions.sql
--   bq query --use_legacy_sql=false --maximum_bytes_billed=150000000000 < 10_gkg_org_mentions.sql
-- Accounts come from the shared abm.accounts table (domain, company).

DECLARE days INT64 DEFAULT 7;

WITH targets AS (
  SELECT DISTINCT domain, LOWER(TRIM(company)) AS name
  FROM `YOUR_PROJECT.abm.accounts`
  WHERE company IS NOT NULL AND LENGTH(TRIM(company)) >= 4   -- very short names match too much
),
gkg AS (
  SELECT DATE, DocumentIdentifier, SourceCommonName, LOWER(V2Organizations) AS orgs, V2Tone
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONTIME >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL days DAY)
    AND V2Organizations IS NOT NULL
)
SELECT
  t.domain,
  t.name                                                              AS company,
  COUNT(DISTINCT g.DocumentIdentifier)                                AS articles,
  COUNT(DISTINCT g.SourceCommonName)                                  AS outlets,
  ROUND(AVG(SAFE_CAST(SPLIT(g.V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)), 2) AS avg_tone,  -- below 0 = negative coverage
  ARRAY_AGG(g.DocumentIdentifier ORDER BY g.DATE DESC LIMIT 3)        AS latest_urls
FROM gkg AS g
JOIN targets AS t
  ON STRPOS(g.orgs, t.name) > 0
GROUP BY t.domain, t.name
ORDER BY articles DESC;
