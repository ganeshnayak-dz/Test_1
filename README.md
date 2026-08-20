# Genie Agent DAB - Setup & Sync Guide

This project keeps a Databricks Genie Space under version control using a
Databricks Asset Bundle (DAB), and keeps a set of shared workspace folders
(skills, reference notebooks, etc.) in sync alongside it.

## Files in this project

| File | Purpose |
|---|---|
| `init_genie_bundle.sh` | One-time interactive setup. Run this first, only once, in a brand-new empty Git folder. |
| `config.json` | Central config: Space ID, warehouse ID, bundle name, resource key, test-target settings. Edit this instead of the scripts. |
| `databricks.yml` | The DAB project file (generated from `config.json`). |
| `resources/*.genie_space.yml` | Genie Space resource definition, pulled from the live space. |
| `src/*.geniespace.json` | The actual Genie Space content (instructions, SQL examples, tables). |
| `postprocess_generated_yml.py` | Restores `${var.warehouse_id}` / `${workspace.current_user.userName}` references after each pull (bundle generate overwrites them with hardcoded values). |
| `pull_and_sync.sh` | **Command 1.** Pulls the Genie Space and syncs shared folders. Optionally validates. |
| `push_and_deploy.sh` | **Command 2.** Runs bundle checks (and optionally deploys to test), THEN commits and pushes to Git. |
| `sync_shared_folders.sh` | Pulls shared workspace folders INTO this repo (so they get committed/pushed to GitHub) and deploys them out to your own workspace path, based on `folder_sync_config.json`. Called automatically by `pull_and_sync.sh`, but can be run standalone too. |
| `folder_sync_config.json` | The editable list of folders to sync. Add or remove entries here - no script editing needed. |
| `shared_folders/` | Created automatically the first time a folder is synced. This is the actual, version-controlled copy that gets committed and pushed to GitHub. |

## One-time setup

1. Create an empty Git folder in Databricks, linked to your GitHub repo.
2. Open the Web Terminal (via a throwaway notebook -> connect to serverless compute -> terminal icon).
3. `cd` into the Git folder.
4. Paste in `init_genie_bundle.sh` and run:
   ```
   bash init_genie_bundle.sh
   ```
5. Answer the prompts:
   - **Genie Space ID** - from the Genie UI -> About -> Space ID, or the URL.
   - **Bundle name** - a project label, e.g. `my-project-genie-agent`.
   - **Display title** - what shows in the Genie UI.
   - **Resource key** - internal short name; a suggestion is auto-filled from the bundle name, just press Enter to accept it.
   - **Test target?** - whether to also configure a `test` deployment target now.
   - **Deploy dev now?** - whether to immediately create a live dev copy.
   - **Sync folders now?** - whether to run the folder sync immediately.

   The warehouse ID is **auto-detected** from the live Genie Space after
   the first pull - you do not need to look it up yourself.

6. Once it finishes, commit to GitHub via the Git folder UI (Changes tab ->
   commit message -> Commit & Push). This can't be done from the terminal.

### Re-running init_genie_bundle.sh later

You should not need to run this script again for everyday work - use
`pull_and_sync.sh` and `push_and_deploy.sh` instead (see below). But if you
ever do re-run it (e.g. to point the project at a different Genie Space),
it behaves differently the second time:

- If `config.json` already has a `space_id` filled in, the script uses
  `space_id`, `bundle_name`, `title`, `resource_key`, and `test_target`
  straight from that file - it will **not** ask you for the Space ID (or
  any of those) again.
- To reconfigure, just edit `config.json` by hand first (e.g. change
  `space_id` to a different space) and then re-run the script - it picks
  up whatever is in the file.
- It still asks the two action questions each time ("deploy dev now?" and
  "sync folders now?"), since those are one-off actions, not project config.

## Everyday use - three commands

**1. Pull and sync** - whenever the Genie Space is edited in the UI, or you
want to check for updates:

```
bash pull_and_sync.sh                # pull Genie Space + sync shared folders
bash pull_and_sync.sh --validate     # + validate the bundle afterwards
```

**1b. Folders only** - if you just want to refresh shared folders WITHOUT
touching the Genie Space at all:

```
bash sync_shared_folders.sh
```

This never runs `bundle generate`, never touches `databricks.yml` or
`resources/*.yml` - it only pulls/deploys folders. See "Syncing shared
folders on their own" below for details. Push afterwards with
`push_and_deploy.sh`, same as after `pull_and_sync.sh`.

