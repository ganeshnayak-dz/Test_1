---
name: attr-promotional-agent-blueprint
description: "Blueprint for building promotional Genie Agents modeled on the ATTR HCP-HCA 360 agent — covers architecture, instructions, SQL expressions, measures, metric formulas, join patterns, and best practices from both ATTR and IBD agents."
metadata:
  compatible-agents: genie
---

# ATTR Promotional Agent Blueprint

Use this skill when you need to **build, audit, or extend a promotional Genie Agent** for any therapeutic area. This skill documents the complete architecture of the ATTR HCP-HCA 360 Genie Agent and distills reusable patterns from both the ATTR and IBD Early Assets Engine agents.

---

## What Is ATTR?

**ATTR = Transthyretin Amyloidosis** — a rare disease where misfolded transthyretin protein deposits in organs (heart, nerves). The ATTR market has 5 products across 2 drug classes:

| Drug Class | Products | Mechanism |
|-----------|----------|-----------|
| **Silencers** | Wainua (AstraZeneca), Amvuttra, Onpattro | Silence/reduce TTR protein production |
| **Stabilizers** | Vyndamax, Attruby | Stabilize TTR protein to prevent misfolding |

**Indications:**
- hATTR-PN = hereditary ATTR polyneuropathy
- hATTR-Mixed = hereditary ATTR mixed phenotype
- hATTR-CM = hereditary ATTR cardiomyopathy (cardiac)
- Columns with "PNMIXEDHATTR" = hATTR-PN OR hATTR-Mixed (NOT hATTR-CM)
- Columns with "TOTAL" = all indications combined

---

## Agent Architecture Overview

The ATTR agent uses **5 tables** working together:

| Table | Purpose | Grain |
|-------|---------|-------|
| `data_prod_hcp_hca_360` | Main 360 table — monthly product volumes, patient metrics, geography, IDN, segmentation | HCP-month or HCA-month |
| `data_prod_promotions_360_genie` | Promotional engagement — calls, emails, digital, speaker programs | HCP-month |
| `mv_wainua_hcp_promotions_360` | Metric view over promotions (pre-aggregated measures) | HCP-month |
| `mv_wainua_hcp_hca_360` | Metric view over 360 table (pre-aggregated measures with MEASURE() syntax) | HCP-month or HCA-month |
| `d_hcp_specialty_dimension_stage1` | Dimension table — specialty, target flags, segmentation, IDN affiliation | HCP (one row per HCP) |

**Catalog:** `us_commercial_catalog_prod.lgu_eplontersen`

---

## Key Architectural Patterns (Reusable for Any Promotional Agent)

### Pattern 1: Source Type Separation (HCP vs HCA)

The 360 table has two source types:
- **HCP** (~556K rows) = individual health care providers (doctor-level)
- **HCA** (~4K rows) = health care accounts (facility-level)

**Rules:**
- HCP-specific analysis (doctor-level): filter `source_type = 'HCP'`
- IDN/account-level analysis: NO source_type filter (both roll up to the same IDN)
- HCA rows have NULL for specialty, segmentation, behavioral segment — this is expected
- Some data sources (DDD, SD) report at HCA level; others (SP, ELAAD, Komodo, CareSet) at HCP level

### Pattern 2: Data Maturity Filtering

```sql
-- ALWAYS apply by default
WHERE DATA_MATURITY_DATE_FLAG = 1
-- Only include immature months if user explicitly asks for "most recent" or "including incomplete months"
```

### Pattern 3: Date Anchoring (Never Use CURRENT_DATE)

```sql
-- Correct: anchor on MAX date in data
SELECT MAX(MONTH) AS end_date FROM data_prod_hcp_hca_360
-- Then: start_date = end_date - N months

-- WRONG: Never use CURRENT_DATE() or NOW()
```

### Pattern 4: Join Between Promotions and Product Data

```sql
-- Promotions → HCP dimension
CAST(p.hcp_az_cust_id AS STRING) = CAST(d.az_cust_id AS STRING)

-- Product 360 → HCP dimension
CAST(h.HCP_HCA_ID AS STRING) = CAST(d.az_cust_id AS STRING)

-- Promotions → Product 360
CAST(p.hcp_az_cust_id AS STRING) = CAST(h.HCP_HCA_ID AS STRING)
```

