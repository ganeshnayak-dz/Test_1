# Genie Agent - Setup & Sync Guide

**What this is for:** you built a Genie Space (a Databricks natural-language
agent) in one workspace, plus some skills/notebooks that go with it. This
project lets you push all of that to GitHub, then pull and deploy the Genie
Agent into a second workspace - and keep repeating that whenever you update
the agent.

You never need to hand-edit `databricks.yml` or write any Databricks CLI
commands yourself - three scripts do everything. Just follow the steps
below in order.

**Important: these are three separate, manual commands - nothing runs
automatically after another.** `dev_sync.sh` only ever updates local files
in this folder; it never touches Git. Pushing to GitHub (`push.sh`) is
always a command *you* run yourself afterwards, once you're happy with
what `dev_sync.sh` pulled in. Same for `deploy_target.sh` in the other
workspace - it's its own step after `git pull`.

---

## 0. Before you start (once per pair of workspaces)

You need:

1. **A GitHub repo** to hold this project (can be empty).
2. **A Databricks Git folder in the DEV workspace** (the one where your
   Genie Space and skills already live), linked to that GitHub repo:
   - In the Databricks UI: left sidebar -> **Workspace** -> **Git folders**
     (or **Repos**) -> **Add Git folder** -> paste your GitHub repo's clone
     URL -> Create.
   - This gives you a folder in the workspace that is a real git checkout.
3. **A Databricks Git folder in the OTHER (target) workspace**, linked to
   the **same** GitHub repo, the same way.
4. **Access to a Web Terminal** in each workspace, so you can run `bash`
   commands:
   - Open (or create) any notebook -> attach it to a running cluster /
     serverless compute -> click the **Terminal** icon in the notebook
     toolbar. This opens a terminal already authenticated as you, inside
     that workspace.
5. Copy the three scripts (`dev_sync.sh`, `push.sh`, `deploy_target.sh`),
   `config.json`, and `postprocess_generated_yml.py` from this project into
   the root of that Git folder, in **both** workspaces (e.g. drag-and-drop
   upload via the Workspace UI, or paste each file's contents into a new
   file there).

You're set up once this is done - everything from here on is just running
scripts.

---

## 1. Dev workspace - first time (create the bundle)

Do this once, in the DEV workspace's Web Terminal, `cd`'d into your Git
folder.

### 1.1 Find your Genie Space ID
In the Genie UI: open your space -> **About** (or the "i" icon) -> copy the
**Space ID**. It also appears in the browser URL, e.g.
`.../genie/rooms/01f0abcd1234.../` - the ID is that long string.

### 1.2 List the skills/notebook folders you want tracked
Open `config.json` and edit its `"folders"` list - one entry per folder,
with the **live Workspace path** it currently lives at (`src`) and which
**group folder** you want it filed under inside this repo (`repo_path`):

```json
{
  "...": "... (the rest of config.json stays as-is) ...",
  "folders": [
    { "src": "/Workspace/Users/you@company.com/.assistant/skills/my-skill", "repo_path": "shared_folders/skills" },
    { "src": "/Workspace/Users/you@company.com/.assistant/skills/another-skill", "repo_path": "shared_folders/skills" },
    { "src": "/Workspace/Users/you@company.com/notebooks/my-notebooks", "repo_path": "shared_folders/notebooks" }
  ]
}
```
Delete the sample entries and add your real ones - make sure it's still
valid JSON (every entry needs both `"src"` and `"repo_path"`, in quotes,
each entry separated by a comma). You can add as many as you like, and
edit this list again later any time - `dev_sync.sh` will tell you clearly
if an entry is missing a field or the whole file isn't valid JSON.

**Multiple entries CAN share the same `repo_path`** - that's how you group
several things into the same place (e.g. every skill under
`shared_folders/skills`). Each `src` automatically gets its own subfolder
underneath `repo_path`, named after itself, so they never overwrite each
other. The example above ends up as:
```
shared_folders/
  skills/
    my-skill/          <- from .../skills/my-skill
    another-skill/     <- from .../skills/another-skill
  notebooks/
    my-notebooks/      <- from .../notebooks/my-notebooks
```
The only thing to avoid is two entries whose `src` **and** `repo_path` are
both the same (or two different `src` paths that happen to end in the
same folder name, under the same `repo_path`) - `dev_sync.sh` will warn and
skip the second one if that happens, since it can't tell them apart.

### 1.3 Run the setup
```
cd /path/to/your/git/folder
bash dev_sync.sh
```
It will ask you a few questions (press Enter to accept the suggested
default shown in `[brackets]`):

