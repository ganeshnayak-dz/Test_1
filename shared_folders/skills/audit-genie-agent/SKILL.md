---
name: audit-genie-agent
description: Audits a Genie Agent for gaps and suggests improvements to instructions, table metadata, synonyms, SQL expressions, measures, example queries, and overall quality; load when user asks to review, audit, improve, or find gaps in a Genie Agent.
metadata:
  compatible-agents: genie
---

# Audit Genie Agent

This skill provides a structured procedure for auditing any Genie Agent and producing actionable improvement suggestions. It evaluates the agent's instructions, table metadata, column synonyms, SQL expressions, measures, example queries, and overall configuration quality.

## When to Use

Load this skill when the user asks to:
- Review / audit / evaluate a Genie Agent
- Find gaps or issues in a Genie Agent
- Suggest improvements for a Genie Agent
- Check if a Genie Agent follows best practices
- Identify what's missing or can be enhanced in an agent

## Inputs

The user provides ONE of:
- **Agent name** — search for it via `search_assets` to find the `space_id`
- **Agent space_id** — the 32-character hex ID directly

## Procedure

### Step 1: Load the Agent's Full Configuration

1. If the user gave a name, search for it: `search_assets(query="Genie Agent named <name>", keywords=[<name>], asset_types=["ASSET_TYPE_SPACE"])`
2. Confirm editability via `get_asset_info(asset="genie.<space_id>")` — check the `editable` flag.
3. If editable, call `read_full_genie_space_json(space_id="<space_id>")` to get the full JSON document.
4. If NOT editable, use `get_asset_info(asset="genie.<space_id>")` for a read-only view (you can still audit but cannot apply fixes).

### Step 2: Audit Each Dimension

Evaluate the agent across ALL of the following dimensions. For each, note what's good (✅) and what needs improvement (⚠️ or ❌).

---

#### 2A. Title & Description

| Check | What to look for |
|-------|-----------------|
| Clarity | Is the title descriptive enough for users to understand the agent's purpose at a glance? |
| Description completeness | Does the description explain: (1) what questions the agent can answer, (2) what data/domain it covers, (3) scope limitations, (4) who it's for? |
| Audience | Is it clear who the intended users are (analysts, business users, clinicians, etc.)? |
| Discoverability | Would a user searching for this agent find it based on the title + description keywords? |
| Actionability | Does the description give users example questions or hint at what to ask? |
| Data freshness | Does it mention how current the data is or what time range is covered? |

**Common gaps:**
- Generic title like "Sales Agent" with no description
- Missing scope boundaries (what the agent does NOT cover)
- No mention of data freshness or time range covered
- Description is too technical (references table names instead of business concepts)
- No example questions in the description to guide new users
- Description doesn't mention key entities/dimensions users can ask about

**Improvement suggestions — always provide a REWRITTEN description:**
- If description is empty or <20 chars → write a full suggested description (2-4 sentences) covering: purpose, data scope, example questions, and limitations
- If description exists but is weak → provide a "before/after" rewrite showing the improvement
- Structure suggested descriptions as: "[What it does]. [What data it covers]. [Example questions users can ask]. [What it does NOT cover or limitations]."
- Example rewrite:
  - ❌ Before: "Agent for sales data"
  - ✅ After: "Answers questions about revenue, order volume, and customer acquisition across all regions. Covers data from Jan 2022 to present, refreshed daily. Ask things like 'What was revenue last quarter by region?' or 'Who are our top 10 customers by lifetime value?' Does not cover marketing attribution or product inventory."

---

#### 2B. General Instructions (`text_instructions`)

