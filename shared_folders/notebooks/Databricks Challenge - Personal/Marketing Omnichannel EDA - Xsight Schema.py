# Databricks notebook source
# DBTITLE 1,Overview
# MAGIC %md
# MAGIC # Marketing Omnichannel EDA — Xsight Schema
# MAGIC
# MAGIC Exploratory data analysis of the 9 marketing source tables in `databricks_snowflake_migration_catalog.xsight_rpt_zn`, covering HCP omnichannel activity (rep calls, print-on-demand, drug samples, savings cards, telemarketing, website), 3 dimension tables (customer profile, territory, sales org), and 1 weekly Rx table used for impact analysis.
# MAGIC
# MAGIC **Goals:**
# MAGIC 1. Profile row counts, date ranges, and fill rates (NULL %) for every table/column.
# MAGIC 2. Measure HCP overlap across marketing channels.
# MAGIC 3. Validate whether the activity-table ID system (`"Prf Profile Id"`) can be joined to the dimension/Rx ID system (`CUST_ID`).
# MAGIC 4. Surface data quality issues and document gaps before building gold-layer tables.
# MAGIC
# MAGIC **Note on column names:** these tables were migrated from Snowflake. Columns with spaces have embedded double quotes in their names and must be referenced as `` `"Column Name"` `` (backtick + literal double quotes), e.g. `` `"Prf Profile Id"` ``. Dimension tables (`rpt_*`) use plain column names with no quoting needed.

# COMMAND ----------

# DBTITLE 1,Section 1: Setup & Configuration
# Section 1: Setup & Configuration
catalog = "databricks_snowflake_migration_catalog"
schema = "xsight_rpt_zn"

# Fact (activity) tables: channel name, HCP id column, date column
fact_tables = {
    "dz_isa": {"channel": "Rep Calls (ISA)", "hcp_col": '"Prf Profile Id"', "date_col": '"Actual Date"'},
    "dz_pod": {"channel": "Print-on-Demand", "hcp_col": '"Prf Profile Id"', "date_col": '"Actual Date"'},
    "dz_sample_activity": {"channel": "Drug Samples", "hcp_col": '"Prf Profile Id"', "date_col": '"Sample Date"'},
    "dz_savings_card": {"channel": "Savings Card / Copay", "hcp_col": '"Prf Profile Id"', "date_col": '"Org Submitted Cal Date"'},
    "dz_tele_detail": {"channel": "Telemarketing", "hcp_col": '"Prf Profile Id"', "date_col": '"Activity Cal Date"'},
    "dz_website_page": {"channel": "Website Pageviews", "hcp_col": '"Profile Id"', "date_col": '"Cal Date"'},
}
dim_tables = ["rpt_cust_profile", "rpt_cust_territory", "rpt_sales_org"]
rx_table = "rpt_sha_weekly"
all_tables = list(fact_tables.keys()) + dim_tables + [rx_table]

def qtbl(t):
    return f"`{catalog}`.`{schema}`.`{t}`"

print(f"Total tables to profile: {len(all_tables)}")
for t in all_tables:
    print(" -", t)

# COMMAND ----------

# DBTITLE 1,Section 2: Data Preview
# MAGIC %md
# MAGIC ## Section 2: Data Preview
# MAGIC First 5 rows of every table, with a short description of what each contains.

# COMMAND ----------

# DBTITLE 1,Preview all 10 tables
descriptions = {
    "dz_isa": "Rep in-field call activity (F2F + remote meetings) - one row per call/HCP interaction.",
    "dz_pod": "Print-on-demand marketing material requests sent to HCPs.",
    "dz_sample_activity": "Drug sample distribution/order activity to HCPs.",
    "dz_savings_card": "Patient savings card / copay program claims linked to prescribing HCP.",
    "dz_tele_detail": "Telemarketing call center outreach activity to HCPs.",
    "dz_website_page": "Website pageview/session events - NOTE: HCP linkage column is expected to be entirely NULL.",
    "rpt_cust_profile": "Doctor/HCP master profile - specialty, decile, target flag.",
    "rpt_cust_territory": "Doctor (CUST_ID) to sales TERRITORY mapping.",
    "rpt_sales_org": "Sales org hierarchy: territory -> district -> region.",
    "rpt_sha_weekly": "Weekly prescription (Rx) volumes by HCP x brand, for impact analysis.",
}