### Pattern 5: Quarterly Time Windows for Promotions

```sql
-- Q2 2026 = April, May, June
WHERE Month >= '2026-04-01' AND Month <= '2026-06-01'

-- Q3 2026 = July, August, September
WHERE Month >= '2026-07-01' AND Month <= '2026-09-01'
```

---

## Metric Definitions & Formulas

### Product Metrics (per product, per HCP/HCA, per month)

| Metric Suffix | Meaning | Formula |
|--------------|---------|---------|
| `NBRx` | New patients/prescriptions | MAX(Komodo, ELAAD, CareSet) |
| `NTS` | New Therapy Starts | MAX(Komodo, ELAAD) |
| `Switch` | Patients switching from another product | MAX(Komodo, ELAAD) |
| `Add-on` | Patients adding product to existing therapy | MAX(Komodo, ELAAD) |
| `Units` | Total demand units (best source) | MAX(ELAAD, Komodo, CareSet) |
| `DDD_Units` | IQVIA DDD Shipment Data | HCA-level only |
| `Restart Different` | Patients restarting on different product in same family | MAX(Komodo, ELAAD) |
| `SD_Units` | Specialty Distributor units | Wainua only |

### IDN Potential Formula (Critical for Account-Level Analysis)

```sql
-- Wainua IDN Potential (uses SP + Komodo + SD + CareSet combined)
GREATEST(
  COALESCE(SUM(WAINUA_DDD_UNITS), 0),
  COALESCE(SUM(WAINUA_TOTAL_UNITS), 0)
)

-- Amvuttra/Onpattro/Vyndamax/Attruby IDN Potential
GREATEST(
  COALESCE(SUM({PRODUCT}_DDD_UNITS), 0),
  COALESCE(SUM({PRODUCT}_TOTAL_UNITS), 0)
)

-- Class-level IDN Potential (Silencers)
Wainua_IDN_Potential + Amvuttra_IDN_Potential + Onpattro_IDN_Potential

-- Market-level IDN Potential
Silencer_IDN_Potential + Stabilizer_IDN_Potential
```

**IDN Ranking Exclusions (always apply):**
```sql
WHERE INFUSION_CENTRE_FLAG = 0
  AND IDN_NAME NOT ILIKE '%MULTIPLE DOCTORS%'
  AND IDN_NAME NOT ILIKE '%ZIP MAIL SERVICE%'
```

### Reach % Formula

```sql
-- Reach % = (Target HCPs touched by channel X in quarter) / (Total Target HCPs in quarter) × 100
ROUND(
  COUNT(DISTINCT CASE WHEN channel_metric > 0 THEN hcp_id END) * 100.0
  / NULLIF(COUNT(DISTINCT target_hcp_id), 0),
  2
) AS reach_pct
```

**Denominator:** All HCPs with `Current_Quarter_HCP_Target_Flag = 'Yes'` (or Previous for prior quarter)
**Numerator:** Target HCPs with at least one touch in the specified channel during the quarter

### Frequency Formula

```sql
-- Frequency = Total touches / Unique HCPs touched (for a channel in a quarter)
ROUND(
  SUM(channel_metric) * 1.0 / NULLIF(COUNT(DISTINCT CASE WHEN channel_metric > 0 THEN hcp_id END), 0),
  2
) AS frequency
```

### Breadth & Depth

```sql
-- Breadth = count of unique prescribers
COUNT(DISTINCT CASE WHEN WAINUA_TOTAL_NBRX > 0 THEN HCP_HCA_ID END) AS breadth_nbrx
COUNT(DISTINCT CASE WHEN WAINUA_TOTAL_UNITS > 0 THEN HCP_HCA_ID END) AS breadth_units

-- Depth = sum of metric per prescribing entity
SUM(WAINUA_TOTAL_NBRX) AS depth_nbrx
SUM(WAINUA_TOTAL_UNITS) AS depth_units
```

### Market Share

```sql
-- Brand share of class (Silencer class example)
ROUND(
  SUM(WAINUA_TOTAL_NBRX) * 100.0
  / NULLIF(SUM(WAINUA_TOTAL_NBRX + AMVUTTRA_TOTAL_NBRX + ONPATTRO_TOTAL_NBRX), 0),
  2
) AS wainua_silencer_share_pct
```