| Check | What to look for |
|-------|-----------------|
| Length & readability | Are instructions concise and well-organized, or a wall of text? Ideal: grouped by topic with clear headers using `\n` separators. |
| Behavior rules | Does it specify how to handle ambiguous questions? (e.g., ask for clarification vs. assume defaults) |
| Default logic | Are defaults defined? (e.g., default date range, default granularity, default filters) |
| Filter mapping | Are user-facing terms mapped to column values? (e.g., "Therapy" → `drug_class` column) |
| Date handling | Is there a date anchoring strategy? (e.g., use `MAX(date_col)` vs. `current_date()`) |
| Output formatting | Are output rules specified? (e.g., decimal places, NULL handling, column ordering) |
| Priority order | Is there a stated priority when conflicts arise between instructions, expressions, and sample queries? |
| Scope boundaries | Does it say what the agent should NOT do? |
| Contradictions | Are there any conflicting instructions? |

**Common gaps:**
- No date anchoring rule → agent uses `current_date()` which breaks on stale data
- No NULL/empty handling → agent returns confusing results
- No disambiguation rules → agent guesses instead of asking
- Instructions are one giant paragraph → hard for the LLM to parse
- Missing filter mappings → user says "active customers" but agent doesn't know the filter

**Improvement suggestions format:**
- If instructions are >2000 chars with no structure → suggest breaking into sections with `\n\n## Section Name\n` headers
- If no date logic → suggest adding: "Always anchor date calculations on MAX(<date_column>) from the data, never use current_date()."
- If no output rules → suggest adding: "Format numbers to 2 decimal places. Replace NULL with 'N/A'. Order results by the primary metric descending."

---

#### 2C. Tables & Column Metadata (`data_sources.tables`)

| Check | What to look for |
|-------|-----------------|
| Table descriptions | Does each table have a clear `description` explaining what it contains? |
| Column synonyms | Do columns have `synonyms` for common user-facing terms? (e.g., `srvc_dt` → synonyms: ["service date", "date of service"]) |
| Column descriptions | Are important columns described? |
| Format assistance | Are `is_format_assistance` flags set for columns that need special formatting? |
| Redundant tables | Are there tables that overlap significantly? Could confuse the agent. |
| Missing tables | Based on the instructions and expressions, are there tables referenced that aren't in the data sources? |
| Join keys | Are join relationships between tables obvious from column names, or do they need explicit instruction? |

**Common gaps:**
- Cryptic column names with no synonyms (e.g., `srvc_dt`, `proc_cd`, `genr_nm`)
- No table descriptions → agent doesn't know when to use which table
- Tables referenced in SQL expressions but not in `data_sources.tables`
- No join guidance when multiple tables exist → agent may produce incorrect joins
- Missing synonyms for domain jargon → user says "diagnosis" but column is `dx_cd`

**Improvement suggestions — always provide CONCRETE rewrites:**
- For each table missing a description → **write a suggested description** by inspecting its columns (run `SELECT * FROM <table> LIMIT 5` if needed to understand the data)
- For columns with cryptic names → suggest specific synonyms based on apparent meaning and domain context
- For multi-table agents with no join instructions → suggest exact join guidance text to add to `text_instructions`
- For table descriptions that are too technical → rewrite in user-facing language
- Example table description rewrite:
  - ❌ Before: (no description)
  - ✅ After: "Patient-level claims data with one row per service encounter. Contains diagnosis codes, procedure codes, service dates, provider info, and cost fields. Use this table for patient counts, utilization analysis, and cost breakdowns."

---

#### 2D. SQL Expressions (`sql_snippets.expressions`)

| Check | What to look for |
|-------|-----------------|
| Completeness | Do expressions cover the key derived fields users would ask about? |
| Synonyms | Does each expression have relevant `synonyms` so it triggers correctly? |
| Instructions | Does each expression have a clear `instruction` explaining when to use it? |
| SQL correctness | Is the SQL syntactically valid? Are table/column references correct? |
| Hardcoded values | Are there hardcoded code lists (ICD codes, status values) that might go stale? |
| Reusability | Are expressions modular, or do they duplicate logic? |
| Naming | Are `display_name` values clear and user-facing? |

**Common gaps:**
- Expression exists but has no synonyms → never gets triggered
- Expression references a table not in `data_sources.tables`
- Duplicate logic across multiple expressions
- Missing expressions for common user questions (inferred from sample queries)
- Overly complex expressions that could be split into smaller, composable pieces