for t in all_tables:
    print(f"\n=== {t} ===\n{descriptions.get(t, '')}")
    display(spark.sql(f"SELECT * FROM {qtbl(t)} LIMIT 5"))

# COMMAND ----------

# DBTITLE 1,Section 3: Row Counts & Basic Stats
# MAGIC %md
# MAGIC ## Section 3: Row Counts & Basic Stats
# MAGIC Total rows, distinct HCP counts, and date ranges for fact tables; row/key counts for dimension and Rx tables.

# COMMAND ----------

# DBTITLE 1,Fact table row counts and date ranges
# MAGIC %sql
# MAGIC -- Row counts, distinct HCPs, and date ranges per fact (activity) table
# MAGIC SELECT 'dz_isa' AS table_name, COUNT(*) AS total_rows,
# MAGIC        COUNT(DISTINCT `"Prf Profile Id"`) AS distinct_hcps,
# MAGIC        MIN(`"Actual Date"`) AS min_date, MAX(`"Actual Date"`) AS max_date
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_isa
# MAGIC UNION ALL
# MAGIC SELECT 'dz_pod', COUNT(*), COUNT(DISTINCT `"Prf Profile Id"`), MIN(`"Actual Date"`), MAX(`"Actual Date"`)
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_pod
# MAGIC UNION ALL
# MAGIC SELECT 'dz_sample_activity', COUNT(*), COUNT(DISTINCT `"Prf Profile Id"`), MIN(`"Sample Date"`), MAX(`"Sample Date"`)
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_sample_activity
# MAGIC UNION ALL
# MAGIC SELECT 'dz_savings_card', COUNT(*), COUNT(DISTINCT `"Prf Profile Id"`), MIN(`"Org Submitted Cal Date"`), MAX(`"Org Submitted Cal Date"`)
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_savings_card
# MAGIC UNION ALL
# MAGIC SELECT 'dz_tele_detail', COUNT(*), COUNT(DISTINCT `"Prf Profile Id"`), MIN(`"Activity Cal Date"`), MAX(`"Activity Cal Date"`)
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_tele_detail
# MAGIC UNION ALL
# MAGIC SELECT 'dz_website_page', COUNT(*), COUNT(DISTINCT `"Profile Id"`), MIN(CAST(`"Cal Date"` AS DATE)), MAX(CAST(`"Cal Date"` AS DATE))
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_website_page
# MAGIC ORDER BY table_name;

# COMMAND ----------

# DBTITLE 1,Dimension and Rx table row counts
# MAGIC %sql
# MAGIC -- Row/key counts for dimension and Rx tables
# MAGIC SELECT 'rpt_cust_profile' AS table_name, COUNT(*) AS total_rows, COUNT(DISTINCT CUST_ID) AS distinct_ids, CAST(NULL AS TIMESTAMP) AS min_date, CAST(NULL AS TIMESTAMP) AS max_date
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.rpt_cust_profile
# MAGIC UNION ALL
# MAGIC SELECT 'rpt_cust_territory', COUNT(*), COUNT(DISTINCT CUST_ID), CAST(NULL AS TIMESTAMP), CAST(NULL AS TIMESTAMP)
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.rpt_cust_territory
# MAGIC UNION ALL
# MAGIC SELECT 'rpt_sales_org', COUNT(*), COUNT(DISTINCT TERRITORY_CD), CAST(NULL AS TIMESTAMP), CAST(NULL AS TIMESTAMP)
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.rpt_sales_org
# MAGIC UNION ALL
# MAGIC SELECT 'rpt_sha_weekly', COUNT(*), COUNT(DISTINCT CUST_ID), MIN(WEEKEND_DATE), MAX(WEEKEND_DATE)
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.rpt_sha_weekly;

# COMMAND ----------

# DBTITLE 1,Section 4: Fill Rate Analysis
# MAGIC %md
# MAGIC ## Section 4: Fill Rate Analysis (NULL Check)
# MAGIC NULL percentage for every column of every table, computed dynamically from each table's actual schema. Key columns to watch: `dz_website_page."Profile Id"` (expected ~100% NULL), all `"Prf Profile Id"` columns (should be ~0% NULL), and `dz_isa."Rm Duration"` / `"Rm End Time"` / `"Rm Start Time"` (likely high NULL rate for face-to-face calls).

# COMMAND ----------

# DBTITLE 1,Dynamic NULL fill-rate per table
from pyspark.sql import functions as F

