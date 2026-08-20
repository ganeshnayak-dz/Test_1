---
name: marketing-eda-notebook
description: Generate a comprehensive EDA notebook for the 9 marketing tables in xsight_db_dbrx.xsight_rpt_zn — covers data profiling, fill rates, overlaps, joinability, and data quality checks.
metadata:
  compatible-agents: genie
---

# Marketing Omnichannel EDA Notebook Generator

## Purpose

Generate a **complete .ipynb notebook** (Databricks-compatible) that performs Exploratory Data Analysis on the 9 marketing tables. The notebook should be ready to upload and run in Databricks without modification.

## Output Format

Generate a **Jupyter notebook (.ipynb)** with:
- **Markdown cells** for section headers and explanations
- **Code cells** using `spark.sql()` for all queries (Databricks PySpark)
- Each code cell should `display()` the result
- Add comments explaining WHAT each query checks and WHY

## Target Schema

**Catalog:** `xsight_db_dbrx`  
**Schema:** `xsight_rpt_zn`

Column names with spaces need backticks:
```python
spark.sql("SELECT `Prf Profile Id`, `Actual Date` FROM xsight_db_dbrx.xsight_rpt_zn.dz_isa")
```

## The 9 Assigned Tables + 1 Extra (Email from OCE)

### FACT TABLES

| # | Table | Channel | Group | HCP ID | Date Column | Rows | HCPs |
|---|-------|---------|-------|--------|-------------|------|------|
| 1 | dz_isa | Rep Calls | Personal | `Prf Profile Id` | `Actual Date` | 64K | 6,844 |
| 2 | dz_tele_detail | Tele Calls | Personal | `Prf Profile Id` | `Activity Cal Date` | 162K | 14,945 |
| 3 | dz_sample_activity | Samples | Personal | `Prf Profile Id` | `Sample Date` | 36K | 10,367 |
| 4 | dz_pod | Print-on-Demand | Personal | `Prf Profile Id` | `Actual Date` | 2.5K | 1,301 |
| 5 | dz_savings_card | Savings Card | Non-Personal | `Prf Profile Id` | `Org Submitted Cal Date` | 84K | 8,477 |
| 6 | dz_website_page | Website | Non-Personal | `Profile Id` (**100% NULL**) | `Cal Date` | 3.8M | 0 |
| 7 | dz_oce_consolidated (Email rows) | Email | Personal | `Prf Profile Id` | `Event Date` | 500K | 48,134 |

### DIMENSION TABLES

| # | Table | Key Columns |
|---|-------|-------------|
| 8 | rpt_cust_profile | CUST_ID, **PROFILE_ID** (join key!), DECILE, SPECIALTY, TARGET_FLAG |
| 9 | rpt_cust_territory | CUST_ID, TERRITORY, effective_start_date (dedup on latest) |
| 10 | rpt_sales_org | TERRITORY_CD, TERRITORY_DESC, DISTRICT_DESC, REGION_DESC |

### OPTIONAL (commented out — uncomment to include)

| Table | Channel | Notes |
|-------|---------|-------|
| rpt_speaker_program | Speaker Program (Non-Personal) | Only 34% of attendees linkable via 3-hop join. ATTENDEE_TAKEDA_ID → CUST_ID → PROFILE_ID |

## JOIN MAP

```
Fact tables.`Prf Profile Id` (DECIMAL)
    │  CAST AS STRING = PROFILE_ID
    ▼
rpt_cust_profile (PROFILE_ID → CUST_ID, SPECIALTY, DECILE, TARGET_FLAG)
    │  CUST_ID = CUST_ID (dedup: latest effective_start_date)
    ▼
rpt_cust_territory (TERRITORY)
    │  TERRITORY = TERRITORY_CD
    ▼
rpt_sales_org (TERRITORY_DESC, DISTRICT_DESC, REGION_DESC)
```

All 6 HCP-linked fact tables join at **100%** to rpt_cust_profile.