```
Genie Space ID (Genie UI -> About -> Space ID, or from the URL): 01f0abcd1234...
Bundle name [genie-agent]: my-project-genie-agent
Display title [my-project-genie-agent]: My Project Genie Agent
```

The script then:
- writes `databricks.yml` and `config.json`,
- pulls your Genie Space's content into `resources/` and `src/`,
- auto-detects the SQL warehouse ID (no need to look it up),
- pulls each folder from step 1.2 into `shared_folders/` inside this repo.

When it finishes you'll see:
```
Done. Everything needed is now in this folder.
Review the changes, then run:
  bash push.sh
```

### 1.4 Push to GitHub
```
bash push.sh
```
or with your own commit message:
```
bash push.sh 'initial genie agent setup'
```
If you see `⚠️ Git CLI not available from terminal` (common in some Web
Terminals), commit instead via the Databricks UI: open the Git folder ->
**Git** icon in the sidebar -> write a commit message -> **Commit & Push**.

Your GitHub repo now has the full bundle: `databricks.yml`, `config.json`,
`resources/`, `src/`, and `shared_folders/`.

---

## 2. Other workspace - first time (deploy the agent)

Do this once, in the OTHER (target) workspace's Web Terminal, `cd`'d into
its Git folder (the one linked to the same GitHub repo).

### 2.1 Pull the repo
Either:
```
git pull
```
or, if git isn't available from the terminal (common in Web Terminals -
you'll see `⚠️ Git CLI not available from terminal`): Git folder UI ->
**Git** icon -> **Pull**.

**Make sure this step actually completed before continuing** -
`deploy_target.sh` in step 2.2 tries this same pull for you as a
convenience, but if the git CLI isn't available it can only warn you, not
force a pull to happen - it will deploy whatever is currently in these
files either way, pulled or not.

### 2.2 Deploy the Genie Agent
```
bash deploy_target.sh
```
This validates the bundle and runs `databricks bundle deploy`, which
creates the Genie Space in **this** workspace from the files currently in
this folder. It does **not** touch skills or notebooks.