This only updates your local files. Nothing is pushed to Git and nothing is
deployed yet.

**2. Push (and optionally deploy)** - once you're happy with what's in your
files:

```
bash push_and_deploy.sh                                   # validate, commit (default message), push
bash push_and_deploy.sh 'my commit message'               # validate, commit (custom message), push
bash push_and_deploy.sh --deploy-test                     # validate + deploy to test, commit (default message), push
bash push_and_deploy.sh --deploy-test 'my commit message' # validate + deploy to test, commit (custom message), push
```

This runs the bundle checks (and the test deploy, if you asked for one)
*first*, then commits and pushes to Git - with whatever commit message you
give it, or "sync genie space changes" if you don't give one.

**Golden rule:** always run `pull_and_sync.sh` before `push_and_deploy.sh`,
even if you're not sure anything changed - it prevents accidentally
overwriting someone else's UI edit with stale files.

## Syncing shared folders on their own

If you just want to refresh the shared folders without touching the Genie
Space, run:

```
bash sync_shared_folders.sh
```

It reads `folder_sync_config.json`. Each entry has three fields:

- **`master_src`** - the LIVE Workspace path of the shared/master copy (e.g.
  the folder as it exists in the owner's own account). Pulled down into
  `repo_path` on a best-effort basis - only whoever has read access to it
  needs this step to succeed.
- **`repo_path`** - where that content lives INSIDE this Git repo, relative
  to this folder (e.g. `shared_folders/marketing-eda-notebook`). This is
  what actually gets committed and pushed to GitHub - `push_and_deploy.sh`'s
  `git add .` picks it up automatically, no extra step needed.
- **`dest`** - the LIVE Workspace path that `repo_path` gets deployed to for
  whoever is currently running the sync.

`{username}` anywhere in `master_src` or `dest` is replaced with whoever is
currently running the script, so the same config file works for anyone.

Example entry - real usage (one fixed master, per-user destination):
```json
{
  "master_src": "/Workspace/Users/owner@company.com/.assistant/skills/marketing-eda-notebook",
  "repo_path": "shared_folders/marketing-eda-notebook",
  "dest": "/Workspace/Users/{username}/.assistant/skills/marketing-eda-notebook"
}
```

**How the two systems connect:** the folder owner runs `pull_and_sync.sh`,
which calls `sync_shared_folders.sh` and pulls the current content of
`master_src` down into `repo_path` inside this repo. They then run
`push_and_deploy.sh`, which commits and pushes `repo_path` to GitHub along
with the rest of the bundle. Anyone else who `git pull`s this repo already
has those files locally (from GitHub, no live access to `master_src`
needed) - running `sync_shared_folders.sh` for them just deploys whatever
is in `repo_path` out to their own `dest`. This is what makes the shared
folder both version-controlled in Git and immediately usable for everyone.

## config.json reference

```json
{
  "bundle_name": "my-genie-bundle",
  "resource_key": "my_genie_agent",
  "title": "My Genie Agent",
  "space_id": "01f...",
  "warehouse_id": "auto-detected-on-first-run",
  "test_target": true,
  "test_host": "",
  "test_warehouse_id": "auto-detected-on-first-run"
}
```

`warehouse_id` and `test_warehouse_id` are filled in automatically by
`init_genie_bundle.sh` after it pulls the space for the first time - you
never need to look these up or type them in yourself.

Both `pull_and_sync.sh` and `push_and_deploy.sh` read `space_id`,
`resource_key`, and `test_target` directly from this file at run time - to
point the project at a different Space ID or resource key later, edit this
file (and re-run `init_genie_bundle.sh` if you also need `databricks.yml`
regenerated).

## Adding a project to a new/empty Genie Agent later

Just run `init_genie_bundle.sh` again in a different empty Git folder with
a different Space ID - it's fully self-contained and reusable per project.

## Common issues

| Problem | Fix |
|---|---|
| `Error: test: no such target` | You skipped the test-target step during setup, or it failed to write. Re-run `init_genie_bundle.sh` and say yes, or hand-edit `databricks.yml` to add a `test:` block, and set `test_target: true` in `config.json`. |
| "Git CLI not available from terminal" | Normal in the Web Terminal. Commit via the Workspace Git sidebar (Git icon -> Commit & Push), or ask the Databricks Assistant to commit and push. |
| Folder sync "Export failed" | Check the source path is correct and you have read access to it. |
| `Resources:` empty in `bundle summary` | Usually a missing `include: - resources/*.yml` line in `databricks.yml`. |