---

## Promotional Channels & Metrics

### Channel Columns in `data_prod_promotions_360_genie`

| Channel | Count Column | Reach Logic |
|---------|-------------|-------------|
| **Calls (total)** | `total_call_count` | `total_call_count > 0` |
| **Above-line calls** | `above_line_call_count` | Primary detail calls |
| **Below-line calls** | `below_line_call_count` | Secondary detail calls |
| **Face-to-Face calls** | `Face_to_Face_Call_count` | In-person visits |
| **Non-F2F calls** | `Non_Face_to_Face_Call_count` | Virtual/phone |
| **Veeva emails sent** | `veeva_emails_sent_count` | `veeva_emails_sent_count > 0` |
| **Veeva emails opened** | `veeva_emails_open_count` | Engagement metric |
| **MCRM emails sent** | `mcrm_emails_sent_count` | `mcrm_emails_sent_count > 0` |
| **MCRM emails opened** | `mcrm_emails_open_count` | Engagement metric |
| **Speaker program (attendee)** | `speaker_program_attendee` | `speaker_program_attendee > 0` |
| **Speaker program (speaker)** | `speaker_program_speaker` | Speaking engagements |
| **PulsePoint display** | `pulsepoint_display_impressions` / `_clicks` / `_click_through_rate` | Digital display |
| **PulsePoint native** | `pulsepoint_native_impressions` / `_clicks` / `_click_through_rate` | Native ads |
| **PulsePoint video** | `pulsepoint_video_impressions` / `_clicks` / `_click_through_rate` | Video ads |
| **Doximity** | `doximity_view` / `doximity_click_through` / `doximity_video_played_two_seconds` / `_five_seconds` | Professional network |
| **Triggers** | `no_of_triggers` | Automated promotional triggers |

### Channel Resolution Rule (MANDATORY)

If a reach/frequency/field question does NOT specify a channel → **STOP and ask:**
> "Which channel? Calls, Veeva Email, Calls + Veeva (field/reps), MCRM Email, Speaker Programs, Doximity, PulsePoint, or all combined?"

---

## Segmentation & Targeting

### HCP Segmentation Values (from `d_hcp_specialty_dimension_stage1`)

| Field | Values | Notes |
|-------|--------|-------|
| `Current_Quarter_HCP_Segmentation_Value` | High, Medium, Low, Non-Target, Unsegmented | Q3 2026 |
| `Previous_Quarter_HCP_Segmentation_Value` | High, Medium, Low, Non-Target, Unsegmented | Q2 2026 |
| `Current_Quarter_HCP_Target_Flag` | Yes, No | Is on current target list |
| `Previous_Quarter_HCP_Target_Flag` | Yes, No | Was on previous target list |

### Behavioral Segments (from `data_prod_hcp_hca_360`)

Values: `PATHWAY HCP`, `SILENCER NAIVE`, `INITIAL DIAGNOSER`, `SILENCER LOYALIST`, `KEE INFLUENCER`

### Specialty Groups (3 levels of granularity)

| Level | Values |
|-------|--------|
| `SPECIALTY_GROUP_1` | Most granular (CARDIO, NEURO, PCP, NP/PA, SURGERY, HEMONC, NEPHROLOGIST, OTHERS) |
| `SPECIALTY_GROUP_2` | CARDIO, NEURO, HEMONC, NP/PA, PCP, NEPHROLOGIST, OTHERS |
| `SPECIALTY_GROUP_3` | CARDIO, NEURO, HEMONC, NEPHROLOGIST, OTHERS (NP/PA → PCP) |

**Rule:** ALWAYS use `SPECIALTY_GROUP_1` from `d_hcp_specialty_dimension_stage1` unless user specifies otherwise.

### Call Plan Rule

Available quarters: **Current = Q3 2026, Previous = Q2 2026. No others.**
- Quarter stated or resolvable (e.g., "July 2026" → Q3) → use it
- Not Q2/Q3 2026 → STOP: "Call plan for [quarter] not available."
- Missing/ambiguous → STOP: "Which quarter's call plan?"

---

## Geographic Hierarchy