## KEY NUMBERS (7 channels: 5 original + Email + Savings Card)

- Total unique HCPs: **57,788**
- Target HCPs with activity: **34,282** (59%)
- Target HCPs with zero touch: **2,874** (7.7%)
- Avg reach: **1.57 channels**
- Median touches: **9** | P75: **20**
- Reference date (max in data): **2023-05-19**
- Engagement score range: **6–26**

## DESIGN DECISIONS

| Decision | Choice |
|----------|--------|
| Reference date | `2023-05-19` (max activity date in data, NOT CURRENT_DATE) |
| Frequency cutoffs | Low (<8) = bottom 50%, Medium (8-19) = P50-P75, High (≥20) = top 25% |
| Engagement score | (reach×2) + freq_numeric(1/2/3) + recency_numeric(3/6/9) |
| Gap flags | Static in Gold Table 2 + Genie uses Table 1 for rolling-window queries |
| Pre/post anchor | First rep call date (stated assumption) |
| Causation caveat | Must be in Genie instructions |
| Speaker Program | Commented out — uncomment to include (34% coverage) |

---

## GOLD TABLE SQL CODE

### Gold Table 1: `gold_hcp_channel_month`

**Grain:** HCP × Channel × Month  
**Purpose:** Unified omnichannel fact with channel-specific nullable columns

