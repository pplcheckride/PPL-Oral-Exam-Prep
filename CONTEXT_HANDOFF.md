# Context Handoff (End-to-End)

Last updated: 2026-02-11 (local)
Project path: `/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep`

## 1) Current Git state

- Branch: `main`
- Working tree: clean
- Latest commits:
  - `d9087c2` `chore: auto-deploy smoke test`
  - `cafc1fd` `chore: reorganize repo structure (docs/tools/db/archive)`
  - `7ad0106` `chore: ignore local netlify deploy bundle`
  - `790cdd4` `docs: add release checklist`
  - `8789073` `chore: bump app version for netlify deploy`
  - `dac741b` `fix: make progress sync schema-compatible and improve sync reset UX`
- Tags:
  - `v1.0.2-sync-stable` (on `8789073`)
  - `v1.0.1-sync-stable` (on `dac741b`)
- Remote: `origin https://github.com/pplcheckride/PPL-Oral-Exam-Prep.git`
- User confirmed repo is now on GitHub and auto-deploy pipeline is working.

## 2) Production/deploy state

- Domain: `https://pplcheckride.com` (Netlify)
- Netlify site is linked to GitHub repo for continuous deployment.
- User confirmed deploy works and live site loads latest app behavior.

## 3) App/runtime status

- Main app entrypoint: `/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep/index.html`
- Footer version currently in code:
  - `const APP_VERSION = 'v2026.02.11+dac741b';` (`index.html:2472`)
- Cloud Sync UX additions are present:
  - `⚙️ Cloud Sync Setup`
  - `🧹 Reset Sync + Local Data`
  - detailed sync error formatting (`formatCloudSyncError`)
- Reset behavior:
  - `resetCloudSyncSettings()` now clears sync credentials and local progress.
  - It does **not** delete Supabase server-side rows (intentional).

## 4) Supabase edge functions status

- Functions directory: `/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep/supabase/functions`
- `verify_jwt = false` is set for:
  - `license_exchange`
  - `progress_sync`
  - `mock_results`
- `progress_sync` includes schema compatibility logic:
  - Accepts app ratings (`correct/unsure/wrong`)
  - Detects legacy constraint failures
  - Retries writes as legacy (`mastered/review/practice`)
  - Maps legacy rows back to app ratings on reads

## 5) Root-cause history (important)

Main blockers that were fixed:

1. **Authorization parsing bug**
- `Bearer\\s+` regex in function code caused false `"Missing Authorization"`.
- Fixed to `Bearer\s+`.

2. **JWT gateway mismatch**
- Needed `--no-verify-jwt` / `verify_jwt=false` because app uses custom license JWT, not Supabase Auth JWT.

3. **Rating schema mismatch**
- DB/user_progress in some environments enforced legacy enum values.
- App used new enum values.
- Fixed with compatibility in `progress_sync`.

4. **Wrong project edited earlier**
- At one point edits were made in `/Users/paramvir/Documents/New project` instead of this repo.
- Current repo now contains correct fixes and is source of truth.

## 6) Repo organization status

Current structure:

- `/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep/index.html` (runtime app)
- `/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep/supabase/functions` (runtime backend functions)
- `/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep/scripts` (ops scripts)
  - `deploy_and_smoke_test.sh`
  - `update_app_version.sh`
- `/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep/docs` (docs/checklists)
- `/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep/db` (current schema)
- `/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep/archive` (old schema + backup files)
- `/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep/tools/content-gen` (content generation assets)

Ignored local artifacts:

- `.DS_Store`
- `supabase/.temp/`
- `netlify-deploy/`

## 7) Operational commands

From `/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep`:

```sh
python3 -m http.server 8000
```

```sh
./scripts/update_app_version.sh index.html
```

```sh
PUBLISHABLE_KEY="sb_publishable_..." bash scripts/deploy_and_smoke_test.sh
```

```sh
supabase functions deploy progress_sync --no-verify-jwt
```

## 8) Known good verification

User confirmed:

- Cloud Sync connect succeeds.
- Progress persists after refresh.
- Mock results write into `public.mock_checkride_results`.
- Netlify + GitHub auto-deploy works.

## 9) Suggested next steps for new conversation

1. Add branch protection + PR workflow on GitHub (`main` protected).
2. Add a server-side delete endpoint for optional "hard reset cloud data".
3. Automate release flow (version bump + smoke + tag) via script or CI.

## 10) UX + Trial rollout status (implemented)

Recent app updates now in `index.html`:

- **P1/P2 UX stabilization**
  - Mode cards are semantic `<button>` elements (keyboard operable).
  - Focus-visible styles added for keyboard navigation.
  - Cloud Sync status row added on main screen:
    - connection state
    - last sync timestamp
    - `Sync Now` action
    - `View History` action
  - Cloud copy updated to consistently reference:
    - `🧹 Reset Sync + Local Data`
  - Debounced progress push added to reduce perceived sync lag (plus existing interval/unload fallback).
  - Dynamic stat grids in mock results and insights now use responsive classes (mobile-safe).

- **Free trial mode (10 questions)**
  - Access model:
    - unlocked = existing stored license session (`token` + `license hash`)
    - trial = not unlocked
  - Curated trial pool:
    - `Q1,Q3,Q12,Q25,Q48,Q77,Q101,Q134,Q182,Q229`
  - All modes work in trial but are restricted to trial pool.
  - Trial mock checkride behavior:
    - `10 questions / 10 minutes`
  - Unlocked mock checkride remains:
    - `30 questions / 30 minutes`
  - Trial upsell indicators are shown in landing/mode/results UI.
  - Historical progress is retained; non-trial content is hidden while locked and reappears after unlock.

---

## Paste-this prompt for next chat

```text
Use /Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep as the source-of-truth repo.
Read CONTEXT_HANDOFF.md first and continue from current state without redoing prior fixes.
```
