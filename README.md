# PPL Oral Exam Prep

Production web app and Supabase Edge Functions for `pplcheckride.com`.

## Repo layout

- `index.html` - production web app entrypoint
- `supabase/functions/` - Edge Functions (`license_exchange`, `progress_sync`, `mock_results`)
- `scripts/` - operational scripts
  - `deploy_and_smoke_test.sh`
  - `update_app_version.sh`
- `docs/` - guides and project notes
- `db/` - current SQL schema artifacts
- `archive/` - legacy/backup files kept for reference
- `tools/content-gen/` - content-generation tooling and source materials

## Common commands

From repo root:

```sh
python3 -m http.server 8000
```

```sh
./scripts/update_app_version.sh index.html
```

```sh
PUBLISHABLE_KEY="sb_publishable_..." bash scripts/deploy_and_smoke_test.sh
```