```sql
CREATE OR REPLACE TABLE <target_schema>.gold_hcp_channel_month AS

WITH territory_deduped AS (
  SELECT CUST_ID, TERRITORY,
    ROW_NUMBER() OVER (PARTITION BY CUST_ID ORDER BY effective_start_date DESC) AS rn
  FROM xsight_db_dbrx.xsight_rpt_zn.rpt_cust_territory
),

-- ============================================================
-- CHANNEL 1: ISA_Call (Rep Visits)
-- ============================================================
isa_activity AS (
  SELECT
    CAST(`Prf Profile Id` AS STRING) AS hcp_id,
    'ISA_Call' AS channel,
    'Personal' AS channel_group,
    DATE_TRUNC('month', `Actual Date`) AS activity_month,
    COUNT(*) AS touch_count,
    COUNT(DISTINCT `Actual Date`) AS distinct_days,
    -- Channel-specific columns
    MAX(`Call Type`) AS call_type,
    MAX(`Call Category`) AS call_category,
    MAX(`Hcp Present`) AS hcp_present,
    MAX(`Interaction Type`) AS interaction_type,
    MAX(`Col 1`) AS product_name,
    MAX(`Meal`) AS meal_flag,
    -- Not applicable for this channel
    CAST(NULL AS DECIMAL(38,0)) AS call_length,
    CAST(NULL AS STRING) AS disposition,
    CAST(NULL AS STRING) AS mail_sent,
    CAST(NULL AS DECIMAL(38,0)) AS sample_qty,
    CAST(NULL AS STRING) AS order_status,
    CAST(NULL AS STRING) AS message_type,
    CAST(NULL AS DECIMAL(38,0)) AS pod_count,
    CAST(NULL AS DECIMAL(38,0)) AS savings_amount,
    CAST(NULL AS DECIMAL(38,0)) AS approved_claims,
    CAST(NULL AS DECIMAL(38,0)) AS submitted_claims,
    CAST(NULL AS DECIMAL(38,0)) AS reversed_claims,
    CAST(NULL AS DECIMAL(38,0)) AS days_supply,
    CAST(NULL AS DECIMAL(38,0)) AS patient_age,
    CAST(NULL AS STRING) AS patient_gender,
    CAST(NULL AS STRING) AS program_name,
    CAST(NULL AS DECIMAL(38,0)) AS mail_instance_id,
    CAST(NULL AS STRING) AS writer_flag,
    CAST(NULL AS STRING) AS freq_bucket
  FROM xsight_db_dbrx.xsight_rpt_zn.dz_isa
  GROUP BY 1, 2, 3, 4
),

-- ============================================================
-- CHANNEL 2: Tele_Call (Telemarketing)
-- ============================================================
tele_activity AS (
  SELECT
    CAST(`Prf Profile Id` AS STRING) AS hcp_id,
    'Tele_Call' AS channel,
    'Personal' AS channel_group,
    DATE_TRUNC('month', `Activity Cal Date`) AS activity_month,
    COUNT(*) AS touch_count,
    COUNT(DISTINCT `Activity Cal Date`) AS distinct_days,
    -- Not applicable
    CAST(NULL AS STRING) AS call_type,
    CAST(NULL AS STRING) AS call_category,
    CAST(NULL AS STRING) AS hcp_present,
    CAST(NULL AS STRING) AS interaction_type,
    CAST(NULL AS STRING) AS product_name,
    CAST(NULL AS STRING) AS meal_flag,
    -- Channel-specific
    CAST(AVG(`Call Length`) AS DECIMAL(38,0)) AS call_length,
    MAX(`Disposition Desc`) AS disposition,
    MAX(`Mail Sent`) AS mail_sent,
    -- Not applicable
    CAST(NULL AS DECIMAL(38,0)) AS sample_qty,
    CAST(NULL AS STRING) AS order_status,
    CAST(NULL AS STRING) AS message_type,
    CAST(NULL AS DECIMAL(38,0)) AS pod_count,
    CAST(NULL AS DECIMAL(38,0)) AS savings_amount,
    CAST(NULL AS DECIMAL(38,0)) AS approved_claims,
    CAST(NULL AS DECIMAL(38,0)) AS submitted_claims,
    CAST(NULL AS DECIMAL(38,0)) AS reversed_claims,
    CAST(NULL AS DECIMAL(38,0)) AS days_supply,
    CAST(NULL AS DECIMAL(38,0)) AS patient_age,
    CAST(NULL AS STRING) AS patient_gender,
    CAST(NULL AS STRING) AS program_name,
    CAST(NULL AS DECIMAL(38,0)) AS mail_instance_id,
    CAST(NULL AS STRING) AS writer_flag,
    CAST(NULL AS STRING) AS freq_bucket
  FROM xsight_db_dbrx.xsight_rpt_zn.dz_tele_detail
  GROUP BY 1, 2, 3, 4
),

-- ============================================================
-- CHANNEL 3: Sample (Drug Samples)
-- ============================================================
sample_activity AS (
  SELECT
    CAST(`Prf Profile Id` AS STRING) AS hcp_id,
    'Sample' AS channel,
    'Personal' AS channel_group,
    DATE_TRUNC('month', `Sample Date`) AS activity_month,
    COUNT(*) AS touch_count,
    COUNT(DISTINCT `Sample Date`) AS distinct_days,
    CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING),
    -- Channel-specific
    SUM(`Quantity`) AS sample_qty,
    MAX(`Order Status`) AS order_status,
    -- Not applicable
    CAST(NULL AS STRING), CAST(NULL AS DECIMAL(38,0)),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING)
  FROM xsight_db_dbrx.xsight_rpt_zn.dz_sample_activity
  GROUP BY 1, 2, 3, 4
),

-- ============================================================
-- CHANNEL 4: POD_Print (Print-on-Demand)
-- ============================================================
pod_activity AS (
  SELECT
    CAST(`Prf Profile Id` AS STRING) AS hcp_id,
    'POD_Print' AS channel,
    'Personal' AS channel_group,
    DATE_TRUNC('month', `Actual Date`) AS activity_month,
    COUNT(*) AS touch_count,
    COUNT(DISTINCT `Actual Date`) AS distinct_days,
    CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING),
    -- Channel-specific
    MAX(`Message Type`) AS message_type,
    SUM(`Pod Utilization Count`) AS pod_count,
    -- Not applicable
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING)
  FROM xsight_db_dbrx.xsight_rpt_zn.dz_pod
  GROUP BY 1, 2, 3, 4
),

-- ============================================================
-- CHANNEL 5: Savings_Card (Copay Assistance)
-- ============================================================
savings_card_activity AS (
  SELECT
    CAST(`Prf Profile Id` AS STRING) AS hcp_id,
    'Savings_Card' AS channel,
    'Non-Personal' AS channel_group,
    DATE_TRUNC('month', `Org Submitted Cal Date`) AS activity_month,
    COUNT(*) AS touch_count,
    COUNT(DISTINCT `Org Submitted Cal Date`) AS distinct_days,
    CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS DECIMAL(38,0)),
    -- Channel-specific
    SUM(`Savings Amount`) AS savings_amount,
    SUM(`Approved Claims`) AS approved_claims,
    SUM(`Submitted Claims`) AS submitted_claims,
    SUM(`Reversed Claims`) AS reversed_claims,
    CAST(AVG(`Days Supply`) AS DECIMAL(38,0)) AS days_supply,
    CAST(AVG(`Patient Age`) AS DECIMAL(38,0)) AS patient_age,
    MAX(`Patient Gender`) AS patient_gender,
    MAX(`Program Name`) AS program_name,
    -- Not applicable
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING)
  FROM xsight_db_dbrx.xsight_rpt_zn.dz_savings_card
  GROUP BY 1, 2, 3, 4
),

-- ============================================================
-- CHANNEL 6: Email (from dz_oce_consolidated)
-- ============================================================
email_activity AS (
  SELECT
    CAST(`Prf Profile Id` AS STRING) AS hcp_id,
    'Email' AS channel,
    'Personal' AS channel_group,
    DATE_TRUNC('month', CAST(`Event Date` AS DATE)) AS activity_month,
    COUNT(*) AS touch_count,
    COUNT(DISTINCT CAST(`Event Date` AS DATE)) AS distinct_days,
    CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS DECIMAL(38,0)),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)),
    CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING),
    -- Channel-specific
    MAX(`Mail Instance Id`) AS mail_instance_id,
    MAX(`Writer Flag`) AS writer_flag,
    MAX(`Freq Bucket`) AS freq_bucket
  FROM xsight_db_dbrx.xsight_rpt_zn.dz_oce_consolidated
  WHERE `Engagement Type` = 'Email'
  GROUP BY 1, 2, 3, 4
),

-- ============================================================
-- OPTIONAL CHANNEL 7: Speaker_Program (uncomment to include)
-- ============================================================
-- speaker_activity AS (
--   SELECT
--     p.PROFILE_ID AS hcp_id,
--     'Speaker_Program' AS channel,
--     'Non-Personal' AS channel_group,
--     DATE_TRUNC('month', CAST(sp.PROGRAM_DATE AS DATE)) AS activity_month,
--     COUNT(*) AS touch_count,
--     COUNT(DISTINCT CAST(sp.PROGRAM_DATE AS DATE)) AS distinct_days,
--     CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS STRING),
--     CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING),
--     CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING), CAST(NULL AS DECIMAL(38,0)),
--     CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS DECIMAL(38,0)),
--     CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING),
--     CAST(NULL AS DECIMAL(38,0)), CAST(NULL AS STRING), CAST(NULL AS STRING)
--   FROM xsight_db_dbrx.xsight_rpt_zn.rpt_speaker_program sp
--   JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_cust_profile p ON sp.ATTENDEE_TAKEDA_ID = p.CUST_ID
--   WHERE sp.ATTENDEE_TAKEDA_ID IS NOT NULL AND sp.PROGRAM_DATE IS NOT NULL AND p.PROFILE_ID IS NOT NULL
--   GROUP BY 1, 2, 3, 4
-- ),

-- ============================================================
-- UNION ALL CHANNELS
-- ============================================================
all_activity AS (
  SELECT * FROM isa_activity
  UNION ALL SELECT * FROM tele_activity
  UNION ALL SELECT * FROM sample_activity
  UNION ALL SELECT * FROM pod_activity
  UNION ALL SELECT * FROM savings_card_activity
  UNION ALL SELECT * FROM email_activity
  -- UNION ALL SELECT * FROM speaker_activity  -- uncomment to include
)

-- ============================================================
-- FINAL SELECT: Join dimensions
-- ============================================================
SELECT
  a.*,
  YEAR(a.activity_month) AS activity_year,
  MONTH(a.activity_month) AS activity_month_num,
  p.TARGET_FLAG AS target_flag,
  p.SPECIALTY AS specialty,
  p.DECILE AS decile,
  t.TERRITORY AS territory,
  s.TERRITORY_DESC AS territory_name,
  s.DISTRICT_DESC AS district,
  s.REGION_DESC AS region
FROM all_activity a
LEFT JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_cust_profile p
  ON a.hcp_id = p.PROFILE_ID
LEFT JOIN territory_deduped t
  ON p.CUST_ID = t.CUST_ID AND t.rn = 1
LEFT JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_sales_org s
  ON t.TERRITORY = s.TERRITORY_CD;
```