```
Territory → District → Region
```

Fields: `TERRITORY_NAME`, `TERRITORY_ID`, `DISTRICT_NAME`, `REGION_NAME`
Secondary territory: `TERRITORY_ID_B` (redundant field team for priority zips)

---

## Wainua Specialty Pharmacy Funnel Metrics

| Metric | Description |
|--------|-------------|
| `WAINUA_SP_REFERRALS` | Referral count from Orsini |
| `WAINUA_SPA360_REFERRALS` | Combined referrals (SP + Access 360 Hub) |
| `WAINUA_TOTAL_REFERRALS` | MAX(Komodo excl. Orsini + SP, ELAAD) |
| `WAINUA_SP_NBRX` / `SP_NPS` | New patients from SP |
| `WAINUA_SP_ACTIVE_PATIENTS` | Active patients in SP |
| `WAINUA_SP_PENDING_PATIENTS` | Pending patients |
| `WAINUA_SP_DENIED_PATIENTS` | Denied patients |
| `WAINUA_SP_ABANDONED_PATIENTS` | Abandoned patients |
| `WAINUA_SP_DISCONTINUED_PATIENTS` | Discontinued patients |
| `WAINUA_SP_TRIAGED_PATIENTS` | Triaged patients |
| `WAINUA_SP_UNITS` | Demand units from SP |
| `WAINUA_SD_UNITS` | Units from Specialty Distributors |
| `WAINUA_NEW_FLSP_PATIENTS` | New Free Limited Supply Program patients |
| `WAINUA_CONTINUING_FLSP_PATIENTS` | Continuing FLSP patients |

---

## Diagnosis Metrics

| Metric | Description |
|--------|-------------|
| `ATTR_NEWLY_DIAGNOSED_PATIENTS` | New ATTR diagnoses |
| `HF_NEWLY_DIAGNOSED_PATIENTS` | New Heart Failure diagnoses |
| `HFPEF_NEWLY_DIAGNOSED_PATIENTS` | New HFpEF diagnoses |

---

## General Instructions (Behavioral Rules for the Agent)

### Complexity Classification (First Line of Every Response)

| Level | Description | Behavior |
|-------|-------------|----------|
| **L1 Easy** | Single table, simple counts/filters | Ask follow-up if critical params missing |
| **L2 Intermediate** | Joins, grouped aggregations, trends, ranked lists | Ask follow-up if critical params missing |
| **L3 Complex** | 3+ dimensions, advanced potential, ambiguous intent | MANDATORY: list missing params, do NOT generate SQL until user responds |

### Mandatory Clarification Rules

1. **HCP metric without specific metric named** → Ask: "Total Units or NBRx?"
   - NBRx triggers: "new patients", "new writers", "patient starts", "market share"
   - Units triggers: "units", "total units", "demand units", "dispensed"
   - BYPASS: If user names NTS, switch, add-on, referrals, diagnosis, breadth, depth, DDD, SD → use directly

2. **Channel not specified for reach/frequency** → Ask which channel (see Channel Resolution Rule above)

3. **Call plan quarter ambiguous** → Ask which quarter

4. **Broad "volume" question without brand** → Ask if user wants diagnosis metrics alongside product metrics

### Output Format Rules

- Tabular, human-readable aliases
- No nulls in output
- Percentages to 2 decimals
- Rates in %
- Scalar only if explicitly requested

---

## Sample SQL Patterns

### Target HCPs with Wainua NBRx but Zero Calls (Q2 2026)

```sql
WITH product_cohort AS (
  SELECT DISTINCT CAST(HCP_HCA_ID AS STRING) AS hcp_id
  FROM us_commercial_catalog_prod.lgu_eplontersen.data_prod_hcp_hca_360
  WHERE source_type = 'HCP'
    AND DATA_MATURITY_DATE_FLAG = 1
    AND MONTH >= '2026-04-01' AND MONTH <= '2026-06-01'
    AND WAINUA_TOTAL_NBRX > 0
),
target_cohort AS (
  SELECT DISTINCT CAST(az_cust_id AS STRING) AS hcp_id
  FROM us_commercial_catalog_prod.lgu_eplontersen.d_hcp_specialty_dimension_stage1
  WHERE Previous_Quarter_HCP_Target_Flag = 'Yes'
),
calls AS (
  SELECT CAST(hcp_az_cust_id AS STRING) AS hcp_id,
    SUM(total_call_count) AS total_calls
  FROM us_commercial_catalog_prod.lgu_eplontersen.data_prod_promotions_360_genie
  WHERE Month >= '2026-04-01' AND Month <= '2026-06-01'
  GROUP BY 1
)
SELECT p.hcp_id
FROM product_cohort p
JOIN target_cohort t ON p.hcp_id = t.hcp_id
LEFT JOIN calls c ON p.hcp_id = c.hcp_id
WHERE COALESCE(c.total_calls, 0) = 0
```