fill_rate_results = {}
for t in all_tables:
    cols = spark.table(f"{catalog}.{schema}.{t}").columns
    null_exprs = ", ".join([f"SUM(CASE WHEN `{c}` IS NULL THEN 1 ELSE 0 END) AS `{c}`" for c in cols])
    q = f"SELECT COUNT(*) AS total_rows, {null_exprs} FROM {qtbl(t)}"
    row = spark.sql(q).collect()[0]
    total = row["total_rows"]
    recs = []
    for c in cols:
        null_count = row[c]
        pct = round(null_count * 100.0 / total, 2) if total else None
        recs.append((c, total, null_count, pct))
    df = spark.createDataFrame(recs, ["column_name", "total_rows", "null_count", "null_pct"]).orderBy(F.desc("null_pct"))
    fill_rate_results[t] = df
    print(f"\n=== Fill rate: {t} ===")
    display(df)

# COMMAND ----------

# DBTITLE 1,Section 5: Cardinality Analysis
# MAGIC %md
# MAGIC ## Section 5: Distinct Value Counts (Cardinality)
# MAGIC Distinct values and frequencies for key categorical columns across fact tables.

# COMMAND ----------

# DBTITLE 1,Cardinality of key categorical columns
categorical_checks = [
    ("dz_isa", '"Sp Group"'), ("dz_isa", '"Decile Grp"'), ("dz_isa", '"Call Type"'), ("dz_isa", '"Call Category"'),
    ("dz_pod", '"Sp Group"'), ("dz_pod", '"Message Type"'),
    ("dz_tele_detail", '"Sp Group"'), ("dz_tele_detail", '"Disposition Desc"'), ("dz_tele_detail", '"Activity Type"'),
    ("dz_savings_card", '"Sp Group"'), ("dz_savings_card", '"Sc Type"'),
    ("dz_sample_activity", '"Sp Group"'), ("dz_sample_activity", '"Order Status"'),
    ("dz_website_page", '"Audience Type"'), ("dz_website_page", '"Page Audience Type"'),
]

for t, c in categorical_checks:
    print(f"\n--- DISTINCT {c} in {t} ---")
    display(spark.sql(f"SELECT `{c}` AS value, COUNT(*) AS cnt FROM {qtbl(t)} GROUP BY `{c}` ORDER BY cnt DESC LIMIT 20"))

# COMMAND ----------

# DBTITLE 1,Section 6: HCP Overlap Analysis
# MAGIC %md
# MAGIC ## Section 6: HCP Overlap Analysis
# MAGIC How many doctors are touched by more than one marketing channel? (Website excluded here since its HCP-linkage column is expected to be NULL - see Section 4/11.)

# COMMAND ----------

# DBTITLE 1,Top HCPs by channels touched
# MAGIC %sql
# MAGIC WITH hcps_per_channel AS (
# MAGIC   SELECT DISTINCT CAST(`"Prf Profile Id"` AS STRING) AS hcp_id, 'ISA_Call' AS channel FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_isa WHERE `"Prf Profile Id"` IS NOT NULL
# MAGIC   UNION ALL
# MAGIC   SELECT DISTINCT CAST(`"Prf Profile Id"` AS STRING), 'POD' FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_pod WHERE `"Prf Profile Id"` IS NOT NULL
# MAGIC   UNION ALL
# MAGIC   SELECT DISTINCT CAST(`"Prf Profile Id"` AS STRING), 'Sample' FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_sample_activity WHERE `"Prf Profile Id"` IS NOT NULL
# MAGIC   UNION ALL
# MAGIC   SELECT DISTINCT CAST(`"Prf Profile Id"` AS STRING), 'Savings_Card' FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_savings_card WHERE `"Prf Profile Id"` IS NOT NULL
# MAGIC   UNION ALL
# MAGIC   SELECT DISTINCT CAST(`"Prf Profile Id"` AS STRING), 'Tele' FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_tele_detail WHERE `"Prf Profile Id"` IS NOT NULL
# MAGIC )
# MAGIC SELECT hcp_id, COUNT(DISTINCT channel) AS channels_touched, COLLECT_SET(channel) AS channel_list
# MAGIC FROM hcps_per_channel
# MAGIC GROUP BY hcp_id
# MAGIC ORDER BY channels_touched DESC, hcp_id
# MAGIC LIMIT 20;

# COMMAND ----------