---

### Gold Table 2: `gold_hcp_omnichannel_summary`

**Grain:** One row per HCP  
**Purpose:** Reach, frequency, recency, engagement tiers, gap flags

```sql
CREATE OR REPLACE TABLE <target_schema>.gold_hcp_omnichannel_summary AS

WITH base AS (
  SELECT
    hcp_id,
    COUNT(*) AS total_rows,
    SUM(touch_count) AS total_touches,
    COUNT(DISTINCT channel) AS channel_reach,
    COUNT(DISTINCT activity_month) AS active_months,
    MAX(activity_month) AS last_activity_month,
    SUM(CASE WHEN channel_group = 'Personal' THEN touch_count ELSE 0 END) AS personal_touches,
    SUM(CASE WHEN channel_group = 'Non-Personal' THEN touch_count ELSE 0 END) AS non_personal_touches,
    -- Channel presence flags
    MAX(CASE WHEN channel = 'ISA_Call' THEN 1 ELSE 0 END) AS has_isa_call,
    MAX(CASE WHEN channel = 'Tele_Call' THEN 1 ELSE 0 END) AS has_tele_call,
    MAX(CASE WHEN channel = 'Sample' THEN 1 ELSE 0 END) AS has_sample,
    MAX(CASE WHEN channel = 'POD_Print' THEN 1 ELSE 0 END) AS has_pod,
    MAX(CASE WHEN channel = 'Savings_Card' THEN 1 ELSE 0 END) AS has_savings_card,
    MAX(CASE WHEN channel = 'Email' THEN 1 ELSE 0 END) AS has_email,
    -- MAX(CASE WHEN channel = 'Speaker_Program' THEN 1 ELSE 0 END) AS has_speaker_program,  -- uncomment if included
    -- Last activity per channel
    MAX(CASE WHEN channel = 'ISA_Call' THEN activity_month END) AS last_isa_call_month,
    MAX(CASE WHEN channel = 'Email' THEN activity_month END) AS last_email_month
  FROM <target_schema>.gold_hcp_channel_month
  GROUP BY hcp_id
)

SELECT
  b.*,
  ROUND(b.personal_touches * 100.0 / NULLIF(b.total_touches, 0), 1) AS personal_mix_pct,
  
  -- Recency (reference date = 2023-05-19, max date in data)
  DATEDIFF('2023-05-19', b.last_activity_month) AS days_since_last_touch,
  CASE
    WHEN DATEDIFF('2023-05-19', b.last_activity_month) <= 90 THEN 'Active'
    WHEN DATEDIFF('2023-05-19', b.last_activity_month) <= 180 THEN 'Cooling'
    ELSE 'Dormant'
  END AS recency_tier,
  
  -- Frequency tier (data-driven: P50=9, P75=20)
  CASE
    WHEN b.total_touches >= 20 THEN 'High'
    WHEN b.total_touches >= 8 THEN 'Medium'
    ELSE 'Low'
  END AS frequency_tier,
  
  -- Engagement tier
  CASE
    WHEN b.channel_reach >= 4 AND b.total_touches >= 20 THEN 'Over-Engaged'
    WHEN b.channel_reach >= 2 AND b.total_touches >= 8 THEN 'Well-Engaged'
    ELSE 'Under-Engaged'
  END AS engagement_tier,
  
  -- Engagement score (range: 6–26)
  (b.channel_reach * 2) +
  (CASE WHEN b.total_touches >= 20 THEN 3 WHEN b.total_touches >= 8 THEN 2 ELSE 1 END) +
  (CASE WHEN DATEDIFF('2023-05-19', b.last_activity_month) <= 90 THEN 9
        WHEN DATEDIFF('2023-05-19', b.last_activity_month) <= 180 THEN 6
        ELSE 3 END) AS engagement_score,
  
  -- Channel gap flags
  CASE WHEN p.TARGET_FLAG = 'Y' AND b.has_isa_call = 0 THEN 1 ELSE 0 END AS gap_target_no_rep_call,
  CASE WHEN b.has_email = 1 AND b.has_isa_call = 0 THEN 1 ELSE 0 END AS gap_email_no_rep_call,
  CASE WHEN p.TARGET_FLAG = 'Y' AND b.has_email = 1 AND b.has_isa_call = 0 THEN 1 ELSE 0 END AS gap_target_email_no_rep,
  
  -- Dimensions
  p.TARGET_FLAG AS target_flag,
  p.SPECIALTY AS specialty,
  p.DECILE AS decile,
  t.TERRITORY AS territory,
  s.TERRITORY_DESC AS territory_name,
  s.DISTRICT_DESC AS district,
  s.REGION_DESC AS region

FROM base b
LEFT JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_cust_profile p ON b.hcp_id = p.PROFILE_ID
LEFT JOIN (
  SELECT CUST_ID, TERRITORY, ROW_NUMBER() OVER (PARTITION BY CUST_ID ORDER BY effective_start_date DESC) AS rn
  FROM xsight_db_dbrx.xsight_rpt_zn.rpt_cust_territory
) t ON p.CUST_ID = t.CUST_ID AND t.rn = 1
LEFT JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_sales_org s ON t.TERRITORY = s.TERRITORY_CD;
```

