---
name: load-genie-context
description: Loads the full context (instructions, SQL expressions, measures, sample queries, tables) from any Genie Agent given its space_id; load when you need to retrieve a Genie Agent's complete configuration to generate SQL yourself.
metadata:
  compatible-agents: genie
---

# Load Genie Context

This skill provides a **generalized procedure** for extracting the full context of any Genie Agent so that Genie (this assistant) can generate SQL using the agent's curated logic — without routing the question to the Genie Agent itself.

## When to Use

Load this skill whenever another skill (e.g., an agent-based skill) needs the full context of a Genie Agent to generate SQL. This skill works for ANY Genie Agent — not just one specific agent. The calling skill provides the `space_id`.

## Procedure

### Step 1: Identify the Target Genie Agent

The calling skill provides the `space_id` of the target Genie Agent. Use that space_id in the next step. This skill does NOT maintain a registry of agents — it is fully generalized and works with any valid space_id passed to it.

### Step 2: Read the Full Genie Agent JSON

Call `read_full_genie_space_json(space_id="<space_id>")` to retrieve the complete agent configuration.

This returns a JSON document containing:
- `title` — Agent name
- `description` — Agent description
- `space.data_sources.tables[]` — All tables with identifiers and column configs (synonyms, format assistance flags)
- `space.instructions.text_instructions[]` — General instructions (behavior rules, defaults, business logic)
- `space.instructions.sql_snippets.expressions[]` — SQL expressions (reusable CASE statements, flags, derivations)
- `space.instructions.sql_snippets.measures[]` — Measures / metrics (aggregations, time derivations, counts)
- `space.instructions.example_question_sqls[]` — Sample queries (question + SQL pairs)

### Step 3: Extract and Apply the Context

Once you have the JSON, extract and internalize ALL of the following. **Do not skip any section.**

#### 3a. General Instructions (`text_instructions`)

Read every `text_instructions[].content` entry thoroughly. These contain:
- Behavior rules (e.g., no clarifying questions unless mandatory input missing)
- Scope rules (e.g., reporting only, no modeling)
- Default logic (e.g., run on both data sources if not specified)
- Filter rules (e.g., Therapy → `drug_class`/`proc_class`; Product → `prod_nm` AND `genr_nm`)
- Date anchoring rules (e.g., anchor on `MAX(srvc_dt)`, use `ADD_MONTHS`, never `current_date()`)
- Output formatting rules (e.g., tabular, no nulls, 2 decimals)
- Mandatory logic triggers (e.g., "newly diagnosed" → 12-month lookback exclusion)
- Priority order (Sample Queries > SQL Expressions > General Instructions)

**CRITICAL:** These instructions are MANDATORY. Apply them to every query you generate. They override your own defaults.

#### 3b. SQL Expressions (`sql_snippets.expressions`)

Each expression has:
- `id` — unique identifier
- `display_name` — human-readable name (e.g., "Diagnosis Flag", "Comorbidity Flags")
- `sql` — the exact SQL logic (CASE statements, EXISTS checks, etc.)
- `instruction` — when/how to use this expression
- `synonyms` — trigger words that indicate this expression should be used

**CRITICAL RULES for expressions:**
- When the user's question matches an expression's `display_name` or any of its `synonyms`, you MUST use that exact SQL expression — do NOT write your own version.
- Copy the SQL exactly as written. Do not modify column names, logic, or code lists.
- If the instruction says "Use optum foundation layer table if running on optum data," swap the table reference accordingly but keep the logic identical.
- Expressions are reusable building blocks — embed them in your CTEs or SELECT statements as needed.

#### 3c. Measures (`sql_snippets.measures`)

Each measure has:
- `id` — unique identifier
- `display_name` — human-readable name (e.g., "Claim Count", "Year-Quarter Derivation")
- `sql` — the exact SQL formula
- `instruction` — when/how to use this measure
- `synonyms` — trigger words that indicate this measure should be used