### 2.3 Copy skills/notebooks manually (for now)
For each folder under `shared_folders/`, upload it to wherever it needs to
live in this workspace - either via the Workspace UI (drag-and-drop the
folder in), or with the CLI, e.g.:
```
databricks workspace import-dir shared_folders/my-skill /Workspace/Users/<your-email>/.assistant/skills/my-skill --overwrite
```
(Replace the folder name and destination path for each entry you listed in
`config.json`'s `"folders"` list.)

Your Genie Agent is now live in the new workspace.

---

## 3. Ongoing updates (repeat as often as you like)

Whenever you change the Genie Space (in the Genie UI) or a skill/notebook
in the **dev** workspace:

**In the dev workspace:**
```
cd /path/to/your/git/folder
bash dev_sync.sh
```
This time it will **not** ask you any setup questions (it already knows
the Space ID from `config.json`) - it just re-pulls the latest Genie Space
content and the folders listed in `config.json`.
```
bash push.sh
```
(or `bash push.sh 'describe what changed'`)

**In the other workspace, whenever you want those changes live there too:**
```
git pull
bash deploy_target.sh
```
And re-copy any changed skill/notebook folders manually, same as step 2.3.

That's the entire day-to-day workflow - two commands on each side.

---

## Quick command reference

| Where | Command | Does |
|---|---|---|
| Dev workspace | `bash dev_sync.sh` | Create (first time) or update (every time after) the bundle; always pulls the Genie Space + skill/notebook folders into the repo. |
| Dev workspace | `bash push.sh` | Validate, commit, push to GitHub. |
| Dev workspace | `bash push.sh 'message'` | Same, with your own commit message. |
| Other workspace | `git pull` | Get the latest files from GitHub. |
| Other workspace | `bash deploy_target.sh` | Pull + deploy only the Genie Agent to this workspace, using the `dev` target. |
| Other workspace | `bash deploy_target.sh test` | Same, but deploys the `test` target instead (only works if `config.json` has a `test` section - see below). |

---

## Files in this project

| File | Purpose |
|---|---|
| `dev_sync.sh` | **Run in the dev workspace.** First time: asks setup questions and creates the bundle. Every time after: silently updates it. Always pulls the Genie Space and your skills/notebooks folders into this repo. |
| `push.sh` | **Run in the dev workspace**, after `dev_sync.sh`. Validates, then commits + pushes everything to GitHub. |
| `deploy_target.sh` | **Run in the other workspace.** Pulls the latest from GitHub, then deploys only the Genie Agent - the `dev` target by default, or `bash deploy_target.sh test` to deploy the `test` target instead. |
| `config.json` | **The only file you edit by hand.** Space ID, warehouse ID, bundle name, resource key, the list of skills/notebooks folders to pull into this repo, and (optionally) `dev`/`test` target settings. See reference below. |
| `databricks.yml` | The DAB project file. Written/updated automatically by `dev_sync.sh` on every run (`dev` target, plus `test` if `config.json` has one) - you shouldn't need to hand-edit it. |
| `resources/*.genie_space.yml`, `src/*.geniespace.json` | The Genie Space's definition and content, pulled from the live space by `dev_sync.sh`. |
| `postprocess_generated_yml.py` | Internal helper `dev_sync.sh` calls automatically to keep the warehouse ID and user path dynamic instead of hardcoded. You never run this yourself. |
| `shared_folders/` | Created automatically the first time a folder is pulled in. The version-controlled copy of your skills/notebooks that gets committed and pushed to GitHub. |

## config.json reference

Everything editable lives in this one file - there is no second config
file to worry about.

```json
{
  "bundle_name": "my-genie-agent",
  "resource_key": "my_genie_agent",
  "title": "My Genie Agent",
  "space_id": "01f0abcd1234...",
  "warehouse_id": "auto-detected-on-first-run",
  "folders": [
    { "src": "/Workspace/Users/you@company.com/.assistant/skills/my-skill",
      "repo_path": "shared_folders/skills" },
    { "src": "/Workspace/Users/you@company.com/.assistant/skills/another-skill",
      "repo_path": "shared_folders/skills" }
  ],
  "dev": {
    "mode": "development",
    "title": "[Dev] My Genie Agent",
    "permissions": []
  },
  "test": {
    "mode": "production",
    "workspace_host": "https://your-test-workspace.cloud.databricks.com/",
    "warehouse_id": "0123456789abcdef",
    "title": "[Test] My Genie Agent",
    "permissions": [
      { "user_name": "someone@company.com", "level": "CAN_MANAGE" }
    ]
  }
}
```
- `bundle_name`, `resource_key`, `title` - set once, during the questions in
  step 1.3. `resource_key` is auto-derived from `bundle_name` (lowercased,
  non-letters/digits turned into `_`).
- `space_id` - the Genie Space this project tracks. `dev_sync.sh` reads
  this on every run to decide first-run vs update, and to know which space
  to pull.
- `warehouse_id` - filled in automatically after the first pull. You never
  need to look this up yourself.
- `folders` - the skills/notebook folders to keep tracked in this repo,
  each with:
  - **`src`** - the live Workspace path to pull the folder FROM (in the dev
    workspace). Can be anywhere you have read access to.
  - **`repo_path`** - the group folder it lands under inside this repo
    (relative to this folder). Multiple entries can share the same
    `repo_path` - each `src` gets its own subfolder underneath it, named
    after itself, so several skills/notebooks can sit side by side without
    overwriting each other (see the worked example in step 1.2). This is
    what actually gets committed and pushed - `push.sh`'s `git add .` picks
    it up automatically, no extra step needed.

  `dev_sync.sh` only ever pulls `src -> repo_path/<name>`; it never deploys
  folders back out to a workspace. Deploying them into the other workspace
  is the manual step 2.3 / 3 above, for now. Every entry needs both `src`
  and `repo_path`, or `dev_sync.sh` will warn and skip it.
- `dev` *(optional)* - overrides for the `dev` target's `mode`, `title`,
  and `permissions`, the same shape as `test` below. Leave it out entirely
  and `dev_sync.sh` just uses the top-level `title` (and `mode: development`,
  no `permissions:` block) like it always has - this section only exists so
  you can override those per-target without touching the top-level `title`
  (which is also used as `test`'s title fallback, see below).
- `test` *(optional)* - values for a second, `test` target (a separate
  workspace, e.g. for UAT/sign-off before something goes to `dev` for
  real use). If present, `dev_sync.sh` writes a matching `test:` target
  into `databricks.yml` on every run, right alongside `dev:` - same
  pattern as the two-target `databricks.yml` some AZ projects already use
  (`dev` + `test`). Fields:
  - **`workspace_host`** and **`warehouse_id`** - required for the `test`
    target to be generated at all; if either is missing, `dev_sync.sh`
    writes a `dev`-only bundle (same as if `test` weren't in `config.json`).
  - **`mode`** - defaults to `production` if omitted.
  - **`title`** - the Genie Space title shown in the test workspace;
    defaults to `[Test] <title>` if omitted.
  - **`permissions`** - a list of `{ "user_name": "...", "level": "..." }`
    entries (level defaults to `CAN_MANAGE`), written as the target's
    `permissions:` block - who gets access to the Genie Space deployed to
    the test workspace.

  Deploy it with `bash deploy_target.sh test` (run in the test workspace,
  once its Git folder is set up the same way as step 0 describes for the
  "other" workspace) - see the command reference below.

**To point this project at a different Genie Space later:** set `space_id`
back to `PASTE_YOUR_GENIE_SPACE_ID_HERE` (or delete `config.json` entirely),
then run `bash dev_sync.sh` again - it will treat it as a first run and ask
the setup questions again (your `folders` list is preserved either way).

## Troubleshooting

| Problem | Fix |
|---|---|
| "Git CLI not available from terminal" | Normal in some Web Terminals. Use the Workspace Git sidebar instead (Git icon -> Commit & Push, or Pull), or ask the Databricks Assistant to do it for you. |
| `dev_sync.sh` fails at "Pulling Genie Space" | Double check the Space ID in `config.json` is correct and that you (the current user) have access to that Genie Space. |
| `Error: Unable to locate the bundle root: databricks.yml not found` | `config.json` has a Space ID but `databricks.yml` doesn't exist yet (e.g. it was deleted, or `config.json` was copied in by hand). Just run `bash dev_sync.sh` again - it now detects the missing `databricks.yml` and re-runs first-time setup, with your existing Space ID pre-filled so you can just press Enter to confirm it. |
| Folder pull says "Could not read `<src>`" | The `src` path in `config.json`'s `"folders"` list is wrong, or you don't have read access to it from this workspace/user. Fix the path or ask the owner for access. |
| "(Nothing pulled...)" / a `WARN:` or `ERR:` line about `config.json` | The `"folders"` list in `config.json` has a problem - either it's not valid JSON (check for a missing comma or quote), two entries that resolve to the exact same destination (see step 1.2), or an entry is missing `"src"` or `"repo_path"`. The exact entry and reason is printed right above this line - fix it in `config.json` and run `bash dev_sync.sh` again. |
| `Error(message=BAD_REQUEST: Node named '<name>' already exists ...)` / `wsfs/workspace/...` error during folder pull | A transient Workspace-filesystem conflict - `dev_sync.sh` now retries automatically. If it still happens, just run `bash dev_sync.sh` again - it's safe to re-run. This is unrelated to `push.sh` / Git, even though it can print right after `dev_sync.sh`'s "Done" message. |
| `mkdir: cannot create directory '.../shared_folders...': No such file or directory` | Same kind of transient Workspace-filesystem conflict as above - `dev_sync.sh` now retries this too and skips just that one folder (with a `❌` message) instead of stopping the whole run. If it keeps failing for the same folder every time, `shared_folders/` may have been left in a half-created state by an earlier interrupted run: delete the specific subfolder under `shared_folders/` (via the Workspace UI, or `rm -rf shared_folders/<name>`) and run `bash dev_sync.sh` again. |
| `deploy_target.sh` prints "Git CLI not available" / "git pull failed" | Expected in most Web Terminals - it's a warning, not a failure; the script still moves on to deploy. It cannot pull for you in that case, so make sure you pulled via the Workspace Git sidebar (Git icon -> Pull) yourself first, or the deploy will use stale files. |
| `deploy_target.sh` fails at "Deploying" | Make sure you ran `git pull` first (or pulled via the UI) so `databricks.yml`/`resources/` are up to date, and that you have permission to deploy in this workspace. |
| `Error: test: no such target` | `databricks.yml` only gets a `test` target if `config.json` has a usable `test` section (needs `workspace_host` + `warehouse_id`). Add it, run `bash dev_sync.sh` again, and confirm `databricks.yml` now has a `test:` block before running `bash deploy_target.sh test`. |
| `Resources:` empty in `databricks bundle summary` | Usually a missing `include: - resources/*.yml` line in `databricks.yml` - re-run `bash dev_sync.sh` to regenerate it. |
| Skill/notebook folder didn't show up in the other workspace | Expected - `deploy_target.sh` only deploys the Genie Agent. Copy folders under `shared_folders/` manually (step 2.3). |
