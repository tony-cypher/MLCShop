# Deployment Runbook — Render (API) + Vercel (Storefront)

Operational checklist for deploying this repo. The README (§9) explains the background;
this file is the step-by-step you follow on deploy day.

---

## 0. What was verified (2026-10-02)

- The FastAPI app was booted with `uvicorn app.main:app` (no `.env`, env-vars only) and served
  `/up` → `OK`, `/api/products` → JSON with Laravel-compatible payloads, `/api/auth/login` →
  a bearer token, and a correct CORS preflight for the storefront origin.
- The full storefront was exercised against the live API: catalogue grid, filters/sidebar,
  product detail with reviews and related items, login, add-to-cart, cart totals and a complete
  test checkout — the order then appeared in **Orders** with status `confirmed`.
- `python -m pytest -q` → **42 passed** (catalogue, auth, favourites, checkout, orders,
  rate limiting, dynamic OAuth URL resolution).
- `npm run build` (tsc + Vite) → clean production build.
- The seeded catalogue reproduces the original data exactly: 8 categories, 10 brands,
  33 products, 19 reviews, demo user, and every product slug matches its image file.

---

## 1. Prerequisites

- Repo pushed to GitHub (`main`).
- Supabase Postgres credentials (Project Settings → Database; prefer the **session pooler**
  host + port 5432 from Render).
- The frontend and backend deploy from the **same repo**: `frontend/` on Vercel,
  `backend/` on Render.

---

## 2. Backend → Render (native Python runtime)

1. Render dashboard → **New + → Blueprint** → pick the repo. Render reads `render.yaml`
   (service `mlcshop`, root directory `backend`, health check `/up`,
   start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
2. Fill the `sync: false` env vars:

   | Key | Value |
   | --- | --- |
   | `FRONTEND_URL` | your Vercel URL (set after step 3; update + redeploy later) — **required** |
   | `DB_HOST` / `DB_USERNAME` / `DB_PASSWORD` | from Supabase (session pooler) |
   | `RESEND_API_KEY` | from Resend (resend.com) when switching mail on |
   | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | only for Google sign-in |
   | `APP_URL` | **optional** — blank auto-detects `RENDER_EXTERNAL_URL`; set only for a custom domain |
   | `GOOGLE_REDIRECT_URI` | **optional** — blank derives `<APP_URL>/api/auth/google/callback` |
   | `CORS_ALLOWED_ORIGINS` | leave empty unless you add extra domains |

   Defaults already set by the blueprint: `DB_CONNECTION=pgsql`, `DB_PORT=5432`,
   `DB_SSLMODE=require`, `MAIL_MAILER=log`, `RUN_SEED=false`, `PYTHON_VERSION=3.12.6`.
3. **First deploy**: on boot the service creates any missing tables (retrying 5× with backoff) and
   then serves on `$PORT`.
4. **Seed once**: set `RUN_SEED=true` → **Manual Deploy → Deploy latest commit** → watch the logs
   for `Seeding complete.` → set `RUN_SEED=false` again. Repeat any time you add catalogue rows.
5. Verify: `https://<service>.onrender.com/up` → `OK`; `/api/products` → JSON;
   `/docs` → interactive API docs.

Free tier: sleeps after ~15 min idle (first request ~30–60 s); no shell — use env vars +
`RUN_SEED` instead of running one-off commands.

---

## 3. Frontend → Vercel

1. vercel.com/new → import the same repo.
2. **Root Directory:** `frontend` · Framework preset: Vite (build `npm run build` → `dist`).
3. **Environment variable:** `VITE_API_URL = https://<your-service>.onrender.com/api`
   (must include the `/api` suffix — Vite bakes it in at build time, so any change needs a
   redeploy).
4. Deploy. `frontend/vercel.json` keeps SPA deep links working.

> Do **not** leave `VITE_API_URL` set-but-empty anywhere: the app falls back to `/api` only
> when the variable is *unset* (`frontend/src/lib/api.ts`).

---

## 4. Wire the two together (once both URLs exist)

| Where | Change |
| --- | --- |
| Render → `FRONTEND_URL` | set to the Vercel URL → Manual Deploy (drives email links, CORS and the Google callback) |
| Google Cloud Console | add `https://<service>.onrender.com/api/auth/google/callback` to the OAuth client's **Authorized redirect URIs**. The API derives the identical value from `RENDER_EXTERNAL_URL`, so no `GOOGLE_REDIRECT_URI` is required — but if you do set it, it must match exactly |
| Resend | set `MAIL_MAILER=resend` + `RESEND_API_KEY` on Render when ready for real email |

---

## 5. Post-deploy checklist

- [ ] `/up` → `OK`, `/api/products` → JSON (Render URL)
- [ ] Storefront loads products (correct `VITE_API_URL`)
- [ ] Register / login works (CORS errors usually mean a wrong `FRONTEND_URL`)
- [ ] `APP_ENV=production`, `APP_DEBUG=false`, `RUN_SEED=false`
- [ ] Test checkout places an order and it shows up under **Orders** for the signed-in user
      (email lands in Render logs while `MAIL_MAILER=log`)
- [ ] Google sign-in works (if configured)

---

## 6. Rolling back / re-seeding

- **Bad deploy?** Render → **Deploys** tab → *Rollback* to the previous successful deploy.
- **Re-seed after a catalogue change?** `RUN_SEED=true` + Manual Deploy, then back to `false`.
  The seeders are idempotent, so they update existing rows rather than duplicating them.
- **Schema changes?** The service creates missing tables on boot, but it does not alter existing
  ones. For a real migration story, add Alembic (`alembic init`) and run `alembic upgrade head`
  in the Render start command before `uvicorn`.