# DBTITLE 1,HCP count by number of channels touched
# MAGIC %sql
# MAGIC WITH hcps_per_channel AS (
# MAGIC   SELECT DISTINCT CAST(`"Prf Profile Id"` AS STRING) AS hcp_id, 'ISA_Call' AS channel FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_isa WHERE `"Prf Profile Id"` IS NOT NULL
# MAGIC   UNION ALL
# MAGIC   SELECT DISTINCT CAST(`"Prf Profile Id"` AS STRING), 'POD' FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_pod WHERE `"Prf Profile Id"` IS NOT NULL
# MAGIC   UNION ALL
# MAGIC   SELECT DISTINCT CAST(`"Prf Profile Id"` AS STRING), 'Sample' FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_sample_activity WHERE `"Prf Profile Id"` IS NOT NULL
# MAGIC   UNION ALL
# MAGIC   SELECT DISTINCT CAST(`"Prf Profile Id"` AS STRING), 'Savings_Card' FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_savings_card WHERE `"Prf Profile Id"` IS NOT NULL
# MAGIC   UNION ALL
# MAGIC   SELECT DISTINCT CAST(`"Prf Profile Id"` AS STRING), 'Tele' FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_tele_detail WHERE `"Prf Profile Id"` IS NOT NULL
# MAGIC ),
# MAGIC hcp_channel_counts AS (
# MAGIC   SELECT hcp_id, COUNT(DISTINCT channel) AS channels_touched
# MAGIC   FROM hcps_per_channel
# MAGIC   GROUP BY hcp_id
# MAGIC )
# MAGIC SELECT channels_touched, COUNT(*) AS hcp_count
# MAGIC FROM hcp_channel_counts
# MAGIC GROUP BY channels_touched
# MAGIC ORDER BY channels_touched;

# COMMAND ----------

# DBTITLE 1,Section 7: Join Validation
# MAGIC %md
# MAGIC ## Section 7: Join Validation — ID Systems
# MAGIC Test whether activity-table IDs (`"Prf Profile Id"`) can be linked to the dimension/Rx ID system (`CUST_ID` / `HCP_ID`).

# COMMAND ----------

# DBTITLE 1,Sample ID formats across systems
print("--- Sample IDs from activity tables (Prf Profile Id) ---")
display(spark.sql(f'SELECT CAST(`"Prf Profile Id"` AS STRING) AS id_sample FROM {qtbl("dz_isa")} WHERE `"Prf Profile Id"` IS NOT NULL LIMIT 5'))

print("--- Sample IDs from rpt_cust_profile (CUST_ID) ---")
display(spark.sql(f'SELECT CUST_ID AS id_sample FROM {qtbl("rpt_cust_profile")} LIMIT 5'))

print("--- Sample IDs from rpt_sha_weekly (CUST_ID, HCP_ID) ---")
display(spark.sql(f'SELECT CUST_ID, HCP_ID FROM {qtbl("rpt_sha_weekly")} LIMIT 5'))

# COMMAND ----------

# DBTITLE 1,Direct and transformed join attempts
# Step 1: direct join attempt (expect 0 matches - different ID systems)
print("Direct join (Prf Profile Id = rpt_cust_profile.CUST_ID):")
display(spark.sql(f'''
    SELECT COUNT(*) AS direct_match_count
    FROM {qtbl("dz_isa")} a
    JOIN {qtbl("rpt_cust_profile")} p
      ON CAST(a.`"Prf Profile Id"` AS STRING) = p.CUST_ID
'''))

print("Direct join (Prf Profile Id = rpt_sha_weekly.HCP_ID):")
display(spark.sql(f'''
    SELECT COUNT(*) AS direct_match_count
    FROM {qtbl("dz_isa")} a
    JOIN {qtbl("rpt_sha_weekly")} w
      ON CAST(a.`"Prf Profile Id"` AS STRING) = w.HCP_ID
'''))

# Step 2: inspect raw ID patterns to look for a transformation rule
print("CUST_ID length/prefix patterns:")
display(spark.sql(f'SELECT DISTINCT LENGTH(CUST_ID) AS cust_id_len, SUBSTRING(CUST_ID,1,5) AS cust_id_prefix FROM {qtbl("rpt_cust_profile")} LIMIT 20'))

print("Prf Profile Id numeric range:")
display(spark.sql(f'SELECT MIN(`"Prf Profile Id"`) AS min_id, MAX(`"Prf Profile Id"`) AS max_id FROM {qtbl("dz_isa")}'))