---

### Gold Table 3: `gold_activity_rx_impact`

**Grain:** One row per HCP who has Rx data  
**Purpose:** Compare Rx across engagement levels. READ AS ASSOCIATION, NOT CAUSATION.

**NOTE:** This uses `rpt_sha_weekly` which is NOT in the 9 assigned tables but exists in the same schema. The assignment says "join to SHA gold."

```sql
CREATE OR REPLACE TABLE <target_schema>.gold_activity_rx_impact AS

WITH hcp_touches AS (
  SELECT hcp_id, total_touches, channel_reach, has_isa_call, has_email,
    engagement_tier, recency_tier, target_flag, specialty, decile
  FROM <target_schema>.gold_hcp_omnichannel_summary
),

hcp_rx AS (
  SELECT
    CUST_ID,
    SUM(TRX_COUNT) AS total_trx,
    SUM(NRX_COUNT) AS total_nrx,
    AVG(TRX_COUNT) AS avg_weekly_trx,
    COUNT(DISTINCT WEEKEND_DATE) AS weeks_with_rx
  FROM xsight_db_dbrx.xsight_rpt_zn.rpt_sha_weekly
  GROUP BY CUST_ID
),

-- Pre/Post first rep call analysis
first_rep_call AS (
  SELECT CAST(`Prf Profile Id` AS STRING) AS hcp_id, MIN(`Actual Date`) AS first_call_date
  FROM xsight_db_dbrx.xsight_rpt_zn.dz_isa
  GROUP BY 1
),

pre_post AS (
  SELECT
    f.hcp_id,
    SUM(CASE WHEN CAST(r.WEEKEND_DATE AS DATE) BETWEEN DATE_SUB(f.first_call_date, 84) AND DATE_SUB(f.first_call_date, 1)
        THEN r.TRX_COUNT ELSE 0 END) AS trx_pre_12wk,
    SUM(CASE WHEN CAST(r.WEEKEND_DATE AS DATE) BETWEEN f.first_call_date AND DATE_ADD(f.first_call_date, 84)
        THEN r.TRX_COUNT ELSE 0 END) AS trx_post_12wk
  FROM first_rep_call f
  JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_cust_profile p ON f.hcp_id = p.PROFILE_ID
  JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_sha_weekly r ON p.CUST_ID = r.CUST_ID
  GROUP BY f.hcp_id
)

SELECT
  COALESCE(h.hcp_id, p.PROFILE_ID) AS hcp_id,
  h.total_touches,
  h.channel_reach,
  h.engagement_tier,
  h.has_isa_call,
  h.has_email,
  -- Touch level
  CASE
    WHEN h.total_touches >= 20 THEN 'High-Touch'
    WHEN h.total_touches >= 8 THEN 'Medium-Touch'
    WHEN h.total_touches >= 1 THEN 'Low-Touch'
    ELSE 'No-Touch'
  END AS touch_level,
  -- Rx metrics
  r.total_trx,
  r.total_nrx,
  ROUND(r.avg_weekly_trx, 3) AS avg_weekly_trx,
  r.weeks_with_rx,
  -- Pre/Post (NULL if no rep call)
  pp.trx_pre_12wk,
  pp.trx_post_12wk,
  CASE WHEN pp.trx_pre_12wk > 0 
    THEN ROUND((pp.trx_post_12wk - pp.trx_pre_12wk) * 100.0 / pp.trx_pre_12wk, 1)
    ELSE NULL END AS trx_pct_change_post_call,
  -- Dimensions
  h.target_flag,
  h.specialty,
  h.decile

FROM hcp_rx r
JOIN xsight_db_dbrx.xsight_rpt_zn.rpt_cust_profile p ON r.CUST_ID = p.CUST_ID
LEFT JOIN hcp_touches h ON p.PROFILE_ID = h.hcp_id
LEFT JOIN pre_post pp ON p.PROFILE_ID = pp.hcp_id
WHERE p.PROFILE_ID IS NOT NULL;
```

