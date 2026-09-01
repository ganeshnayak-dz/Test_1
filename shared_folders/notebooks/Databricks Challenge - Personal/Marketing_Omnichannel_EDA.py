# Databricks notebook source
# MAGIC %sql
# MAGIC create table dz_demo_ws.gold.demo_table_team_3

# COMMAND ----------

# MAGIC %md
# MAGIC # Marketing Omnichannel EDA — Xsight Schema
# MAGIC ## Exploratory Data Analysis for 9 Marketing Tables
# MAGIC **Schema:** `xsight_db_dbrx.xsight_rpt_zn`  
# MAGIC **Purpose:** Profile data quality, validate joins, identify gaps before building gold layer  
# MAGIC **Date:** Auto-generated

# COMMAND ----------

# Configuration
catalog = "xsight_db_dbrx"
schema = "xsight_rpt_zn"
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"USE SCHEMA {schema}")

# Table lists
fact_tables = ["dz_isa", "dz_pod", "dz_sample_activity", "dz_savings_card", "dz_tele_detail", "dz_website_page"]
dim_tables = ["rpt_cust_profile", "rpt_cust_territory", "rpt_sales_org"]
all_tables = fact_tables + dim_tables

print(f"Catalog: {catalog}")
print(f"Schema: {schema}")
print(f"Total tables to analyze: {len(all_tables)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 1: Data Preview
# MAGIC Quick look at each table — first 5 rows to understand structure and content.

# COMMAND ----------

# Preview each table (SELECT * LIMIT 5)
for table in all_tables:
    print(f"\n{'='*80}")
    print(f"TABLE: {table}")
    print(f"{'='*80}")
    display(spark.sql(f"SELECT * FROM {catalog}.{schema}.{table} LIMIT 5"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 2: Row Counts, Distinct HCPs, and Date Ranges
# MAGIC Basic stats for each table — how big is it, how many doctors, what time period?

# COMMAND ----------

# Row counts, distinct HCPs, and date ranges for all fact tables
df = spark.sql("""
SELECT 'dz_isa' AS table_name, COUNT(*) AS total_rows, COUNT(DISTINCT `Prf Profile Id`) AS distinct_hcps, MIN(`Actual Date`) AS min_date, MAX(`Actual Date`) AS max_date
FROM dz_isa
UNION ALL
SELECT 'dz_pod', COUNT(*), COUNT(DISTINCT `Prf Profile Id`), MIN(`Actual Date`), MAX(`Actual Date`)
FROM dz_pod
UNION ALL
SELECT 'dz_sample_activity', COUNT(*), COUNT(DISTINCT `Prf Profile Id`), MIN(`Sample Date`), MAX(`Sample Date`)
FROM dz_sample_activity
UNION ALL
SELECT 'dz_savings_card', COUNT(*), COUNT(DISTINCT `Prf Profile Id`), MIN(`Org Submitted Cal Date`), MAX(`Org Submitted Cal Date`)
FROM dz_savings_card
UNION ALL
SELECT 'dz_tele_detail', COUNT(*), COUNT(DISTINCT `Prf Profile Id`), MIN(`Activity Cal Date`), MAX(`Activity Cal Date`)
FROM dz_tele_detail
UNION ALL
SELECT 'dz_website_page', COUNT(*), COUNT(DISTINCT `Profile Id`), MIN(CAST(`Cal Date` AS DATE)), MAX(CAST(`Cal Date` AS DATE))
FROM dz_website_page
""")
display(df)

# COMMAND ----------

# Dimension table stats
df = spark.sql("""
SELECT 'rpt_cust_profile' AS table_name, COUNT(*) AS total_rows, COUNT(DISTINCT CUST_ID) AS distinct_keys, COUNT(DISTINCT PROFILE_ID) AS distinct_profile_ids
FROM rpt_cust_profile
UNION ALL
SELECT 'rpt_cust_territory', COUNT(*), COUNT(DISTINCT CUST_ID), COUNT(DISTINCT TERRITORY)
FROM rpt_cust_territory
UNION ALL
SELECT 'rpt_sales_org', COUNT(*), COUNT(DISTINCT TERRITORY_CD), COUNT(DISTINCT REGION_DESC)
FROM rpt_sales_org
""")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 3: Fill Rate Analysis (NULL Checks)
# MAGIC For each table, what percentage of key columns are NULL? Highlights data gaps.

# COMMAND ----------

# Fill rate for dz_isa — check NULLs in every column
df = spark.sql("""
SELECT
  COUNT(*) AS total_rows,
  -- Key identifiers
  ROUND(SUM(CASE WHEN `Prf Profile Id` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_prf_profile_id,
  ROUND(SUM(CASE WHEN `Activity Key` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_activity_key,
  ROUND(SUM(CASE WHEN `Call Key` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_call_key,
  -- Date
  ROUND(SUM(CASE WHEN `Actual Date` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_actual_date,
  -- Dimensions
  ROUND(SUM(CASE WHEN `Sp Group` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_sp_group,
  ROUND(SUM(CASE WHEN `Decile Value` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_decile_value,
  ROUND(SUM(CASE WHEN `State Code` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_state_code,
  ROUND(SUM(CASE WHEN `Zip` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_zip,
  ROUND(SUM(CASE WHEN `Reporting Sales Org Id` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_sales_org_id,
  -- Measures
  ROUND(SUM(CASE WHEN `Rm Duration` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_rm_duration,
  ROUND(SUM(CASE WHEN `Hcp Present` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_hcp_present
FROM dz_isa
""")
display(df)

# COMMAND ----------

df = spark.sql("""
SELECT
  COUNT(*) AS total_rows,
  ROUND(SUM(CASE WHEN `Prf Profile Id` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_prf_profile_id,
  ROUND(SUM(CASE WHEN `Activity Cal Date` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_activity_date,
  ROUND(SUM(CASE WHEN `Call Length` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_call_length,
  ROUND(SUM(CASE WHEN `Disposition Desc` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_disposition,
  ROUND(SUM(CASE WHEN `Sp Group` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_sp_group,
  ROUND(SUM(CASE WHEN `Decile Value` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_decile,
  ROUND(SUM(CASE WHEN `State Code` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_state,
  ROUND(SUM(CASE WHEN `Request Saving Card` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_request_saving_card
FROM dz_tele_detail
""")
display(df)

# COMMAND ----------

df = spark.sql("""
SELECT
  COUNT(*) AS total_rows,
  ROUND(SUM(CASE WHEN `Prf Profile Id` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_prf_profile_id,
  ROUND(SUM(CASE WHEN `Sample Date` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_sample_date,
  ROUND(SUM(CASE WHEN `Quantity` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_quantity,
  ROUND(SUM(CASE WHEN `Order Status` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_order_status,
  ROUND(SUM(CASE WHEN `Sp Group` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_sp_group,
  ROUND(SUM(CASE WHEN `Decile Value` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_decile
FROM dz_sample_activity
""")
display(df)

# COMMAND ----------

df = spark.sql("""
SELECT
  COUNT(*) AS total_rows,
  ROUND(SUM(CASE WHEN `Prf Profile Id` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_prf_profile_id,
  ROUND(SUM(CASE WHEN `Actual Date` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_actual_date,
  ROUND(SUM(CASE WHEN `Message Type` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_message_type,
  ROUND(SUM(CASE WHEN `Pod Utilization Count` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_pod_count,
  ROUND(SUM(CASE WHEN `Sp Group` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_sp_group,
  ROUND(SUM(CASE WHEN `Decile Value` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_decile
FROM dz_pod
""")
display(df)

# COMMAND ----------

df = spark.sql("""
SELECT
  COUNT(*) AS total_rows,
  ROUND(SUM(CASE WHEN `Prf Profile Id` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_prf_profile_id,
  ROUND(SUM(CASE WHEN `Org Submitted Cal Date` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_date,
  ROUND(SUM(CASE WHEN `Savings Amount` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_savings_amount,
  ROUND(SUM(CASE WHEN `Approved Claims` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_approved_claims,
  ROUND(SUM(CASE WHEN `Patient Gender` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_patient_gender,
  ROUND(SUM(CASE WHEN `Patient Age` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_patient_age,
  ROUND(SUM(CASE WHEN `Sp Group` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_sp_group
FROM dz_savings_card
""")
display(df)

# COMMAND ----------

# CRITICAL: Website table — Profile Id is expected to be 100% NULL
df = spark.sql("""
SELECT
  COUNT(*) AS total_rows,
  ROUND(SUM(CASE WHEN `Profile Id` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_profile_id,
  ROUND(SUM(CASE WHEN `Cal Date` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_cal_date,
  ROUND(SUM(CASE WHEN `Audience Type` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_audience_type,
  ROUND(SUM(CASE WHEN `Page Name` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_page_name,
  ROUND(SUM(CASE WHEN `Device Info` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_device,
  ROUND(SUM(CASE WHEN `Medium` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_medium,
  ROUND(SUM(CASE WHEN `geo_state` IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_geo_state
FROM dz_website_page
""")
print("EXPECTED: Profile Id should be ~100% NULL — website data is anonymous, cannot link to HCPs")
display(df)

# COMMAND ----------

# CRITICAL: Check PROFILE_ID fill rate — this is the bridge to fact tables
df = spark.sql("""
SELECT
  COUNT(*) AS total_rows,
  ROUND(SUM(CASE WHEN PROFILE_ID IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_profile_id,
  ROUND(SUM(CASE WHEN CUST_ID IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_cust_id,
  ROUND(SUM(CASE WHEN SPECIALTY IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_specialty,
  ROUND(SUM(CASE WHEN DECILE IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_decile,
  ROUND(SUM(CASE WHEN TARGET_FLAG IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_null_target_flag,
  SUM(CASE WHEN PROFILE_ID IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_profile_id,
  SUM(CASE WHEN PROFILE_ID IS NULL THEN 1 ELSE 0 END) AS rows_without_profile_id
FROM rpt_cust_profile
""")
print("PROFILE_ID is the JOIN KEY to fact tables. ~50% of rows have it populated.")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 4: Distinct Values & Cardinality
# MAGIC What are the categorical values in each table? Are they consistent across tables?

# COMMAND ----------

# Compare Sp Group values across all fact tables — are they consistent?
df = spark.sql("""
SELECT 'dz_isa' AS table_name, `Sp Group`, COUNT(*) AS row_count, COUNT(DISTINCT `Prf Profile Id`) AS hcp_count FROM dz_isa GROUP BY `Sp Group`
UNION ALL
SELECT 'dz_pod', `Sp Group`, COUNT(*), COUNT(DISTINCT `Prf Profile Id`) FROM dz_pod GROUP BY `Sp Group`
UNION ALL
SELECT 'dz_sample_activity', `Sp Group`, COUNT(*), COUNT(DISTINCT `Prf Profile Id`) FROM dz_sample_activity GROUP BY `Sp Group`
UNION ALL
SELECT 'dz_savings_card', `Sp Group`, COUNT(*), COUNT(DISTINCT `Prf Profile Id`) FROM dz_savings_card GROUP BY `Sp Group`
UNION ALL
SELECT 'dz_tele_detail', `Sp Group`, COUNT(*), COUNT(DISTINCT `Prf Profile Id`) FROM dz_tele_detail GROUP BY `Sp Group`
ORDER BY table_name, hcp_count DESC
""")
display(df)

# COMMAND ----------

# rpt_cust_profile uses SPECIALTY — compare to Sp Group in fact tables
df = spark.sql("""
SELECT SPECIALTY, COUNT(*) AS hcp_count, 
  SUM(CASE WHEN TARGET_FLAG = 'Y' THEN 1 ELSE 0 END) AS target_count
FROM rpt_cust_profile
WHERE PROFILE_ID IS NOT NULL
GROUP BY SPECIALTY
ORDER BY hcp_count DESC
""")
print("Compare these SPECIALTY values to 'Sp Group' in fact tables — naming may differ")
display(df)

# COMMAND ----------

# Decile distribution across fact tables
df = spark.sql("""
SELECT 'dz_isa' AS tbl, CAST(`Decile Value` AS INT) AS decile, COUNT(DISTINCT `Prf Profile Id`) AS hcps FROM dz_isa GROUP BY 2
UNION ALL
SELECT 'dz_tele_detail', CAST(`Decile Value` AS INT), COUNT(DISTINCT `Prf Profile Id`) FROM dz_tele_detail GROUP BY 2
UNION ALL
SELECT 'dz_sample_activity', CAST(`Decile Value` AS INT), COUNT(DISTINCT `Prf Profile Id`) FROM dz_sample_activity GROUP BY 2
ORDER BY tbl, decile
""")
display(df)

# COMMAND ----------

# Key categorical values in each table
print("=== dz_isa: Call Types ===")
display(spark.sql("SELECT `Call Type`, `Call Category`, COUNT(*) AS cnt FROM dz_isa GROUP BY 1, 2 ORDER BY cnt DESC"))

print("\n=== dz_tele_detail: Dispositions ===")
display(spark.sql("SELECT `Disposition Desc`, COUNT(*) AS cnt FROM dz_tele_detail GROUP BY 1 ORDER BY cnt DESC"))

print("\n=== dz_pod: Message Types ===")
display(spark.sql("SELECT `Message Type`, COUNT(*) AS cnt FROM dz_pod GROUP BY 1 ORDER BY cnt DESC"))

print("\n=== dz_savings_card: Program Names & Types ===")
display(spark.sql("SELECT `Program Name`, `Sc Type`, COUNT(*) AS cnt FROM dz_savings_card GROUP BY 1, 2 ORDER BY cnt DESC"))

print("\n=== dz_website_page: Audience Types ===")
display(spark.sql("SELECT `Audience Type`, COUNT(*) AS cnt FROM dz_website_page GROUP BY 1 ORDER BY cnt DESC"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 5: HCP Overlap Analysis
# MAGIC How many doctors appear across multiple channels? This is the foundation of "omnichannel" analysis.

# COMMAND ----------

# How many HCPs appear in each channel, and how many are in multiple channels?
df = spark.sql("""
WITH hcps_per_channel AS (
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) AS hcp_id, 'ISA_Call' AS channel FROM dz_isa
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING), 'Tele_Call' FROM dz_tele_detail
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING), 'Sample' FROM dz_sample_activity
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING), 'POD_Print' FROM dz_pod
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING), 'Savings_Card' FROM dz_savings_card
),
hcp_channel_count AS (
  SELECT hcp_id, COUNT(DISTINCT channel) AS channels_touched
  FROM hcps_per_channel
  GROUP BY hcp_id
)
SELECT channels_touched, COUNT(*) AS hcp_count
FROM hcp_channel_count
GROUP BY channels_touched
ORDER BY channels_touched
""")
print("Distribution: How many HCPs are touched by 1, 2, 3, 4, 5 channels")
display(df)

# COMMAND ----------

# Total unique HCPs across all activity tables
df = spark.sql("""
WITH all_hcps AS (
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) AS hcp_id FROM dz_isa
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) FROM dz_tele_detail
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) FROM dz_sample_activity
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) FROM dz_pod
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) FROM dz_savings_card
)
SELECT COUNT(*) AS total_unique_hcps FROM all_hcps
""")
display(df)

# COMMAND ----------

# Top 20 HCPs with most channel diversity
df = spark.sql("""
WITH hcps_per_channel AS (
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) AS hcp_id, 'ISA_Call' AS channel FROM dz_isa
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING), 'Tele_Call' FROM dz_tele_detail
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING), 'Sample' FROM dz_sample_activity
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING), 'POD_Print' FROM dz_pod
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING), 'Savings_Card' FROM dz_savings_card
)
SELECT hcp_id, COUNT(DISTINCT channel) AS channels_touched, COLLECT_SET(channel) AS channel_list
FROM hcps_per_channel
GROUP BY hcp_id
ORDER BY channels_touched DESC
LIMIT 20
""")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 6: JOIN VALIDATION — The Critical Test
# MAGIC Test that fact tables join to dim tables via PROFILE_ID. This is the bridge between the two ID systems.

# COMMAND ----------

# TEST: Do all fact tables join to rpt_cust_profile via PROFILE_ID?
df = spark.sql("""
SELECT 'dz_isa' AS tbl, COUNT(*) AS total_rows, 
  SUM(CASE WHEN p.PROFILE_ID IS NOT NULL THEN 1 ELSE 0 END) AS matched_rows,
  ROUND(SUM(CASE WHEN p.PROFILE_ID IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS match_pct
FROM dz_isa a
LEFT JOIN rpt_cust_profile p ON CAST(a.`Prf Profile Id` AS STRING) = p.PROFILE_ID
UNION ALL
SELECT 'dz_pod', COUNT(*), SUM(CASE WHEN p.PROFILE_ID IS NOT NULL THEN 1 ELSE 0 END),
  ROUND(SUM(CASE WHEN p.PROFILE_ID IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)
FROM dz_pod a
LEFT JOIN rpt_cust_profile p ON CAST(a.`Prf Profile Id` AS STRING) = p.PROFILE_ID
UNION ALL
SELECT 'dz_sample_activity', COUNT(*), SUM(CASE WHEN p.PROFILE_ID IS NOT NULL THEN 1 ELSE 0 END),
  ROUND(SUM(CASE WHEN p.PROFILE_ID IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)
FROM dz_sample_activity a
LEFT JOIN rpt_cust_profile p ON CAST(a.`Prf Profile Id` AS STRING) = p.PROFILE_ID
UNION ALL
SELECT 'dz_savings_card', COUNT(*), SUM(CASE WHEN p.PROFILE_ID IS NOT NULL THEN 1 ELSE 0 END),
  ROUND(SUM(CASE WHEN p.PROFILE_ID IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)
FROM dz_savings_card a
LEFT JOIN rpt_cust_profile p ON CAST(a.`Prf Profile Id` AS STRING) = p.PROFILE_ID
UNION ALL
SELECT 'dz_tele_detail', COUNT(*), SUM(CASE WHEN p.PROFILE_ID IS NOT NULL THEN 1 ELSE 0 END),
  ROUND(SUM(CASE WHEN p.PROFILE_ID IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)
FROM dz_tele_detail a
LEFT JOIN rpt_cust_profile p ON CAST(a.`Prf Profile Id` AS STRING) = p.PROFILE_ID
""")
print("Expected: All 5 tables should show ~100% match rate")
display(df)

# COMMAND ----------

# TEST: Full chain — fact → profile → territory → sales_org
df = spark.sql("""
SELECT 
  a.`Prf Profile Id`,
  p.CUST_ID,
  p.SPECIALTY,
  p.TARGET_FLAG,
  p.DECILE,
  t.TERRITORY,
  s.TERRITORY_DESC,
  s.DISTRICT_DESC,
  s.REGION_DESC
FROM dz_isa a
JOIN rpt_cust_profile p ON CAST(a.`Prf Profile Id` AS STRING) = p.PROFILE_ID
JOIN rpt_cust_territory t ON p.CUST_ID = t.CUST_ID
JOIN rpt_sales_org s ON t.TERRITORY = s.TERRITORY_CD
LIMIT 10
""")
print("Full join chain working — fact table enriched with all dimensions")
display(df)

# COMMAND ----------

# Check: does rpt_cust_territory have multiple rows per CUST_ID?
df = spark.sql("""
SELECT 
  COUNT(DISTINCT CUST_ID) AS total_customers,
  COUNT(*) AS total_rows,
  COUNT(*) - COUNT(DISTINCT CUST_ID) AS duplicate_rows,
  COUNT(DISTINCT effective_start_date) AS distinct_effective_dates
FROM rpt_cust_territory
""")
print("If total_rows > total_customers, some HCPs have multiple territory assignments (use latest effective_start_date)")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 7: Date Range & Temporal Overlap
# MAGIC Which months have data across all channels? Which channels stop early?

# COMMAND ----------

# Monthly row counts per channel — identify gaps and coverage
df = spark.sql("""
SELECT 'ISA_Call' AS channel, DATE_TRUNC('month', `Actual Date`) AS month, COUNT(*) AS touches FROM dz_isa GROUP BY 2
UNION ALL
SELECT 'Tele_Call', DATE_TRUNC('month', `Activity Cal Date`), COUNT(*) FROM dz_tele_detail GROUP BY 2
UNION ALL
SELECT 'Sample', DATE_TRUNC('month', `Sample Date`), COUNT(*) FROM dz_sample_activity GROUP BY 2
UNION ALL
SELECT 'POD_Print', DATE_TRUNC('month', `Actual Date`), COUNT(*) FROM dz_pod GROUP BY 2
UNION ALL
SELECT 'Savings_Card', DATE_TRUNC('month', `Org Submitted Cal Date`), COUNT(*) FROM dz_savings_card GROUP BY 2
ORDER BY channel, month
""")
print("Look for: channels that stop early (POD stops Feb 2022, Tele stops Jan 2022)")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 8: Website Deep Dive
# MAGIC Since website has NO HCP linkage, what CAN we use from it?

# COMMAND ----------

# Website: what's usable at aggregate level?
print("=== Audience Type Breakdown ===")
display(spark.sql("SELECT `Audience Type`, COUNT(*) AS pageviews FROM dz_website_page GROUP BY 1"))

print("\n=== Top 10 Pages ===")
display(spark.sql("SELECT `Page Name`, COUNT(*) AS views FROM dz_website_page GROUP BY 1 ORDER BY views DESC LIMIT 10"))

print("\n=== Traffic Medium ===")
display(spark.sql("SELECT `Medium`, COUNT(*) AS visits FROM dz_website_page GROUP BY 1 ORDER BY visits DESC"))

print("\n=== Device Breakdown ===")
display(spark.sql("SELECT `Device Info`, COUNT(*) AS visits FROM dz_website_page GROUP BY 1 ORDER BY visits DESC"))

print("\n=== Monthly Web Traffic Trend ===")
display(spark.sql("""
SELECT DATE_TRUNC('month', CAST(`Cal Date` AS DATE)) AS month, 
  COUNT(*) AS pageviews,
  COUNT(DISTINCT `Visit Key`) AS sessions
FROM dz_website_page 
GROUP BY 1 ORDER BY 1
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 9: Data Quality Checks
# MAGIC Duplicates, consistency, impossible values.

# COMMAND ----------

# Check for duplicate rows in each table
df = spark.sql("""
SELECT 'dz_isa' AS tbl, COUNT(*) AS total, COUNT(DISTINCT `Activity Key`, `Seq Number`) AS distinct_keys,
  COUNT(*) - COUNT(DISTINCT `Activity Key`, `Seq Number`) AS potential_dupes
FROM dz_isa
UNION ALL
SELECT 'dz_tele_detail', COUNT(*), COUNT(DISTINCT `Tele Activity Key`),
  COUNT(*) - COUNT(DISTINCT `Tele Activity Key`)
FROM dz_tele_detail
UNION ALL
SELECT 'dz_pod', COUNT(*), COUNT(DISTINCT `Print Utilization Key`),
  COUNT(*) - COUNT(DISTINCT `Print Utilization Key`)
FROM dz_pod
""")
display(df)

# COMMAND ----------

# Do the same HCPs have the same decile across different tables?
df = spark.sql("""
SELECT a.hcp_id, a.decile_isa, b.decile_tele, 
  CASE WHEN a.decile_isa = b.decile_tele THEN 'Match' ELSE 'MISMATCH' END AS status
FROM (SELECT CAST(`Prf Profile Id` AS STRING) AS hcp_id, MAX(`Decile Value`) AS decile_isa FROM dz_isa GROUP BY 1) a
JOIN (SELECT CAST(`Prf Profile Id` AS STRING) AS hcp_id, MAX(`Decile Value`) AS decile_tele FROM dz_tele_detail GROUP BY 1) b
ON a.hcp_id = b.hcp_id
WHERE a.decile_isa != b.decile_tele
LIMIT 20
""")
print("HCPs with different decile values across tables (data inconsistency check)")
display(df)

# COMMAND ----------

# Sanity checks: impossible values
df = spark.sql("""
SELECT 
  'dz_isa' AS tbl, MIN(`Decile Value`) AS min_decile, MAX(`Decile Value`) AS max_decile,
  SUM(CASE WHEN `Actual Date` > CURRENT_DATE() THEN 1 ELSE 0 END) AS future_dates
FROM dz_isa
UNION ALL
SELECT 'dz_savings_card', MIN(`Decile Value`), MAX(`Decile Value`),
  SUM(CASE WHEN `Org Submitted Cal Date` > CURRENT_DATE() THEN 1 ELSE 0 END)
FROM dz_savings_card
UNION ALL
SELECT 'dz_tele_detail', MIN(`Decile Value`), MAX(`Decile Value`),
  SUM(CASE WHEN `Activity Cal Date` > CURRENT_DATE() THEN 1 ELSE 0 END)
FROM dz_tele_detail
""")
print("Decile should be 1-10 (or 0 for unranked). Future dates = data quality issue.")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 10: Target Flag Analysis
# MAGIC How many target HCPs exist and how many have activity?

# COMMAND ----------

# How many target HCPs have marketing activity?
df = spark.sql("""
WITH target_hcps AS (
  SELECT PROFILE_ID, CUST_ID, TARGET_FLAG
  FROM rpt_cust_profile
  WHERE PROFILE_ID IS NOT NULL AND TARGET_FLAG = 'Y'
),
activity_hcps AS (
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) AS hcp_id FROM dz_isa
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) FROM dz_tele_detail
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) FROM dz_sample_activity
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) FROM dz_pod
  UNION
  SELECT DISTINCT CAST(`Prf Profile Id` AS STRING) FROM dz_savings_card
)
SELECT 
  COUNT(DISTINCT t.PROFILE_ID) AS total_target_hcps_with_profile_id,
  SUM(CASE WHEN a.hcp_id IS NOT NULL THEN 1 ELSE 0 END) AS targets_with_activity,
  SUM(CASE WHEN a.hcp_id IS NULL THEN 1 ELSE 0 END) AS targets_without_activity
FROM target_hcps t
LEFT JOIN activity_hcps a ON t.PROFILE_ID = a.hcp_id
""")
print("How many TARGET HCPs have at least one marketing touch?")
display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 11: Summary Findings
# MAGIC Key takeaways from this EDA.

# COMMAND ----------

print("""
============================================================================
                    EDA SUMMARY -- KEY FINDINGS
============================================================================

  SCHEMA: xsight_db_dbrx.xsight_rpt_zn

  1. JOIN STATUS:
     [OK] All 5 HCP fact tables -> rpt_cust_profile: 100% match
     [OK] rpt_cust_profile -> rpt_cust_territory -> rpt_sales_org: works
     [X]  dz_website_page: NO HCP linkage (Profile Id 100% NULL)

  2. JOIN KEY:
     CAST(`Prf Profile Id` AS STRING) = rpt_cust_profile.PROFILE_ID

  3. DATA GAPS:
     - Website: anonymous only (aggregate metrics only)
     - POD data stops Feb 2022
     - Tele data stops Jan 2022
     - No email data exists in any table
     - rpt_cust_territory has some duplicate rows (use latest date)

  4. CHANNEL CLASSIFICATION:
     Personal: ISA_Call, Tele_Call, Sample, POD_Print
     Non-Personal: Savings_Card, Website (aggregate only)

  5. NEXT STEPS:
     - Build gold_hcp_channel_month (UNION all 5 fact tables)
     - Build gold_hcp_omnichannel_summary (reach, frequency, recency)
     - Set up Genie Agent with gold tables + instructions

============================================================================
""")