# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer Build — Marketing Omnichannel Analytics**Team 3 — Databricks Challenge**All tables this notebook creates are suffixed **`_team_3`** and land in **`dz_demo_ws.gold`**.| # | Table | Grain | Purpose ||---|-------|-------|---------|| 1 | `gold_hcp_channel_month_team_3` | HCP x Channel x Month | Unified omnichannel activity fact || 2 | `gold_hcp_omnichannel_summary_team_3` | One row per HCP | Reach, frequency, recency, engagement tiers, gap flags || 3 | `gold_activity_rx_impact_team_3` | One row per HCP with Rx data | Touch level vs TRx/NRx — association, not causation || 4 | `gold_website_monthly_team_3` | Month x Audience x Medium x Device | Website aggregate — no HCP link || 5 | `gold_website_top_pages_team_3` | Month x Page | Website top pages — no HCP link |**Approach:** each channel is built as its own **temp view** first, so every step is visible andeasy to check independently before anything is joined or unioned. Temp views only live for thissession — the final `CREATE OR REPLACE TABLE` statements are what actually persist.**Source:** `xsight_db_dbrx.xsight_rpt_zn`**Target:** `dz_demo_ws.gold`**Currently active channels (5):** ISA_Call, Tele_Call, Sample, POD_Print, Savings_Card — thesematch the 9 originally assigned tables.**Commented out for now:** Email (`dz_oce_consolidated`) and Speaker Program(`rpt_speaker_program`) — neither is one of the 9 assigned tables. Both views are written andready in Section 2, just uncomment them (and their line in the Section 3 union) if we decide toinclude them later.**No dates are hardcoded.** The reference date used for recency/engagement is computed live fromthe data (`v_reference_date`), so this notebook always reflects the full dataset as it exists atrun time. Adjust this only if/when we deliberately want to simulate an "as-of" date for the Genie Agent.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 0: Setup

# COMMAND ----------