---

### Gold Table 4: `gold_website_monthly` (Aggregate — No HCP)

**Grain:** Month × Audience Type × Medium × Device  
**Purpose:** Website traffic metrics at aggregate level. Cannot link to HCPs (Profile Id is 100% NULL), so kept separate from HCP-level gold tables.

```sql
CREATE OR REPLACE TABLE <target_schema>.gold_website_monthly AS

SELECT
  DATE_TRUNC('month', CAST(`Cal Date` AS DATE)) AS activity_month,
  YEAR(CAST(`Cal Date` AS DATE)) AS activity_year,
  MONTH(CAST(`Cal Date` AS DATE)) AS activity_month_num,
  `Audience Type` AS audience_type,
  `Medium` AS medium,
  `Device Info` AS device,
  `Website Name` AS website_name,
  -- Measures
  COUNT(*) AS pageviews,
  COUNT(DISTINCT `Visit Key`) AS sessions,
  SUM(`Bounce Count`) AS bounces,
  SUM(`New User Count`) AS new_users,
  SUM(`Visit Count`) AS visits,
  ROUND(AVG(`Session Duration`), 1) AS avg_session_duration,
  ROUND(AVG(`Time On Page`), 1) AS avg_time_on_page,
  ROUND(AVG(`Visit Score`), 2) AS avg_visit_score,
  ROUND(SUM(`Bounce Count`) * 100.0 / NULLIF(COUNT(DISTINCT `Visit Key`), 0), 1) AS bounce_rate_pct
FROM xsight_db_dbrx.xsight_rpt_zn.dz_website_page
WHERE `Cal Date` IS NOT NULL
GROUP BY 1, 2, 3, 4, 5, 6, 7;
```