### Veeva Email Reach % Among Target HCPs with Amvuttra NBRx (Q2 2026)

```sql
WITH target_amvuttra AS (
  SELECT DISTINCT CAST(h.HCP_HCA_ID AS STRING) AS hcp_id
  FROM us_commercial_catalog_prod.lgu_eplontersen.data_prod_hcp_hca_360 h
  JOIN us_commercial_catalog_prod.lgu_eplontersen.d_hcp_specialty_dimension_stage1 d
    ON CAST(h.HCP_HCA_ID AS STRING) = CAST(d.az_cust_id AS STRING)
  WHERE h.source_type = 'HCP'
    AND h.DATA_MATURITY_DATE_FLAG = 1
    AND h.MONTH >= '2026-04-01' AND h.MONTH <= '2026-06-01'
    AND h.AMVUTTRA_TOTAL_NBRX > 0
    AND d.Previous_Quarter_HCP_Target_Flag = 'Yes'
),
veeva_reached AS (
  SELECT DISTINCT CAST(hcp_az_cust_id AS STRING) AS hcp_id
  FROM us_commercial_catalog_prod.lgu_eplontersen.data_prod_promotions_360_genie
  WHERE Month >= '2026-04-01' AND Month <= '2026-06-01'
    AND veeva_emails_sent_count > 0
)
SELECT
  ROUND(
    COUNT(DISTINCT v.hcp_id) * 100.0 / NULLIF(COUNT(DISTINCT t.hcp_id), 0),
    2
  ) AS veeva_reach_pct
FROM target_amvuttra t
LEFT JOIN veeva_reached v ON t.hcp_id = v.hcp_id
```

---

## Best Practices from IBD Agent (Applicable to Promotional Agents)

### 1. Locked SQL Templates

The IBD agent uses **locked, validated SQL templates** that are never modified in structure — only placeholders are substituted. Apply this pattern for complex promotional queries:
- Define a validated template for each common query type (reach, frequency, top HCPs, IDN ranking)
- Lock the CTE structure, join logic, and filter patterns
- Only allow substitution of: time window, channel, metric, geography

### 2. Mandatory Confirmation Before SQL Execution

IBD requires presenting parameters + rules to the user and waiting for confirmation before generating SQL. For promotional agents:
- Present the parameters being applied (quarter, channel, metric, segment)
- Show which tables and joins will be used
- Wait for user confirmation on L3 queries

### 3. Cross-Skill Dependencies

IBD skills reference each other (e.g., steroid-dependent → patient-cohort-builder). For promotional agents:
- Create separate skills for: Reach/Frequency, IDN Analysis, Promotional Mix, Market Share
- Each skill should reference the base cohort-building skill

### 4. Priority Order for SQL Generation

```
Sample Queries > SQL Expressions > General Instructions > Skill Rules
```

### 5. Dual-Source Handling

IBD runs ELAAD and Optum separately, never merging. For promotional agents with multiple data sources:
- Never UNION different source types without explicit user request
- Document which metrics come from which source
- Use MAX/GREATEST across sources for "best available" metrics

### 6. Claim Quality / Data Quality Filters (Hardcoded, Non-Negotiable)

IBD has mandatory base CTE filters. For promotional agents:
- `DATA_MATURITY_DATE_FLAG = 1` is the equivalent mandatory filter
- `SALES_BLOCK_FLAG = 0 AND ALL_BLOCK_FLAG = 0` for non-blocked HCPs
- `INFUSION_CENTRE_FLAG = 0` for IDN rankings (exclude infusion centers)