source_catalog = "xsight_db_dbrx"source_schema = "xsight_rpt_zn"target_catalog_schema = "dz_demo_ws.gold"TABLE_1 = "gold_hcp_channel_month_team_3"TABLE_2 = "gold_hcp_omnichannel_summary_team_3"TABLE_3 = "gold_activity_rx_impact_team_3"TABLE_4 = "gold_website_monthly_team_3"TABLE_5 = "gold_website_top_pages_team_3"spark.sql(f"USE CATALOG {source_catalog}")spark.sql(f"USE SCHEMA {source_schema}")spark.sql(f"CREATE SCHEMA IF NOT EXISTS {target_catalog_schema}")print(f"Source: {source_catalog}.{source_schema}")print(f"Target: {target_catalog_schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 1: Dimension ChainOne temp view: dedupe `rpt_cust_territory` to the latest record per HCP (it currently has 2 rowsper `CUST_ID`, tagged with `effective_start_date`).

# COMMAND ----------

-- Dedupe territory to the latest record per HCP (table has 2 rows per CUST_ID)CREATE OR REPLACE TEMP VIEW v_territory_deduped ASSELECT CUST_ID, TERRITORY,  ROW_NUMBER() OVER (PARTITION BY CUST_ID ORDER BY effective_start_date DESC) AS rnFROM xsight_db_dbrx.xsight_rpt_zn.rpt_cust_territory;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 2: Channel Temp ViewsEach channel becomes one temp view: aggregate to (hcp_id, channel, month), keep channel-specificcolumns, fill in `NULL` for columns that don't apply to that channel. Same column list and orderin every view, so they can be UNIONed later.

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TEMP VIEW v_isa_activity AS
# MAGIC SELECT  CAST(`Prf Profile Id` AS STRING) AS hcp_id,  'ISA_Call' AS channel,  'Personal' AS channel_group,  DATE_TRUNC('month', `Actual Date`) AS activity_month,  COUNT(*) AS touch_count,  COUNT(DISTINCT `Actual Date`) AS distinct_days,  MAX(`Call Type`) AS call_type,  MAX(`Call Category`) AS call_category,  MAX(`Hcp Present`) AS hcp_present,  MAX(`Interaction Type`) AS interaction_type,  MAX(`Col 1`) AS product_name,  MAX(`Meal`) AS meal_flag,  CAST(NULL AS DECIMAL(38,0)) AS call_length,  CAST(NULL AS STRING) AS disposition,  CAST(NULL AS STRING) AS mail_sent,  CAST(NULL AS DECIMAL(38,0)) AS sample_qty,  CAST(NULL AS STRING) AS order_status,  CAST(NULL AS STRING) AS message_type,  CAST(NULL AS DECIMAL(38,0)) AS pod_count,  CAST(NULL AS DECIMAL(38,2)) AS savings_amount,  CAST(NULL AS DECIMAL(38,0)) AS approved_claims,  CAST(NULL AS DECIMAL(38,0)) AS submitted_claims,  CAST(NULL AS DECIMAL(38,0)) AS reversed_claims,  CAST(NULL AS DECIMAL(38,0)) AS days_supply,  CAST(NULL AS DECIMAL(38,0)) AS patient_age,  CAST(NULL AS STRING) AS patient_gender,  CAST(NULL AS STRING) AS program_name,  CAST(NULL AS STRING) AS mail_instance_id,  CAST(NULL AS STRING) AS writer_flag,  CAST(NULL AS STRING) AS freq_bucketFROM xsight_db_dbrx.xsight_rpt_zn.dz_isaGROUP BY 1, 2, 3, 4;

# COMMAND ----------

CREATE OR REPLACE TEMP VIEW v_tele_activity ASSELECT  CAST(`Prf Profile Id` AS STRING) AS hcp_id,  'Tele_Call' AS channel,  'Personal' AS channel_group,  DATE_TRUNC('month', `Activity Cal Date`) AS activity_month,  COUNT(*) AS touch_count,  COUNT(DISTINCT `Activity Cal Date`) AS distinct_days,  CAST(NULL AS STRING) AS call_type,  CAST(NULL AS STRING) AS call_category,  CAST(NULL AS STRING) AS hcp_present,  CAST(NULL AS STRING) AS interaction_type,  CAST(NULL AS STRING) AS product_name,  CAST(NULL AS STRING) AS meal_flag,  CAST(AVG(`Call Length`) AS DECIMAL(38,0)) AS call_length,  MAX(`Disposition Desc`) AS disposition,  MAX(`Mail Sent`) AS mail_sent,  CAST(NULL AS DECIMAL(38,0)) AS sample_qty,  CAST(NULL AS STRING) AS order_status,  CAST(NULL AS STRING) AS message_type,  CAST(NULL AS DECIMAL(38,0)) AS pod_count,  CAST(NULL AS DECIMAL(38,2)) AS savings_amount,  CAST(NULL AS DECIMAL(38,0)) AS approved_claims,  CAST(NULL AS DECIMAL(38,0)) AS submitted_claims,  CAST(NULL AS DECIMAL(38,0)) AS reversed_claims,  CAST(NULL AS DECIMAL(38,0)) AS days_supply,  CAST(NULL AS DECIMAL(38,0)) AS patient_age,  CAST(NULL AS STRING) AS patient_gender,  CAST(NULL AS STRING) AS program_name,  CAST(NULL AS STRING) AS mail_instance_id,  CAST(NULL AS STRING) AS writer_flag,  CAST(NULL AS STRING) AS freq_bucketFROM xsight_db_dbrx.xsight_rpt_zn.dz_tele_detailGROUP BY 1, 2, 3, 4;

# COMMAND ----------

CREATE OR REPLACE TEMP VIEW v_sample_activity ASSELECT  CAST(`Prf Profile Id` AS STRING) AS hcp_id,  'Sample' AS channel,  'Personal' AS channel_group,  DATE_TRUNC('month', `Sample Date`) AS activity_month,  COUNT(*) AS touch_count,  COUNT(DISTINCT `Sample Date`) AS distinct_days,  CAST(NULL AS STRING) AS call_type,  CAST(NULL AS STRING) AS call_category,  CAST(NULL AS STRING) AS hcp_present,  CAST(NULL AS STRING) AS interaction_type,  CAST(NULL AS STRING) AS product_name,  CAST(NULL AS STRING) AS meal_flag,  CAST(NULL AS DECIMAL(38,0)) AS call_length,  CAST(NULL AS STRING) AS disposition,  CAST(NULL AS STRING) AS mail_sent,  SUM(`Quantity`) AS sample_qty,  MAX(`Order Status`) AS order_status,  CAST(NULL AS STRING) AS message_type,  CAST(NULL AS DECIMAL(38,0)) AS pod_count,  CAST(NULL AS DECIMAL(38,2)) AS savings_amount,  CAST(NULL AS DECIMAL(38,0)) AS approved_claims,  CAST(NULL AS DECIMAL(38,0)) AS submitted_claims,  CAST(NULL AS DECIMAL(38,0)) AS reversed_claims,  CAST(NULL AS DECIMAL(38,0)) AS days_supply,  CAST(NULL AS DECIMAL(38,0)) AS patient_age,  CAST(NULL AS STRING) AS patient_gender,  CAST(NULL AS STRING) AS program_name,  CAST(NULL AS STRING) AS mail_instance_id,  CAST(NULL AS STRING) AS writer_flag,  CAST(NULL AS STRING) AS freq_bucketFROM xsight_db_dbrx.xsight_rpt_zn.dz_sample_activityGROUP BY 1, 2, 3, 4;

# COMMAND ----------

CREATE OR REPLACE TEMP VIEW v_pod_activity ASSELECT  CAST(`Prf Profile Id` AS STRING) AS hcp_id,  'POD_Print' AS channel,  'Personal' AS channel_group,  DATE_TRUNC('month', `Actual Date`) AS activity_month,  COUNT(*) AS touch_count,  COUNT(DISTINCT `Actual Date`) AS distinct_days,  CAST(NULL AS STRING) AS call_type,  CAST(NULL AS STRING) AS call_category,  CAST(NULL AS STRING) AS hcp_present,  CAST(NULL AS STRING) AS interaction_type,  CAST(NULL AS STRING) AS product_name,  CAST(NULL AS STRING) AS meal_flag,  CAST(NULL AS DECIMAL(38,0)) AS call_length,  CAST(NULL AS STRING) AS disposition,  CAST(NULL AS STRING) AS mail_sent,  CAST(NULL AS DECIMAL(38,0)) AS sample_qty,  CAST(NULL AS STRING) AS order_status,  MAX(`Message Type`) AS message_type,  SUM(`Pod Utilization Count`) AS pod_count,  CAST(NULL AS DECIMAL(38,2)) AS savings_amount,  CAST(NULL AS DECIMAL(38,0)) AS approved_claims,  CAST(NULL AS DECIMAL(38,0)) AS submitted_claims,  CAST(NULL AS DECIMAL(38,0)) AS reversed_claims,  CAST(NULL AS DECIMAL(38,0)) AS days_supply,  CAST(NULL AS DECIMAL(38,0)) AS patient_age,  CAST(NULL AS STRING) AS patient_gender,  CAST(NULL AS STRING) AS program_name,  CAST(NULL AS STRING) AS mail_instance_id,  CAST(NULL AS STRING) AS writer_flag,  CAST(NULL AS STRING) AS freq_bucketFROM xsight_db_dbrx.xsight_rpt_zn.dz_podGROUP BY 1, 2, 3, 4;

# COMMAND ----------

CREATE OR REPLACE TEMP VIEW v_savings_card_activity ASSELECT  CAST(`Prf Profile Id` AS STRING) AS hcp_id,  'Savings_Card' AS channel,  'Non-Personal' AS channel_group,  DATE_TRUNC('month', `Org Submitted Cal Date`) AS activity_month,  COUNT(*) AS touch_count,  COUNT(DISTINCT `Org Submitted Cal Date`) AS distinct_days,  CAST(NULL AS STRING) AS call_type,  CAST(NULL AS STRING) AS call_category,  CAST(NULL AS STRING) AS hcp_present,  CAST(NULL AS STRING) AS interaction_type,  CAST(NULL AS STRING) AS product_name,  CAST(NULL AS STRING) AS meal_flag,  CAST(NULL AS DECIMAL(38,0)) AS call_length,  CAST(NULL AS STRING) AS disposition,  CAST(NULL AS STRING) AS mail_sent,  CAST(NULL AS DECIMAL(38,0)) AS sample_qty,  CAST(NULL AS STRING) AS order_status,  CAST(NULL AS STRING) AS message_type,  CAST(NULL AS DECIMAL(38,0)) AS pod_count,  SUM(`Savings Amount`) AS savings_amount,  SUM(`Approved Claims`) AS approved_claims,  SUM(`Submitted Claims`) AS submitted_claims,  SUM(`Reversed Claims`) AS reversed_claims,  CAST(AVG(`Days Supply`) AS DECIMAL(38,0)) AS days_supply,  CAST(AVG(`Patient Age`) AS DECIMAL(38,0)) AS patient_age,  MAX(`Patient Gender`) AS patient_gender,  MAX(`Program Name`) AS program_name,  CAST(NULL AS STRING) AS mail_instance_id,  CAST(NULL AS STRING) AS writer_flag,  CAST(NULL AS STRING) AS freq_bucketFROM xsight_db_dbrx.xsight_rpt_zn.dz_savings_cardGROUP BY 1, 2, 3, 4;

# COMMAND ----------

# MAGIC %md
# MAGIC Not in the 9 assigned tables — commented out for now:

# COMMAND ----------

-- Email (dz_oce_consolidated) is NOT one of the 9 assigned tables.-- Keeping this commented out until we confirm with Shuchita whether it's in scope.-- Uncomment this view + its line in the UNION ALL (Section 3) to include it.-- CREATE OR REPLACE TEMP VIEW v_email_activity AS-- SELECT--   CAST(`Prf Profile Id` AS STRING) AS hcp_id,--   'Email' AS channel,--   'Personal' AS channel_group,--   DATE_TRUNC('month', CAST(`Event Date` AS DATE)) AS activity_month,--   COUNT(*) AS touch_count,--   COUNT(DISTINCT CAST(`Event Date` AS DATE)) AS distinct_days,--   CAST(NULL AS STRING) AS call_type, CAST(NULL AS STRING) AS call_category,--   CAST(NULL AS STRING) AS hcp_present, CAST(NULL AS STRING) AS interaction_type,--   CAST(NULL AS STRING) AS product_name, CAST(NULL AS STRING) AS meal_flag,--   CAST(NULL AS DECIMAL(38,0)) AS call_length, CAST(NULL AS STRING) AS disposition,--   CAST(NULL AS STRING) AS mail_sent, CAST(NULL AS DECIMAL(38,0)) AS sample_qty,--   CAST(NULL AS STRING) AS order_status, CAST(NULL AS STRING) AS message_type,--   CAST(NULL AS DECIMAL(38,0)) AS pod_count, CAST(NULL AS DECIMAL(38,2)) AS savings_amount,--   CAST(NULL AS DECIMAL(38,0)) AS approved_claims, CAST(NULL AS DECIMAL(38,0)) AS submitted_claims,--   CAST(NULL AS DECIMAL(38,0)) AS reversed_claims, CAST(NULL AS DECIMAL(38,0)) AS days_supply,--   CAST(NULL AS DECIMAL(38,0)) AS patient_age, CAST(NULL AS STRING) AS patient_gender,--   CAST(NULL AS STRING) AS program_name,--   MAX(`Mail Instance Id`) AS mail_instance_id, MAX(`Writer Flag`) AS writer_flag, MAX(`Freq Bucket`) AS freq_bucket-- FROM xsight_db_dbrx.xsight_rpt_zn.dz_oce_consolidated-- WHERE `Engagement Type` = 'Email'-- GROUP BY 1, 2, 3, 4;

# COMMAND ----------

-- Speaker Program is also NOT one of the 9 assigned tables.-- Only 34% of attendees are linkable (ATTENDEE_TAKEDA_ID -> CUST_ID -> PROFILE_ID).-- Uncomment this view + its line in the UNION ALL (Section 3) to include it.-- CREATE OR REPLACE TEMP VIEW v_speaker_activity AS-- SELECT--   p.PROFILE_ID AS hcp_id,--   'Speaker_Program' AS channel,--   'Non-Personal' AS channel_group,--   DATE_TRUNC('month', CAST(sp.PROGRAM_DATE AS DATE)) AS activity_month,--   COUNT(*) AS touch_count,--   COUNT(DISTINCT CAST(sp.PROGRAM_DATE AS DATE)) AS distinct_days,--   CAST(NULL AS STRING) AS call_type, CAST(NULL AS STRING) AS call_category,--   CAST(NULL AS STRING) AS hcp_present, CAST(NULL AS STRING) AS interaction_type,--   CAST(NULL AS STRING) AS product_name, CAST(NULL AS STRING) AS meal_flag,--   CAST(NULL AS DECIMAL(38,0)) AS call_length, CAST(NULL AS STRING) AS disposition,--   CAST(NULL AS STRING) AS mail_sent, CAST(NULL AS DECIMAL(38,0)) AS sample_qty,--   CAST(NULL AS STRING) AS order_status, CAST(NULL AS STRING) AS message_type,--   CAST(NULL AS DECIMAL(38,0)) AS pod_count, CAST(NULL AS DECIMAL(38,2)) AS savings_amount,--   CAST(NULL AS DECIMAL(38,0)) AS approved_claims, CAST(NULL AS DECIMAL(38,0)) AS submitted_claims,--   CAST(NULL AS DECIMAL(38,0)) AS reversed_claims, CAST(NULL AS DECIMAL(38,0)) AS days_supply,--   CAST(NULL AS DECIMAL(38,0)) AS patient_age, CAST(NULL AS STRING) AS patient_gender,--   CAST(NULL AS STRING) AS program_name, CAST(NULL AS STRING) AS mail_instance_id,--   CAST(NULL AS STRING) AS writer_flag, CAST(NULL AS STRING) AS freq_bucket-- FROM xsight_db_dbrx.xsight_rpt_zn.rpt_speaker_program sp-- JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_cust_profile p ON sp.ATTENDEE_TAKEDA_ID = p.CUST_ID-- WHERE sp.ATTENDEE_TAKEDA_ID IS NOT NULL AND sp.PROGRAM_DATE IS NOT NULL AND p.PROFILE_ID IS NOT NULL-- GROUP BY 1, 2, 3, 4;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 3: Union All Active Channels

# COMMAND ----------

-- Combine all active channels into one view (positionally — column order must match)CREATE OR REPLACE TEMP VIEW v_all_activity ASSELECT * FROM v_isa_activityUNION ALL SELECT * FROM v_tele_activityUNION ALL SELECT * FROM v_sample_activityUNION ALL SELECT * FROM v_pod_activityUNION ALL SELECT * FROM v_savings_card_activity-- UNION ALL SELECT * FROM v_email_activity      -- uncomment if Email is added-- UNION ALL SELECT * FROM v_speaker_activity    -- uncomment if Speaker Program is added;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 4: Gold Table 1 — `gold_hcp_channel_month_team_3`

# COMMAND ----------

-- Join activity to the HCP dimension chain and land as the Gold tableCREATE OR REPLACE TABLE dz_demo_ws.gold.gold_hcp_channel_month_team_3 ASSELECT  a.*,  YEAR(a.activity_month) AS activity_year,  MONTH(a.activity_month) AS activity_month_num,  p.TARGET_FLAG AS target_flag,  p.SPECIALTY AS specialty,  p.DECILE AS decile,  t.TERRITORY AS territory,  s.TERRITORY_DESC AS territory_name,  s.DISTRICT_DESC AS district,  s.REGION_DESC AS regionFROM v_all_activity aLEFT JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_cust_profile p ON a.hcp_id = p.PROFILE_IDLEFT JOIN v_territory_deduped t ON p.CUST_ID = t.CUST_ID AND t.rn = 1LEFT JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_sales_org s ON t.TERRITORY = s.TERRITORY_CD;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Check Gold Table 1

# COMMAND ----------

display(spark.sql(f"""  SELECT channel, COUNT(*) AS rows, COUNT(DISTINCT hcp_id) AS distinct_hcps,         MIN(activity_month) AS min_month, MAX(activity_month) AS max_month  FROM {target_catalog_schema}.{TABLE_1}  GROUP BY channel  ORDER BY rows DESC"""))

# COMMAND ----------

# every row should have matched the dimension chain via PROFILE_IDdisplay(spark.sql(f"""  SELECT COUNT(*) AS total_rows, SUM(CASE WHEN target_flag IS NULL THEN 1 ELSE 0 END) AS rows_missing_dim_match  FROM {target_catalog_schema}.{TABLE_1}"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 5: Gold Table 2 — `gold_hcp_omnichannel_summary_team_3`

# COMMAND ----------

-- Roll Gold Table 1 up to one row per HCPCREATE OR REPLACE TEMP VIEW v_hcp_base ASSELECT  hcp_id,  COUNT(*) AS total_rows,  SUM(touch_count) AS total_touches,  COUNT(DISTINCT channel) AS channel_reach,  COUNT(DISTINCT activity_month) AS active_months,  MAX(activity_month) AS last_activity_month,  SUM(CASE WHEN channel_group = 'Personal' THEN touch_count ELSE 0 END) AS personal_touches,  SUM(CASE WHEN channel_group = 'Non-Personal' THEN touch_count ELSE 0 END) AS non_personal_touches,  MAX(CASE WHEN channel = 'ISA_Call' THEN 1 ELSE 0 END) AS has_isa_call,  MAX(CASE WHEN channel = 'Tele_Call' THEN 1 ELSE 0 END) AS has_tele_call,  MAX(CASE WHEN channel = 'Sample' THEN 1 ELSE 0 END) AS has_sample,  MAX(CASE WHEN channel = 'POD_Print' THEN 1 ELSE 0 END) AS has_pod,  MAX(CASE WHEN channel = 'Savings_Card' THEN 1 ELSE 0 END) AS has_savings_card,  MAX(CASE WHEN channel = 'Email' THEN 1 ELSE 0 END) AS has_emailFROM dz_demo_ws.gold.gold_hcp_channel_month_team_3GROUP BY hcp_id;

# COMMAND ----------

-- Reference date is computed from the data itself, NOT hardcoded.-- This picks up the max activity_month across whatever channels are active above.CREATE OR REPLACE TEMP VIEW v_reference_date ASSELECT MAX(activity_month) AS ref_date FROM dz_demo_ws.gold.gold_hcp_channel_month_team_3;

# COMMAND ----------

# sanity check — this is the date everything else is measured againstdisplay(spark.sql("SELECT * FROM v_reference_date"))

# COMMAND ----------

-- Add tiers, engagement score, and gap flags, then land as the Gold tableCREATE OR REPLACE TABLE dz_demo_ws.gold.gold_hcp_omnichannel_summary_team_3 ASSELECT  b.*,  ROUND(b.personal_touches * 100.0 / NULLIF(b.total_touches, 0), 1) AS personal_mix_pct,  DATEDIFF(r.ref_date, b.last_activity_month) AS days_since_last_touch,  CASE    WHEN DATEDIFF(r.ref_date, b.last_activity_month) <= 90 THEN 'Active'    WHEN DATEDIFF(r.ref_date, b.last_activity_month) <= 180 THEN 'Cooling'    ELSE 'Dormant'  END AS recency_tier,  -- Frequency cutoffs (Low <8 / Medium 8-19 / High >=20) were validated against  -- touch-count percentiles on the currently-active channels. Re-check the  -- percentiles (Section 5 validation cell) if channels are added/removed.  CASE    WHEN b.total_touches >= 20 THEN 'High'    WHEN b.total_touches >= 8 THEN 'Medium'    ELSE 'Low'  END AS frequency_tier,  CASE    WHEN b.channel_reach >= 4 AND b.total_touches >= 20 THEN 'Over-Engaged'    WHEN b.channel_reach >= 2 AND b.total_touches >= 8 THEN 'Well-Engaged'    ELSE 'Under-Engaged'  END AS engagement_tier,  (b.channel_reach * 2) +  (CASE WHEN b.total_touches >= 20 THEN 3 WHEN b.total_touches >= 8 THEN 2 ELSE 1 END) +  (CASE WHEN DATEDIFF(r.ref_date, b.last_activity_month) <= 90 THEN 9        WHEN DATEDIFF(r.ref_date, b.last_activity_month) <= 180 THEN 6        ELSE 3 END) AS engagement_score,  CASE WHEN p.TARGET_FLAG = 'Y' AND b.has_isa_call = 0 THEN 1 ELSE 0 END AS gap_target_no_rep_call,  CASE WHEN b.has_email = 1 AND b.has_isa_call = 0 THEN 1 ELSE 0 END AS gap_email_no_rep_call,  CASE WHEN p.TARGET_FLAG = 'Y' AND b.has_email = 1 AND b.has_isa_call = 0 THEN 1 ELSE 0 END AS gap_target_email_no_rep,  p.TARGET_FLAG AS target_flag,  p.SPECIALTY AS specialty,  p.DECILE AS decile,  t.TERRITORY AS territory,  s.TERRITORY_DESC AS territory_name,  s.DISTRICT_DESC AS district,  s.REGION_DESC AS regionFROM v_hcp_base bCROSS JOIN v_reference_date rLEFT JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_cust_profile p ON b.hcp_id = p.PROFILE_IDLEFT JOIN v_territory_deduped t ON p.CUST_ID = t.CUST_ID AND t.rn = 1LEFT JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_sales_org s ON t.TERRITORY = s.TERRITORY_CD;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Check Gold Table 2

# COMMAND ----------

display(spark.sql(f"""  SELECT COUNT(*) AS total_hcps, ROUND(AVG(channel_reach), 2) AS avg_reach,         ROUND(AVG(total_touches), 1) AS avg_touches,         MIN(engagement_score) AS min_score, MAX(engagement_score) AS max_score  FROM {target_catalog_schema}.{TABLE_2}"""))

# COMMAND ----------

# re-check frequency-tier cutoffs whenever the active channel list changesdisplay(spark.sql(f"""  SELECT    PERCENTILE(total_touches, 0.25) AS p25,    PERCENTILE(total_touches, 0.50) AS p50_median,    PERCENTILE(total_touches, 0.75) AS p75,    MAX(total_touches) AS max_touches  FROM {target_catalog_schema}.{TABLE_2}"""))

# COMMAND ----------

display(spark.sql(f"""  SELECT recency_tier, frequency_tier, engagement_tier, COUNT(*) AS hcp_count  FROM {target_catalog_schema}.{TABLE_2}  GROUP BY recency_tier, frequency_tier, engagement_tier  ORDER BY hcp_count DESC"""))

# COMMAND ----------

# channel-gap headline numbersdisplay(spark.sql(f"""  SELECT    SUM(gap_target_no_rep_call) AS target_hcps_no_rep_call,    SUM(gap_email_no_rep_call) AS hcps_email_no_rep_call,    SUM(gap_target_email_no_rep) AS target_hcps_email_only,    SUM(CASE WHEN target_flag = 'Y' THEN 1 ELSE 0 END) AS total_target_hcps  FROM {target_catalog_schema}.{TABLE_2}"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 6: Gold Table 3 — `gold_activity_rx_impact_team_3`Uses `rpt_sha_weekly` (Rx data) — not one of the 9 assigned tables. Confirm it's accessiblebefore running this section. **Read this table as association, not causation.**

# COMMAND ----------

-- rpt_sha_weekly is NOT one of the 9 assigned tables — confirm access before running this section.-- Weekly Rx rolled up per HCPCREATE OR REPLACE TEMP VIEW v_hcp_rx ASSELECT  CUST_ID,  SUM(TRX_COUNT) AS total_trx,  SUM(NRX_COUNT) AS total_nrx,  AVG(TRX_COUNT) AS avg_weekly_trx,  COUNT(DISTINCT WEEKEND_DATE) AS weeks_with_rxFROM xsight_db_dbrx.xsight_rpt_zn.rpt_sha_weeklyGROUP BY CUST_ID;-- First rep call date per HCP (pre/post anchor — assumption: FIRST call, not most recent)CREATE OR REPLACE TEMP VIEW v_first_rep_call ASSELECT CAST(`Prf Profile Id` AS STRING) AS hcp_id, MIN(`Actual Date`) AS first_call_dateFROM xsight_db_dbrx.xsight_rpt_zn.dz_isaGROUP BY 1;-- TRx in the 12 weeks before vs. after that first callCREATE OR REPLACE TEMP VIEW v_pre_post ASSELECT  f.hcp_id,  SUM(CASE WHEN CAST(r.WEEKEND_DATE AS DATE) BETWEEN DATE_SUB(f.first_call_date, 84) AND DATE_SUB(f.first_call_date, 1)      THEN r.TRX_COUNT ELSE 0 END) AS trx_pre_12wk,  SUM(CASE WHEN CAST(r.WEEKEND_DATE AS DATE) BETWEEN f.first_call_date AND DATE_ADD(f.first_call_date, 84)      THEN r.TRX_COUNT ELSE 0 END) AS trx_post_12wkFROM v_first_rep_call fJOIN xsight_db_dbrx.xsight_rpt_zn.rpt_cust_profile p ON f.hcp_id = p.PROFILE_IDJOIN xsight_db_dbrx.xsight_rpt_zn.rpt_sha_weekly r ON p.CUST_ID = r.CUST_IDGROUP BY f.hcp_id;

# COMMAND ----------

-- Read this table as ASSOCIATION, not causation — reps tend to target high-prescribers already.CREATE OR REPLACE TABLE dz_demo_ws.gold.gold_activity_rx_impact_team_3 ASSELECT  COALESCE(h.hcp_id, p.PROFILE_ID) AS hcp_id,  h.total_touches,  h.channel_reach,  h.engagement_tier,  h.has_isa_call,  h.has_email,  CASE    WHEN h.total_touches >= 20 THEN 'High-Touch'    WHEN h.total_touches >= 8 THEN 'Medium-Touch'    WHEN h.total_touches >= 1 THEN 'Low-Touch'    ELSE 'No-Touch'  END AS touch_level,  r.total_trx,  r.total_nrx,  ROUND(r.avg_weekly_trx, 3) AS avg_weekly_trx,  r.weeks_with_rx,  pp.trx_pre_12wk,  pp.trx_post_12wk,  CASE WHEN pp.trx_pre_12wk > 0    THEN ROUND((pp.trx_post_12wk - pp.trx_pre_12wk) * 100.0 / pp.trx_pre_12wk, 1)    ELSE NULL END AS trx_pct_change_post_call,  h.target_flag,  h.specialty,  h.decileFROM v_hcp_rx rJOIN xsight_db_dbrx.xsight_rpt_zn.rpt_cust_profile p ON r.CUST_ID = p.CUST_IDLEFT JOIN dz_demo_ws.gold.gold_hcp_omnichannel_summary_team_3 h ON p.PROFILE_ID = h.hcp_idLEFT JOIN v_pre_post pp ON p.PROFILE_ID = pp.hcp_idWHERE p.PROFILE_ID IS NOT NULL;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Check Gold Table 3

# COMMAND ----------

display(spark.sql(f"""  SELECT touch_level, COUNT(*) AS hcp_count, ROUND(AVG(total_trx), 1) AS avg_total_trx  FROM {target_catalog_schema}.{TABLE_3}  GROUP BY touch_level"""))

# COMMAND ----------

display(spark.sql(f"""  SELECT COUNT(*) AS hcps_with_rep_call_and_rx,         ROUND(AVG(trx_pre_12wk), 1) AS avg_trx_pre_12wk,         ROUND(AVG(trx_post_12wk), 1) AS avg_trx_post_12wk  FROM {target_catalog_schema}.{TABLE_3}  WHERE trx_pre_12wk IS NOT NULL"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 7: Gold Tables 4 & 5 — Website Aggregates`dz_website_page` has no HCP identity (`Profile Id` is 100% NULL), so it's kept as its ownaggregate-only tables rather than forced into the HCP-grain tables above.

# COMMAND ----------

-- Website has no HCP identity (Profile Id is 100% NULL) — aggregate-only, kept separateCREATE OR REPLACE TABLE dz_demo_ws.gold.gold_website_monthly_team_3 ASSELECT  DATE_TRUNC('month', CAST(`Cal Date` AS DATE)) AS activity_month,  YEAR(CAST(`Cal Date` AS DATE)) AS activity_year,  MONTH(CAST(`Cal Date` AS DATE)) AS activity_month_num,  `Audience Type` AS audience_type,  `Medium` AS medium,  `Device Info` AS device,  `Website Name` AS website_name,  COUNT(*) AS pageviews,  COUNT(DISTINCT `Visit Key`) AS sessions,  SUM(`Bounce Count`) AS bounces,  SUM(`New User Count`) AS new_users,  SUM(`Visit Count`) AS visits,  ROUND(AVG(`Session Duration`), 1) AS avg_session_duration,  ROUND(AVG(`Time On Page`), 1) AS avg_time_on_page,  ROUND(AVG(`Visit Score`), 2) AS avg_visit_score,  ROUND(SUM(`Bounce Count`) * 100.0 / NULLIF(COUNT(DISTINCT `Visit Key`), 0), 1) AS bounce_rate_pctFROM xsight_db_dbrx.xsight_rpt_zn.dz_website_pageWHERE `Cal Date` IS NOT NULLGROUP BY 1, 2, 3, 4, 5, 6, 7;

# COMMAND ----------

-- Same no-HCP-link caveat as Gold Table 4 — page-level traffic onlyCREATE OR REPLACE TABLE dz_demo_ws.gold.gold_website_top_pages_team_3 ASSELECT  DATE_TRUNC('month', CAST(`Cal Date` AS DATE)) AS activity_month,  `Page Name` AS page_name,  `Page Url` AS page_url,  `Audience Type` AS audience_type,  COUNT(*) AS pageviews,  COUNT(DISTINCT `Visit Key`) AS sessions,  ROUND(AVG(`Time On Page`), 1) AS avg_time_on_page,  SUM(`Bounce Count`) AS bouncesFROM xsight_db_dbrx.xsight_rpt_zn.dz_website_pageWHERE `Cal Date` IS NOT NULL AND `Page Name` IS NOT NULLGROUP BY 1, 2, 3, 4;

# COMMAND ----------

# MAGIC %md
# MAGIC ### Check Gold Tables 4 & 5

# COMMAND ----------

display(spark.sql(f"""  SELECT audience_type, SUM(pageviews) AS total_pageviews, SUM(sessions) AS total_sessions  FROM {target_catalog_schema}.{TABLE_4}  GROUP BY audience_type  ORDER BY total_pageviews DESC"""))

# COMMAND ----------

display(spark.sql(f"""  SELECT page_name, SUM(pageviews) AS total_pageviews  FROM {target_catalog_schema}.{TABLE_5}  GROUP BY page_name  ORDER BY total_pageviews DESC  LIMIT 20"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 8: Final Table Inventory

# COMMAND ----------

display(spark.sql(f"SHOW TABLES IN {target_catalog_schema} LIKE '*team_3*'"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Section 9: Genie Agent Instructions (reference — paste into Genie Space setup)```BUSINESS CONTEXT:This agent answers questions about HCP omnichannel marketing engagement.TABLES (all suffixed _team_3, in dz_demo_ws.gold):- gold_hcp_channel_month_team_3        (HCP x Channel x Month — granular)- gold_hcp_omnichannel_summary_team_3  (one row per HCP — reach/frequency/recency/tiers/gaps)- gold_activity_rx_impact_team_3       (one row per HCP with Rx — touch level vs TRx/NRx)- gold_website_monthly_team_3          (aggregate website traffic — no HCP link)- gold_website_top_pages_team_3        (aggregate top pages — no HCP link)CHANNELS CURRENTLY ACTIVE: ISA_Call, Tele_Call, Sample, POD_Print, Savings_CardEmail and Speaker Program are NOT included yet (not part of the 9 assigned tables).KEY METRICS:- Reach = COUNT(DISTINCT channel) per HCP- Frequency = SUM(touch_count) per HCP- Recency = days since last activity, measured against the max date in the data (not today)- Engagement Score = (reach x 2) + freq_tier(1/2/3) + recency_bonus(3/6/9)TIERS:- Recency: Active (<=90 days), Cooling (91-180), Dormant (>180)- Frequency: Low (<8 touches), Medium (8-19), High (>=20) — re-validate if channels change- Engagement: Under-Engaged (reach<2 AND touches<8), Well-Engaged (reach>=2 AND touches>=8), Over-Engaged (reach>=4 AND touches>=20)CAVEATS:- Activity-to-Rx impact is ASSOCIATION only, NOT causation. Always state this.- Pre/post analysis anchored to FIRST rep call date.- Website data is aggregate only — cannot answer HCP-level web questions.- POD stops Feb 2022, Tele stops Jan 2022.COMMON QUESTIONS -> TABLE MAPPING:- "Which target HCPs got no rep call?" -> gold_hcp_omnichannel_summary_team_3 WHERE gap_target_no_rep_call = 1- "Channel mix by specialty?" -> gold_hcp_channel_month_team_3 GROUP BY specialty, channel- "Do more-engaged HCPs write more?" -> gold_activity_rx_impact_team_3 GROUP BY touch_level- "Engagement tier breakdown?" -> gold_hcp_omnichannel_summary_team_3 GROUP BY engagement_tier- "Website traffic / top pages?" -> gold_website_monthly_team_3 / gold_website_top_pages_team_3```