---

#### 2E. Measures (`sql_snippets.measures`)

| Check | What to look for |
|-------|-----------------|
| Coverage | Are key metrics defined as measures? (counts, sums, averages, rates) |
| Synonyms | Does each measure have synonyms? (e.g., "patient count" → ["number of patients", "how many patients"]) |
| Instructions | Is it clear when each measure applies? |
| SQL correctness | Are aggregation functions correct? |
| Consistency | Do measures use consistent patterns? (e.g., all use the same date column) |

**Common gaps:**
- Key metrics are only in sample queries, not defined as reusable measures
- Measures lack synonyms → user phrasing doesn't trigger them
- No percentage/rate measures when users commonly ask for proportions
- Inconsistent date filtering across measures

---

#### 2F. Example/Sample Queries (`example_question_sqls`)

| Check | What to look for |
|-------|-----------------|
| Coverage | Do sample queries cover the most common user questions? |
| Variety | Do they demonstrate different query patterns? (aggregation, filtering, joins, time-based, ranking) |
| Complexity range | Are there both simple and complex examples? |
| Question clarity | Are the `question` fields phrased as users would actually ask? |
| SQL quality | Is the SQL well-structured, using CTEs where appropriate? |
| Consistency | Do sample queries follow the same patterns as the general instructions? |
| Filter examples | Do they show how to apply the filter mappings from instructions? |
| Edge cases | Do any handle NULL values, empty results, or ambiguous inputs? |

**Common gaps:**
- Too few sample queries (<3) → agent has limited patterns to learn from
- All queries are simple SELECTs → no examples of complex joins, CTEs, or window functions
- Questions are written in developer language, not user language
- Sample queries contradict general instructions (e.g., different date logic)
- No examples showing how to combine multiple expressions/measures
- Missing queries for time-based analysis (YoY, MoM, trends)

---

#### 2G. Overall Coherence & Cross-Cutting Issues

| Check | What to look for |
|-------|-----------------|
| Instruction ↔ Expression alignment | Do instructions reference expressions that exist? Vice versa? |
| Table ↔ SQL alignment | Do all SQL (expressions, measures, samples) reference only tables in `data_sources`? |
| Synonym overlap | Do different expressions/measures have overlapping synonyms that could cause confusion? |
| Completeness vs. bloat | Is the agent trying to do too much? Should it be split? |
| User journey coverage | Can a new user figure out what to ask? (description + sample questions) |

---

### Step 3: Generate the Audit Report

Produce a structured report with:

1. **Summary Score** — Overall health rating (e.g., 🟢 Good / 🟡 Needs Work / 🔴 Significant Gaps)
2. **Strengths** — What the agent does well (2-3 bullet points)
3. **Critical Issues** — Must-fix problems that would cause incorrect answers (❌)
4. **Improvement Opportunities** — Nice-to-have enhancements (⚠️)
5. **Specific Recommendations** — Actionable suggestions with examples:
   - Exact text to add/change for instructions
   - Specific synonyms to add to columns/expressions
   - New expressions or measures to create
   - New sample queries to add
   - Tables that need descriptions

### Step 4: Offer to Apply Fixes

If the agent is editable, offer to apply the suggested improvements using `patch_genie_space_json`. Group fixes by priority:
- **P0 (Critical):** Fixes that prevent incorrect answers
- **P1 (High):** Fixes that significantly improve answer quality
- **P2 (Medium):** Fixes that improve user experience
- **P3 (Low):** Polish and nice-to-haves

Ask the user which fixes they'd like applied before making any changes.

---

## Example Output Structure