### 7. Explicit Code Lists (Never Use LIKE Patterns for Critical Filters)

IBD uses full explicit ICD-10 code lists, never `LIKE 'K51%'`. For promotional agents:
- Use explicit specialty group values, not pattern matching
- Use explicit segmentation values (High, Medium, Low, Non-Target, Unsegmented)
- Use explicit channel column names, not derived patterns

### 8. Date Anchoring on MAX(data_date), Never current_date()

Both agents anchor on the maximum date in the data, not the system clock. This ensures reproducibility and handles data lag.

### 9. COUNT(DISTINCT) for Patient/HCP Counts

Always use `COUNT(DISTINCT pat_id)` or `COUNT(DISTINCT hcp_id)` — never raw COUNT(*) which inflates due to multiple claims/months per entity.

### 10. Workflow Pattern (Evaluate → Load Context → Combine → Confirm → Generate → Validate → Execute)

Both agents follow a strict 7-step workflow. For any new promotional agent:
1. Evaluate the question (classify complexity)
2. Load agent context (tables, expressions, measures)
3. Combine context with domain rules
4. Present parameters for user confirmation
5. Generate SQL from locked templates
6. Validate against all rules
7. Execute and return results

---

## Building a New Promotional Agent — Checklist

### Tables Needed

- [ ] **Main 360 table** — HCP/HCA-month grain with product volumes
- [ ] **Promotions table** — HCP-month grain with channel-level engagement counts
- [ ] **Metric views** — Pre-aggregated measures for common queries
- [ ] **Dimension table** — HCP attributes (specialty, target, segment, geography, IDN)
- [ ] **Reference tables** — Product hierarchy, indication mapping, etc.

### Instructions to Define

- [ ] Source type rules (HCP vs HCA vs both)
- [ ] Data maturity/quality filters
- [ ] Date anchoring rules
- [ ] Metric disambiguation rules (when to ask for clarification)
- [ ] Channel resolution rules
- [ ] Call plan / targeting quarter availability
- [ ] IDN ranking exclusions
- [ ] Complexity classification (L1/L2/L3)
- [ ] Output format standards
- [ ] Out-of-scope declaration

### SQL Expressions to Create

- [ ] IDN Potential (brand, class, market level)
- [ ] Reach % formula
- [ ] Frequency formula
- [ ] Breadth / Depth
- [ ] Market share
- [ ] Specialty grouping logic
- [ ] Target flag resolution

### Measures to Define

- [ ] Total calls / emails / impressions (per channel)
- [ ] Unique HCPs reached (per channel)
- [ ] Average frequency (per channel)
- [ ] Email open rate
- [ ] Click-through rate
- [ ] Prescribing breadth / depth

### Sample Queries to Include

- [ ] Top N HCPs by metric (with target filter)
- [ ] Reach % by channel for a quarter
- [ ] Target HCPs with prescribing but zero promotional touches
- [ ] IDN ranking by potential
- [ ] Promotional mix by specialty
- [ ] Trend over time (monthly/quarterly)

---

## Key Differences: ATTR (Promotional) vs IBD (Claims-Based)

| Dimension | ATTR Promotional Agent | IBD Claims Agent |
|-----------|----------------------|------------------|
| **Data grain** | HCP-month (pre-aggregated) | Claim-level (raw events) |
| **Primary analysis** | Reach, frequency, market share | Patient cohorts, severity, treatment patterns |
| **Complexity** | Joins across 3-5 tables | Complex CTEs with 10+ steps |
| **Time logic** | Calendar quarters, monthly | Rolling windows, index dates, lookback/lookforward |
| **Key formulas** | Reach %, frequency, IDN potential | Attribution (14-day lookback), course merge (30-day gap), confirmatory diagnosis (≥2 claims ≥30 days apart) |
| **Confirmation step** | L3 questions only | Every question (mandatory) |
| **Templates** | Pattern-based (adapt per channel/metric) | Locked verbatim (only substitute placeholders) |

---

## Reference: ATTR Agent Space ID

`01f18a7bc53a15d69aba03c26bc9a2be`

To load full context programmatically:
```
load @[skill.load-genie-context] with space_id = "01f18a7bc53a15d69aba03c26bc9a2be"
```