# Step 3: try a candidate transformation (strip non-numeric characters from CUST_ID, cast to number)
print("Transformed join attempt (strip non-numeric chars from CUST_ID):")
display(spark.sql(f'''
    SELECT COUNT(*) AS transformed_match_count
    FROM {qtbl("dz_isa")} a
    JOIN {qtbl("rpt_cust_profile")} p
      ON TRY_CAST(REGEXP_REPLACE(p.CUST_ID, '[^0-9]', '') AS DECIMAL(38,0)) = a.`"Prf Profile Id"`
'''))

# COMMAND ----------

# DBTITLE 1,Dimension-to-dimension join validation
# Step 4: confirm dimension/Rx tables join to each other correctly
print("profile_to_territory_match:")
display(spark.sql(f'''
  SELECT COUNT(*) AS profile_to_territory_match
  FROM {qtbl("rpt_cust_profile")} p JOIN {qtbl("rpt_cust_territory")} t ON p.CUST_ID = t.CUST_ID
'''))

print("territory_to_sales_org_match:")
display(spark.sql(f'''
  SELECT COUNT(*) AS territory_to_sales_org_match
  FROM {qtbl("rpt_cust_territory")} t JOIN {qtbl("rpt_sales_org")} s ON t.TERRITORY = s.TERRITORY_CD
'''))

print("sha_to_profile_match:")
display(spark.sql(f'''
  SELECT COUNT(*) AS sha_to_profile_match
  FROM {qtbl("rpt_sha_weekly")} w JOIN {qtbl("rpt_cust_profile")} p ON w.CUST_ID = p.CUST_ID
'''))

# COMMAND ----------

# DBTITLE 1,Section 8: Date Range & Overlap Analysis
# MAGIC %md
# MAGIC ## Section 8: Date Range & Overlap Analysis
# MAGIC Monthly activity trend per fact table — identify which channels start/stop early relative to others.

# COMMAND ----------

# DBTITLE 1,Monthly activity trend per fact table
for t, meta in fact_tables.items():
    date_col = meta["date_col"]  # already includes embedded double quotes, e.g. '"Actual Date"'
    print(f"\n--- Monthly activity: {t} ({meta['channel']}) ---")
    display(spark.sql(f'''
        SELECT DATE_TRUNC('month', CAST(`{date_col}` AS DATE)) AS month, COUNT(*) AS activity_count
        FROM {qtbl(t)}
        WHERE `{date_col}` IS NOT NULL
        GROUP BY 1 ORDER BY 1
    '''))

# COMMAND ----------

# DBTITLE 1,Section 9: Data Quality Checks
# MAGIC %md
# MAGIC ## Section 9: Data Quality Checks
# MAGIC Duplicate rows, cross-table consistency of specialty/decile, and impossible values (future dates, out-of-range deciles).

# COMMAND ----------

# DBTITLE 1,Duplicate row check on dz_isa
# MAGIC %sql
# MAGIC -- Duplicate row check: are there duplicate (Activity Key, Seq Number) combinations?
# MAGIC SELECT COUNT(*) AS total_rows,
# MAGIC        COUNT(DISTINCT `"Activity Key"`, `"Seq Number"`) AS distinct_keys
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_isa;

# COMMAND ----------

# DBTITLE 1,Sp Group consistency across fact tables
# MAGIC %sql
# MAGIC -- Do Sp Group (specialty) values match across the different activity tables?
# MAGIC SELECT 'dz_isa' AS tbl, `"Sp Group"` AS sp_group, COUNT(*) AS cnt FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_isa GROUP BY 2
# MAGIC UNION ALL
# MAGIC SELECT 'dz_pod', `"Sp Group"`, COUNT(*) FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_pod GROUP BY 2
# MAGIC UNION ALL
# MAGIC SELECT 'dz_tele_detail', `"Sp Group"`, COUNT(*) FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_tele_detail GROUP BY 2
# MAGIC UNION ALL
# MAGIC SELECT 'dz_sample_activity', `"Sp Group"`, COUNT(*) FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_sample_activity GROUP BY 2
# MAGIC UNION ALL
# MAGIC SELECT 'dz_savings_card', `"Sp Group"`, COUNT(*) FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_savings_card GROUP BY 2
# MAGIC ORDER BY sp_group, tbl;

# COMMAND ----------