```
# 🔍 Genie Agent Audit: [Agent Name]

## Summary: 🟡 Needs Work
The agent has solid table coverage and good SQL expressions, but lacks synonyms,
has no date anchoring strategy, and sample queries are insufficient.

## ✅ Strengths
- Comprehensive SQL expressions for key clinical flags
- Clear filter mapping for therapy vs. product
- Well-structured CTE patterns in sample queries

## ❌ Critical Issues
1. **No date anchoring** — Instructions don't specify how to handle dates.
   The agent will use `current_date()` which returns wrong results on stale data.
   → Add: "Always use `SELECT MAX(srvc_dt) FROM ...` as the anchor date."

2. **Table `xyz` referenced in expression but not in data_sources**
   → Add the table to `data_sources.tables` or fix the expression.

## ⚠️ Improvement Opportunities
1. **Column synonyms missing** — 12 columns have cryptic names with no synonyms.
   Examples:
   - `srvc_dt` → add synonyms: ["service date", "date of service", "claim date"]
   - `proc_cd` → add synonyms: ["procedure code", "CPT code"]

2. **Only 2 sample queries** — Add at least 3-5 more covering:
   - Time-based analysis (trend, YoY)
   - Multi-filter combination
   - Ranking/top-N

3. **Measures lack synonyms** — "Patient Count" has no synonyms.
   → Add: ["number of patients", "how many patients", "patient volume"]

## 📋 Specific Recommendations

### Instructions to Add
[Exact text suggestions]

### Synonyms to Add
| Element | Current Synonyms | Suggested Additions |
|---------|-----------------|-------------------|
| ... | ... | ... |

### New Sample Queries to Add
| Question | Why |
|----------|-----|
| "What is the trend of X over the last 12 months?" | No time-series example exists |

### New Expressions/Measures to Create
| Name | Why | Suggested SQL |
|------|-----|--------------|
| ... | ... | ... |
```

---

## Step 2H: Proactive Better-Suggestion Generation

Beyond flagging gaps, the audit MUST actively generate **better alternatives**. For every issue found, provide a concrete "do this instead" suggestion:

### Description Suggestions
- Read the agent's tables, expressions, and sample queries to understand what it actually does
- Write a **complete suggested description** that a new user would find helpful
- Include 2-3 example questions the agent can answer (derived from sample queries)
- Mention scope limitations (derived from what tables/data are NOT present)

### Instruction Improvement Suggestions
- If instructions are unstructured → provide a **restructured version** with clear sections
- If instructions are missing key rules → write the exact text to add, ready to paste
- If instructions are contradictory → highlight the conflict and suggest which to keep

### Synonym Suggestions
- For every column/expression/measure missing synonyms → suggest 3-5 synonyms based on:
  - Common business terms for that concept
  - How users would naturally phrase it in a question
  - Abbreviations and full forms (e.g., "YoY" ↔ "year over year")
  - Domain jargon variations

### Expression & Measure Suggestions
- If sample queries contain repeated logic that isn't an expression → suggest extracting it as a reusable expression
- If users would commonly ask for a metric not covered → suggest a new measure with SQL
- If an expression is overly complex → suggest splitting into smaller composable pieces

### Sample Query Suggestions
- Identify **question patterns** not covered (time-series, ranking, comparison, filtering, aggregation)
- Write 3-5 new sample queries with both the `question` (in natural user language) and `sql`
- Ensure suggested queries use the agent's existing expressions and measures where applicable

---

## Notes

- This skill is READ-ONLY by default — it audits and suggests. It only modifies the agent if the user explicitly asks to apply fixes.
- If the agent is not editable, still produce the full audit report — the user can share it with the agent owner.
- When auditing, also consider loading `@[skill.load-genie-context]` to use its structured extraction procedure for reading the agent's JSON.
- For very large agents, focus on the highest-impact issues first rather than listing every minor gap.
- **Always provide concrete rewrites** — don't just say "description is missing", write the description. Don't just say "add synonyms", list the exact synonyms. The goal is that the user can approve and apply suggestions with minimal effort.
- When generating suggestions, **sample the actual data** (run `SELECT DISTINCT <col> LIMIT 20` on key columns) to ground your suggestions in reality — e.g., suggest filter values that actually exist, date ranges that match the data, and synonyms that match actual column content.