**Why separate:** `dz_website_page` has `Profile Id` = 100% NULL. No HCP can be identified. This table answers aggregate web questions only: "total traffic trend", "top mediums", "device breakdown", "bounce rate by audience type."

---

### Gold Table 5: `gold_website_top_pages` (Aggregate — Page-Level)

**Grain:** Month × Page  
**Purpose:** Which pages get the most traffic

```sql
CREATE OR REPLACE TABLE <target_schema>.gold_website_top_pages AS

SELECT
  DATE_TRUNC('month', CAST(`Cal Date` AS DATE)) AS activity_month,
  `Page Name` AS page_name,
  `Page Url` AS page_url,
  `Audience Type` AS audience_type,
  COUNT(*) AS pageviews,
  COUNT(DISTINCT `Visit Key`) AS sessions,
  ROUND(AVG(`Time On Page`), 1) AS avg_time_on_page,
  SUM(`Bounce Count`) AS bounces
FROM xsight_db_dbrx.xsight_rpt_zn.dz_website_page
WHERE `Cal Date` IS NOT NULL AND `Page Name` IS NOT NULL
GROUP BY 1, 2, 3, 4;
```

---

## GENIE AGENT INSTRUCTIONS (add these when setting up)

```
BUSINESS CONTEXT:
This agent answers questions about HCP omnichannel marketing engagement.

CHANNEL CLASSIFICATION:
- Personal: ISA_Call (rep visits), Tele_Call (phone), Sample (drug samples), POD_Print (printed materials), Email
- Non-Personal: Savings_Card (patient copay cards)
- Website: aggregate only (cannot link to HCPs)

KEY METRICS:
- Reach = COUNT(DISTINCT channel) per HCP
- Frequency = SUM(touch_count) per HCP
- Recency = days since last activity (reference: 2023-05-19)
- Engagement Score = (reach×2) + freq_tier(1/2/3) + recency_bonus(3/6/9). Range: 6–26.

TIERS:
- Recency: Active (≤90 days), Cooling (91-180), Dormant (>180)
- Frequency: Low (<8 touches), Medium (8-19), High (≥20)
- Engagement: Under-Engaged (reach<2 AND touches<8), Well-Engaged (reach≥2 AND touches≥8), Over-Engaged (reach≥4 AND touches≥20)

IMPORTANT CAVEATS:
- Activity-to-Rx impact shows ASSOCIATION only, NOT causation. Reps target high-prescribers, so correlation ≠ causation. Always state this.
- Pre/post analysis anchored to FIRST rep call date.
- Website data is anonymous — cannot answer HCP-level web questions.
- POD data stops Feb 2022, Tele stops Jan 2022.
- Reference date is 2023-05-19 (max in data), not today.

JOIN KEYS:
- gold tables join on hcp_id
- For territory hierarchy: use territory column → rpt_sales_org.TERRITORY_CD

COMMON QUESTIONS:
- "Which target HCPs got email but no rep call?" → gold_hcp_omnichannel_summary WHERE gap_target_email_no_rep = 1
- "Channel mix by specialty?" → gold_hcp_channel_month GROUP BY specialty, channel
- "Do more-engaged HCPs write more?" → gold_activity_rx_impact GROUP BY touch_level
- "Engagement tier breakdown?" → gold_hcp_omnichannel_summary GROUP BY engagement_tier
```

## When to Use This Skill

Load this skill when:
- Need to generate the EDA notebook or gold table creation code
- Setting up the Genie Agent with tables and instructions
- Need the full SQL for any of the 3 gold tables
- Want to add Speaker Program (uncomment the commented sections)