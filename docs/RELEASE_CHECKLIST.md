# Release Checklist

Use this checklist for every production release of `pplcheckride.com`.

## 1) Preflight (local repo)

- [ ] Open terminal in project:
      `cd "/Users/paramvir/Documents/Aviation:Flying/ppl oral exam prep"`
- [ ] Confirm repo is clean:
      `git status --short`
- [ ] Pull latest remote changes (if any):
      `git pull --rebase origin main`

## 2) Bump app version footer

- [ ] Update `APP_VERSION` in `index.html`:
      `./scripts/update_app_version.sh index.html`
- [ ] Commit version bump:
      `git add index.html`
      `git commit -m "chore: bump app version for release"`
- [ ] Push:
      `git push origin main`

## 3) Cloud Sync backend sanity

- [ ] Ensure function config files still contain:
      `verify_jwt = false`
      - `supabase/functions/license_exchange/config.toml`
      - `supabase/functions/progress_sync/config.toml`
      - `supabase/functions/mock_results/config.toml`
- [ ] Deploy functions when backend changed:
      `supabase functions deploy license_exchange --no-verify-jwt`
      `supabase functions deploy progress_sync --no-verify-jwt`
      `supabase functions deploy mock_results --no-verify-jwt`
- [ ] Run smoke script:
      `PUBLISHABLE_KEY="sb_publishable_..." bash scripts/deploy_and_smoke_test.sh`

## 4) Frontend QA (manual)

- [ ] Serve locally:
      `python3 -m http.server 8000`
- [ ] Open:
      `http://localhost:8000/index.html`
- [ ] Hard refresh with cache disabled.
- [ ] Confirm footer shows expected version.
- [ ] Confirm mode cards are keyboard operable:
      - Tab to each mode card
      - Press Enter/Space to launch
- [ ] Confirm Cloud Sync status row is visible on main screen.
- [ ] Test sync flow:
      - Connect Cloud Sync (`PPL-TEST-001`)
      - Rate 2-3 questions
      - Refresh and confirm progress persists
- [ ] Confirm `Sync Now` and `View History` buttons enable after connect.
- [ ] Run one mock checkride and verify row appears in
      `public.mock_checkride_results`.
- [ ] Verify trial lock behavior (while not connected/unlocked):
      - Only curated 10-question pool is used in Study/Random/Review
      - Mock Checkride runs `10 questions / 10 minutes`
      - Trial upsell banner/CTA is visible
- [ ] Verify unlock transition behavior:
      - Connect valid license key
      - Confirm full 250-question access appears without hard reload
      - Confirm prior hidden progress reappears in stats/insights

## 5) Deploy to production

If Netlify is linked to GitHub auto-deploy:
- [ ] Verify latest deploy came from `main`.

If Netlify uses manual upload:
- [ ] Build minimal deploy folder:
      `rm -rf netlify-deploy && mkdir netlify-deploy && cp index.html netlify-deploy/`
- [ ] In Netlify `Production deploys`, upload folder:
      `netlify-deploy`
- [ ] Open `https://pplcheckride.com` and hard refresh.
- [ ] Confirm footer version matches local `index.html`.

## 6) Tag release (rollback point)

- [ ] Create annotated tag:
      `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- [ ] Push tag:
      `git push origin vX.Y.Z`

## 7) Post-release verification

- [ ] Check homepage loads with no console errors.
- [ ] Check Cloud Sync connect/sync works in production.
- [ ] Check Cloud Sync status text updates after sync and shows recent timestamp.
- [ ] Check mock history is reachable from UI and displays recent attempts.
- [ ] Check trial mode copy and CTA are visible for non-unlocked sessions.
- [ ] Check one new progress update appears in `public.user_progress`.
- [ ] Check one new mock result appears in `public.mock_checkride_results`.