# DBTITLE 1,Decile consistency check between dz_isa and dz_tele_detail
decile_check = spark.sql(f'''
    SELECT a.hcp_id, a.decile_isa, b.decile_tele
    FROM (SELECT CAST(`"Prf Profile Id"` AS STRING) AS hcp_id, MAX(`"Decile Value"`) AS decile_isa FROM {qtbl("dz_isa")} GROUP BY 1) a
    JOIN (SELECT CAST(`"Prf Profile Id"` AS STRING) AS hcp_id, MAX(`"Decile Value"`) AS decile_tele FROM {qtbl("dz_tele_detail")} GROUP BY 1) b
      ON a.hcp_id = b.hcp_id
    WHERE a.decile_isa != b.decile_tele
''')
print(f"HCPs with mismatched decile between dz_isa and dz_tele_detail: {decile_check.count()}")
display(decile_check.limit(10))

# COMMAND ----------

# DBTITLE 1,Future dates and impossible decile values
# MAGIC %sql
# MAGIC SELECT
# MAGIC   (SELECT COUNT(*) FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_isa WHERE `"Actual Date"` > CURRENT_DATE()) AS future_dates_isa,
# MAGIC   (SELECT MIN(`"Decile Value"`) FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_isa) AS min_decile_isa,
# MAGIC   (SELECT MAX(`"Decile Value"`) FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.dz_isa) AS max_decile_isa;

# COMMAND ----------

# DBTITLE 1,Section 10: Embedded Dimensions Profiling
# MAGIC %md
# MAGIC ## Section 10: Embedded Dimensions Profiling
# MAGIC Fact tables carry embedded specialty/decile/geography dimensions. Profile them and compare against `rpt_cust_profile`.

# COMMAND ----------

# DBTITLE 1,Specialty, decile, and state distribution in dz_isa
print("Specialty (Sp Group) distribution in dz_isa:")
display(spark.sql(f'SELECT `"Sp Group"` AS sp_group, COUNT(*) AS rows, COUNT(DISTINCT `"Prf Profile Id"`) AS hcps FROM {qtbl("dz_isa")} GROUP BY 1 ORDER BY hcps DESC'))

print("Decile distribution in dz_isa:")
display(spark.sql(f'SELECT CAST(`"Decile Value"` AS INT) AS decile, COUNT(DISTINCT `"Prf Profile Id"`) AS hcps FROM {qtbl("dz_isa")} GROUP BY 1 ORDER BY 1'))

print("Top 10 states by HCP count in dz_isa:")
display(spark.sql(f'SELECT `"State Code"` AS state_code, COUNT(DISTINCT `"Prf Profile Id"`) AS hcps FROM {qtbl("dz_isa")} GROUP BY 1 ORDER BY hcps DESC LIMIT 10'))

# COMMAND ----------

# DBTITLE 1,Compare specialty values: rpt_cust_profile vs dz_isa
print("Distinct specialties in rpt_cust_profile:")
display(spark.sql(f'SELECT DISTINCT SPECIALTY FROM {qtbl("rpt_cust_profile")} ORDER BY 1'))

print("Distinct Sp Group values in dz_isa:")
display(spark.sql(f'SELECT DISTINCT `"Sp Group"` FROM {qtbl("dz_isa")} ORDER BY 1'))

# COMMAND ----------

# DBTITLE 1,Section 11: Website Table Deep Dive
# MAGIC %md
# MAGIC ## Section 11: Website Table Deep Dive
# MAGIC `dz_website_page` is typically the largest table but has no reliable HCP linkage. Profile what CAN be used at an aggregate (non-HCP) level.

# COMMAND ----------

# DBTITLE 1,Website audience, top pages, traffic, device, trend
print("Audience Type breakdown:")
display(spark.sql(f'SELECT `"Audience Type"` AS audience_type, COUNT(*) AS cnt FROM {qtbl("dz_website_page")} GROUP BY 1 ORDER BY cnt DESC'))

print("Top 10 pages by pageviews:")
display(spark.sql(f'SELECT `"Page Name"` AS page_name, COUNT(*) AS views FROM {qtbl("dz_website_page")} GROUP BY 1 ORDER BY views DESC LIMIT 10'))

print("Traffic sources (Medium):")
display(spark.sql(f'SELECT `"Medium"` AS medium, COUNT(*) AS visits FROM {qtbl("dz_website_page")} GROUP BY 1 ORDER BY visits DESC'))