**CRITICAL RULES for measures:**
- When the user asks for something matching a measure's `display_name` or `synonyms`, use the exact SQL formula provided.
- These define how metrics are calculated — do not invent your own aggregation logic when a measure already exists.

#### 3d. Sample Queries (`example_question_sqls`)

Each sample query has:
- `id` — unique identifier
- `question` — the natural language question it answers
- `sql` — the complete SQL query

**CRITICAL RULES for sample queries:**
- If the user's question closely matches a sample query's `question`, use that SQL as your base — adapt it as needed but preserve its structure, joins, filters, and logic.
- Sample queries have the HIGHEST priority (per general instructions). They represent validated, correct patterns.
- Even if the question doesn't match exactly, sample queries show you the correct join patterns, CTE structures, and filter approaches for this agent's tables.

#### 3e. Tables (`data_sources.tables`)

Each table has:
- `identifier` — full three-level name (catalog.schema.table)
- `column_configs[]` — columns with synonyms and flags

**CRITICAL RULES for tables:**
- ONLY use tables listed in the agent's `data_sources.tables`. Do NOT use any other tables unless the user explicitly asks.
- Use the exact `identifier` as the table name in your SQL.
- Column synonyms tell you what user-facing terms map to which actual column names.

### Step 4: Generate SQL Using the Context

With all context loaded, generate SQL that:
1. Uses ONLY the agent's tables (from 3e)
2. Applies ALL general instruction rules (from 3a)
3. Uses the EXACT SQL expressions when triggered (from 3b)
4. Uses the EXACT measures when triggered (from 3c)
5. Follows sample query patterns when applicable (from 3d)
6. Combines with any sub-skill rules (severity, control status, steroid dependence, etc.) if loaded

**Priority order when conflicts arise:**
1. Sample Queries (highest — use as-is if matching)
2. SQL Expressions (use exact SQL for flags/derivations)
3. General Instructions (apply behavior/scope/output rules)
4. Sub-skill rules (clinical logic from severity/control/steroid skills)

### Step 5: Execute and Return

Execute the SQL via `execute_sql_query_with_timeout` and return results to the user.

---

## Adding a New Agent

To extend this skill for a new Genie Agent:
1. The calling skill provides the new agent's `space_id` — no changes needed to this skill.
2. The procedure (Steps 2–5) works identically for any agent — no code changes needed.
3. Create a new agent-specific skill that references this skill and provides the routing logic + any domain-specific sub-skills.

---

## Example Workflow

```
User: "How many UC patients are there by age group?"

1. Orchestrator → identifies topic → loads relevant agent skill
2. Agent skill → loads @[skill.load-genie-context] with the appropriate space_id
3. load-genie-context procedure:
   a. read_full_genie_space_json("<space_id>")
   b. Extract general instructions → e.g., "run on both data sources if not specified"
   c. Extract expressions → find relevant diagnosis flags, age calculations, etc.
   d. Extract measures → find relevant measures
   e. Extract tables → identify foundation layer tables
4. Generate SQL using:
   - Diagnosis flag expression (exact CASE/EXISTS logic from agent)
   - Age expression (exact CASE logic from agent)
   - Both foundation tables (per general instruction default)
5. Execute SQL → return results
```

---

## Important Notes

- **This skill is a PROCEDURE, not a data store.** It tells you HOW to extract context from any Genie Agent. The actual context lives in the Genie Agent's JSON and is read fresh each time.
- **This skill is fully generalized.** It does NOT hardcode any specific agent name, space_id, or table. The calling skill provides the space_id.
- **Never call `ask_genie_space`** when using this skill — the whole point is that YOU generate the SQL using the agent's context.
- **Read the full JSON thoroughly** — do not skim. Every expression, every instruction, every sample query matters.
- **If `read_full_genie_space_json` fails** (e.g., no edit permission), fall back to `get_asset_info(asset="genie.<space_id>")` which provides a read-only view of the same information.