print("Device breakdown:")
display(spark.sql(f'SELECT `"Device Info"` AS device_info, COUNT(*) AS cnt FROM {qtbl("dz_website_page")} GROUP BY 1 ORDER BY cnt DESC LIMIT 15'))

print("Monthly web traffic trend:")
display(spark.sql(f'''SELECT DATE_TRUNC('month', CAST(`"Cal Date"` AS DATE)) AS month, COUNT(*) AS pageviews
                       FROM {qtbl("dz_website_page")} GROUP BY 1 ORDER BY 1'''))

# COMMAND ----------

# DBTITLE 1,Section 12: Rx Data Profiling
# MAGIC %md
# MAGIC ## Section 12: Rx Data Profiling (rpt_sha_weekly)
# MAGIC Brand coverage, date range, TRx distribution, and territory coverage of the weekly prescription table used for impact analysis.

# COMMAND ----------

# DBTITLE 1,Rx brand coverage
# MAGIC %sql
# MAGIC SELECT BRAND_DESCRIPTION, COUNT(*) AS rows, COUNT(DISTINCT CUST_ID) AS hcps
# MAGIC FROM databricks_snowflake_migration_catalog.xsight_rpt_zn.rpt_sha_weekly
# MAGIC GROUP BY 1 ORDER BY rows DESC;

# COMMAND ----------

# DBTITLE 1,Rx date range, TRx distribution, territory coverage
print("Date range:")
display(spark.sql(f'SELECT MIN(WEEKEND_DATE) AS min_weekend_date, MAX(WEEKEND_DATE) AS max_weekend_date, MIN(MONTH_NAME) AS min_month, MAX(MONTH_NAME) AS max_month FROM {qtbl("rpt_sha_weekly")}'))

print("TRx distribution:")
display(spark.sql(f'SELECT ROUND(AVG(TRX_COUNT),2) AS avg_trx, ROUND(PERCENTILE(TRX_COUNT,0.5),2) AS median_trx, MAX(TRX_COUNT) AS max_trx FROM {qtbl("rpt_sha_weekly")}'))

print("Territory coverage:")
display(spark.sql(f'SELECT COUNT(DISTINCT TERRITORY) AS territories_in_sha FROM {qtbl("rpt_sha_weekly")}'))

# COMMAND ----------

# DBTITLE 1,Section 13: Summary Findings & Recommendations
# MAGIC %md
# MAGIC ## Section 13: Summary Findings & Recommendations
# MAGIC
# MAGIC ### 1. Total HCPs & channel coverage
# MAGIC Across the 5 HCP-linked channels (ISA calls, POD, samples, savings card, tele — website excluded, see #4), **28,224 distinct HCPs** were touched. Distribution by number of channels touched:
# MAGIC
# MAGIC | Channels touched | HCP count |
# MAGIC |---|---|
# MAGIC | 1 | 19,072 (67.6%) |
# MAGIC | 2 | 5,539 |
# MAGIC | 3 | 2,726 |
# MAGIC | 4 | 829 |
# MAGIC | 5 (all channels) | 58 |
# MAGIC
# MAGIC Per-channel distinct HCPs: dz_isa 6,844; dz_tele_detail 14,945; dz_sample_activity 10,367; dz_savings_card 8,477; dz_pod 1,301.
# MAGIC
# MAGIC ### 2. ID mismatch — confirmed, no simple fix
# MAGIC Activity tables use `"Prf Profile Id"` (numeric, range -1 to ~2.0e10); dimension tables use `CUST_ID` (15-char alphanumeric, e.g. prefix `0001A`). A direct cast join produced **0 matches**, and stripping non-numeric characters from `CUST_ID` and casting also produced **0 matches** — there is no arithmetic transformation between the two ID systems. A direct cast join against `rpt_sha_weekly.HCP_ID` produced only 1,612 matches out of 64K dz_isa rows (likely coincidental numeric overlap, not a real key). By contrast, the dimension/Rx side is internally consistent: `rpt_cust_profile` ↔ `rpt_cust_territory` matched all 125,628 rows, `rpt_cust_territory` ↔ `rpt_sales_org` matched 155,690/155,728 rows, and `rpt_sha_weekly.CUST_ID` → `rpt_cust_profile` matched 26.1M/30.0M rows (87%). **A bridge/crosswalk table from the data owner is required** to link activity-table HCPs to the CUST_ID/HCP_ID dimension system.
# MAGIC
# MAGIC ### 3. Website gap
# MAGIC `dz_website_page."Profile Id"` and `"Site Id"` are **100% NULL** across all 3,790,241 rows — confirmed, no HCP linkage exists. `"Device Info"` is also degenerate: 100% of rows report `"mobile"`, which is suspicious and worth a data-owner follow-up (likely a pipeline/mapping bug rather than true device mix). Website data is usable only at an aggregate level: Audience Type splits Patient (59%) / HCP (37%) / Consumer (4%); top pages are Home, Dosing & Administration, and Savings & Support; top traffic source is Search Engines (46%) followed by Typed/Bookmarked (37%).
# MAGIC
# MAGIC ### 4. Date coverage gaps
# MAGIC | Table | Min date | Max date | Notes |
# MAGIC |---|---|---|---|
# MAGIC | dz_isa | 2021-01 | 2023-03 | Volume drops sharply after Jan 2022 (3,428/mo → ~200-300/mo) |
# MAGIC | dz_pod | 2021-01 | 2022-02 | Stops entirely in Feb 2022 |
# MAGIC | dz_sample_activity | 2021-01 | 2023-05 | Continues, lower volume from 2022 on |
# MAGIC | dz_savings_card | 2021-01 | 2023-05 | Ramps up sharply in 2023 (2x+ prior volume) |
# MAGIC | dz_tele_detail | 2021-01 | 2022-01 | Stops entirely in Jan 2022 (only 139 records that month) |
# MAGIC | dz_website_page | 2021-01 | 2023-07 | Continuous, largest table (3.79M rows) |
# MAGIC | rpt_sha_weekly (Rx) | 2019-02 | 2023-04 | Extends ~2 years before the activity window starts |
# MAGIC
# MAGIC Telemarketing and POD appear to have been **discontinued or migrated to a different source system around Jan/Feb 2022** — confirm with the data owner before treating a 2022+ omnichannel view as complete.
# MAGIC
# MAGIC ### 5. Data quality findings
# MAGIC * **dz_isa grain issue**: 64,101 total rows but only 21,048 distinct `("Activity Key", "Seq Number")` combinations — a single call can span multiple detail rows (e.g. same call broken into Safety / Efficacy / MOA / Dosing presentation rows). The natural key for a gold fact table needs an additional column (e.g. `"Presentation Name"`) or an explicit aggregation decision.
# MAGIC * **Specialty granularity mismatch**: `rpt_cust_profile.SPECIALTY` has 183 distinct detailed values (e.g. "GASTROENTEROLOGY", "PEDIATRIC GASTROENTEROLOGY", "MLP - GASTROENTEROLOGY"), while all 5 activity tables use only 4 rolled-up `"Sp Group"` buckets (Gastroenterology, IM/PCP, NP/PA, Other) and are consistent with each other. No 1:1 crosswalk exists between the two taxonomies in the data currently profiled.
# MAGIC * **Decile Value is consistent**: 0 HCPs had mismatched decile values between dz_isa and dz_tele_detail, and all deciles fall within the valid 1-10 range with no future-dated activity records in dz_isa.
# MAGIC * **Fill rates**: `"Rm Duration"`/`"Rm Start Time"`/`"Rm End Time"` in dz_isa are ~84% NULL (expected — remote-meeting fields don't apply to F2F calls); `"Request Saving Card"` in dz_tele_detail is 90% NULL; `"Col 0"`-`"Col 4"` in dz_isa are ~39% NULL and appear to be unused/staging columns worth confirming with the data owner.
# MAGIC
# MAGIC ### 6. Recommendations before building gold-layer tables
# MAGIC 1. Obtain an authoritative crosswalk between `"Prf Profile Id"` (activity systems) and `CUST_ID`/`HCP_ID` (dimension/Rx systems) — this is the single biggest blocker to a unified omnichannel HCP view.
# MAGIC 2. Decide the correct grain for `dz_isa` (call-level vs. call-detail-level) before aggregating.
# MAGIC 3. Clarify whether `dz_website_page` will ever carry HCP-level identity, or should be modeled as aggregate-only in the gold layer.
# MAGIC 4. Confirm why `dz_tele_detail` and `dz_pod` stop in early 2022, and whether a replacement source exists for 2022+.
# MAGIC 5. Request a specialty-to-Sp-Group crosswalk if finer-grained specialty analysis is needed downstream.
# MAGIC 6. Validate the `"Device Info" = 'mobile'` constant and the unused `"Col 0"`-`"Col 4"` columns in dz_isa with the source system owner.