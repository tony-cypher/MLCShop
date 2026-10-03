# MLC — Shop

A full-stack ecommerce demo: **React (Vite + TypeScript)** storefront with a **FastAPI (Python)**
API, **Supabase Postgres** for storage and **Resend** for transactional email.

This is a backend rebuild of the original Laravel version: the React app, its structure, markup and
UI are unchanged — only the API was reimplemented in FastAPI. The API keeps the exact same routes,
request payloads and JSON responses, so the storefront needed no logic changes.

The UI covers every feature of the reference design — category pills, price-range slider with
histogram, star-rating filter, brand checklist, delivery options, sale badges, favourite hearts,
featured product card — plus a **test-only checkout**, order history, email confirmation and a
**light/dark theme**.

---

## 1. What's in the box

| Area | Details |
| --- | --- |
| Storefront | React 19, Vite, TypeScript, React Router |
| API | FastAPI, SQLAlchemy 2.0, Pydantic v2, opaque bearer tokens |
| Database | Supabase Postgres (falls back to SQLite locally) |
| Email | Resend (falls back to the log driver in dev) |
| Checkout | Test only — Luhn-checked card, no processor, no charge |
| Auth | Register / login / email confirmation / Google OAuth / favourites / orders |

### Features implemented from the reference image

- Header: logo, search, Orders, Favourites, Cart with live badge, account menu
- Category pills: **All Categories · Deals · Crypto · Fashion · Health & Wellness · Art · Home · Sport · Music · Gaming**
- Price Range card: average price, histogram, dual-thumb slider, Reset
- Star Rating filter ("4 Stars & up"), Brand checklist with marks + *More Brand*, Delivery Options (Standard / Pick Up)
- Product grid with **Top Item** badges, sale strikethrough prices, favourite hearts and a featured
  dark card with floating rating chips
- Extras: sorting toolbar, hover quick-add, product detail with size/colour options and reviews,
  cart, test checkout, order history, favourites page, dark mode

---

## 2. Requirements

- Python **3.11+** (3.12 recommended)
- Node **20+** and npm
- No database or mail credentials are needed for local development

---

## 3. Quick start (SQLite, no keys needed)

```bash
# API
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed                # creates shop.db and seeds the catalogue
uvicorn app.main:app --reload     # http://127.0.0.1:8000

# Storefront (second terminal)
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

Tables are created automatically on start-up (`create_all`) and the Vite dev server proxies
`/api/*` to `http://127.0.0.1:8000`, so no CORS setup is needed in development.

- Interactive API docs: <http://127.0.0.1:8000/docs>
- **Demo account:** `demo@mlc.test` / `password123`
- **Test card:** `4242 4242 4242 4242`, any future expiry, any CVC

`python -m app.seed` and the `RUN_SEED=true` boot flag are both idempotent — every seeder updates
existing rows instead of duplicating them.

---

## 4. Running the tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q
```

33 end-to-end tests cover the catalogue (filters, sorting, pagination, histogram), auth (register,
login, verify, resend, throttling), favourites, checkout (Luhn, expiry, stock, shipping rules) and
the order history. They run against a throwaway SQLite database.

---

## 5. Connecting Supabase Postgres

1. Open your project on [supabase.com](https://supabase.com) → **Project Settings → Database**.
2. Under **Connection string**, choose **URI** (direct connection) and copy the values.
   It looks like:
   `postgresql://postgres:YOUR-PASSWORD@db.abcdefghijklm.supabase.co:5432/postgres`
3. Put them in `backend/.env`:

```env
DB_CONNECTION=pgsql
DB_HOST=db.abcdefghijklm.supabase.co
DB_PORT=5432
DB_DATABASE=postgres
DB_USERNAME=postgres
DB_PASSWORD=YOUR-DATABASE-PASSWORD
DB_SSLMODE=require
```

> **Where do I find each value?**
> - `DB_HOST` — the `db.<project-ref>.supabase.co` part of the URI
> - `DB_PASSWORD` — the database password you chose when creating the project
>   (reset it under *Project Settings → Database → Reset database password*)
> - `DB_SSLMODE=require` — Supabase requires TLS
> - Deploying to Render? Use the **Session pooler** host
>   (`aws-0-<region>.pooler.supabase.com`, user `postgres.<project-ref>`) — the direct
>   `db.<ref>.supabase.co` host is often IPv6-only and unreachable from Render.

Alternatively set a single connection string, which overrides the `DB_*` values:

```env
DATABASE_URL=postgresql://postgres.<ref>:<password>@<pooler-host>:5432/postgres?sslmode=require
```

4. Create the schema and seed the catalogue:

```bash
cd backend
python -m app.seed
```

5. Verify:

```bash
python -c "from app.database import SessionLocal; from app.models import Product; from sqlalchemy import select, func; db=SessionLocal(); print(db.scalar(select(func.count()).select_from(Product)), 'products')"
```

---

## 6. Configuring Email (Gmail SMTP or Resend)
 
Two emails are sent by the app:
 
| Mail | Trigger |
| --- | --- |
| Email confirmation | Registration (and "Resend email" in the header banner) |
| Order confirmation | Successful test checkout |
 
### Option A: Gmail SMTP (Recommended — no domain required, lands in Inbox)
 
1. Enable **2-Step Verification** on your Google Account: <https://myaccount.google.com/security>.
2. Generate an **App Password**: <https://myaccount.google.com/apppasswords> (name it "MLC Shop").
3. Copy the 16-character password generated by Google.
4. Fill in `backend/.env`:
 
```env
MAIL_MAILER=smtp
MAIL_FROM_ADDRESS=your-email@gmail.com
MAIL_FROM_NAME=MLC

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_TLS=true
```
 
### Option B: Resend
 
1. In [Resend](https://resend.com) generate an API key.
2. Fill in `backend/.env`:
 
```env
MAIL_MAILER=resend
RESEND_API_KEY=re_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
MAIL_FROM_ADDRESS=onboarding@resend.dev   # or your verified domain
MAIL_FROM_NAME=MLC
```
 
> When credentials are not set (or with `MAIL_MAILER=log`), every email is written to the application log.

---

## 7. Sign in with Google (Google Cloud Console)

The login and register pages show a **Continue with Google** button. It stays disabled until you
create an OAuth client and paste the credentials into `backend/.env`.

### Create the OAuth client

1. Open <https://console.cloud.google.com> and sign in with your Google account.
2. Create (or select) a project — e.g. **MLC Shop**.
3. **APIs & Services → OAuth consent screen**
   - User type: **External** → **Create**.
   - Fill in an app name and your email; the rest can stay empty.
   - Under **Test users**, add the Gmail address you will sign in with (required while the
     consent screen is in *Testing* mode).
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**
   - Application type: **Web application**.
   - **Authorized redirect URIs**: add both
     `http://localhost:8000/api/auth/google/callback` (local dev) and
     `https://<your-service>.onrender.com/api/auth/google/callback` (production).
   - Create, then copy the **Client ID** and **Client secret**.

### Enable it in the app

5. In `backend/.env`:

```env
GOOGLE_CLIENT_ID=1234567890-xxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxx
# GOOGLE_REDIRECT_URI is OPTIONAL — leave it blank to derive the callback below.
```

6. Restart the API. Reload <http://localhost:5173/login> — the Google button is now active, and
   `GET /api/auth/google/config` returns `{"data":{"enabled":true}}`.

> **How it works:** `/api/auth/google/redirect` sends the user to Google; the callback finds or
> creates the user by email (stamping `google_id` and `avatar_url`), issues a bearer token and
> redirects to `/auth/google/callback#token=…` on the storefront. Signing in with Google also marks
> the address as verified, so no confirmation email is sent.

### URLs are detected automatically (no localhost in production)

The callback URL and the final redirect are resolved from the environment and the request, so you
never hard-code a host:

1. **Callback (redirect_uri)** — `GOOGLE_REDIRECT_URI` if set, otherwise
   `<APP_URL>/api/auth/google/callback`; on Render `APP_URL` defaults to the service's
   `RENDER_EXTERNAL_URL` (e.g. `https://mlcshop.onrender.com`), and locally it falls back to the
   host you are browsing.
2. **Return to the storefront** — the SPA sends its own origin when it starts the flow
   (`/api/auth/google/redirect?origin=…`); the server keeps it in the OAuth `state` and returns the
   browser there. `FRONTEND_URL` is the fallback when no origin is available.

**In production you only need to set:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and
`FRONTEND_URL` (your Vercel URL). The callback is derived automatically — leave `APP_URL` and
`GOOGLE_REDIRECT_URI` blank unless you use a custom domain.

The value used for the callback must appear **exactly** in the OAuth client's *Authorized redirect
URIs*. A `redirect_uri_mismatch` in the API logs is the tell-tale sign it does not match.

---

## 8. Project structure

```
backend/                  FastAPI service
├─ app/
│  ├─ main.py                 app factory, CORS, error handlers, health check
│  ├─ config.py               settings (DB_*, MAILGUN_*, GOOGLE_*, FRONTEND_URL)
│  ├─ database.py             engine + session factory (Postgres or SQLite)
│  ├─ models.py               SQLAlchemy models (users, catalogue, orders, favourites)
│  ├─ schemas.py              Pydantic request payloads
│  ├─ serializers.py          Laravel-compatible JSON (string decimals, ISO dates)
│  ├─ security.py             bcrypt hashing + opaque token helpers
│  ├─ deps.py                 bearer-token auth dependencies
│  ├─ ratelimit.py            auth 10/min, checkout 8/min per IP
│  ├─ mailer.py               Mailgun sender + Jinja email templates
│  ├─ google_oauth.py         Google OAuth 2.0 flow
│  ├─ urls.py                 env/request-aware callback + frontend URL resolution
│  ├─ validation.py           pydantic → Laravel-style error maps
│  ├─ seed.py / seed_data.py  idempotent seeders (33 products, 10 brands, 8 categories)
│  ├─ routers/                catalog, auth, checkout, favorites, orders
│  └─ templates/mail/         confirmation + order emails
├─ tests/                     pytest suite (42 tests)
├─ scripts/                   fetch_product_images.py (one-time image downloader)
├─ requirements.txt           runtime dependencies
└─ .env.example               every environment variable, documented

frontend/                 React storefront (unchanged)
├─ src/components          Header, CategoryPills, Sidebar, ProductCard, Stars…
├─ src/context             Theme, Auth, Cart, Favorites, Toast
├─ src/pages               Shop, Product, Cart, Checkout, Orders, Favourites, Login, Register, Verify
├─ vercel.json             SPA rewrites + cache headers
└─ src/index.css           design tokens (light + dark) and all styling
```

Repo root: `render.yaml` (Render blueprint), `.gitignore`, `README.md`, `DEPLOY.md`.

### API endpoints

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/products` | `search, category, brands[], min_price, max_price, min_rating, delivery, deals, sort, per_page, page` |
| GET | `/api/products/{slug}` | product + reviews + related |
| GET | `/api/categories`, `/api/brands` | filter data |
| POST | `/api/auth/register` | sends the confirmation email |
| POST | `/api/auth/login` | returns a bearer token |
| GET | `/api/auth/google/config` | `{ enabled }` — drives the Google button state |
| GET | `/api/auth/google/redirect` | starts the Google OAuth flow |
| GET | `/api/auth/google/callback` | Google redirect target; hands the token back to the SPA |
| POST | `/api/auth/verify-email` | `{ token }` |
| POST | `/api/auth/resend-verification` | authenticated, throttled |
| GET/POST | `/api/auth/me`, `/api/auth/logout` | authenticated |
| POST | `/api/checkout` | test order + confirmation email |
| GET | `/api/orders`, `/api/orders/{reference}` | authenticated |
| GET/POST/DELETE | `/api/favorites` | authenticated |
| GET | `/up` | health check (returns `OK`) |

Errors answer in the shape the storefront expects:
`422 {"message": "...", "errors": {"payment.card_number": ["..."]}}`.

### Product images

Products use real photos, self-hosted in `frontend/public/img/products/` (one ~10–85 KB JPEG per
product, ~1.2 MB total). They are served same-origin by Vite/the static build and lazy-loaded, so
the catalogue stays fast with no external CDN calls at runtime.

- Seeding assigns `/img/products/<slug>.jpg` automatically.
- The one-time downloader script fetches freely-licensed photos from the
  [Openverse API](https://api.openverse.org): `python backend/scripts/fetch_product_images.py`
  (idempotent, respects the anonymous rate limit).
- `image_url` is snapshotted onto `order_items` at checkout, so order history and the
  confirmation email keep showing the photo even if a product changes later.
- Emoji remain as a fallback anywhere `image_url` is missing.

---

## 9. Deploying to production (Render + Vercel)

| Piece | Host | Notes |
| --- | --- | --- |
| `frontend/` — React storefront | **Vercel** | static build (`npm run build` → `dist`) |
| `backend/` — FastAPI service | **Render** | native Python runtime, talks to Supabase Postgres |
| Database | **Supabase** | already live — no new DB needed |
| Email | **Resend** | or `MAIL_MAILER=log` to test in Render logs |

All deployment files are already in the repo: `render.yaml` (blueprint), `frontend/vercel.json`,
`backend/.env.production.example`, `frontend/.env.example`. See **`DEPLOY.md`** for the
step-by-step runbook.

### 0. Push the repo to GitHub

```bash
git add -A
git commit -m "MLC shop — FastAPI backend + React storefront"
git remote add origin https://github.com/<you>/mlc-shop.git
git push -u origin main
```

### 1. Backend → Render

1. [render.com](https://dashboard.render.com) → **New + → Blueprint** → connect the GitHub repo.
   Render reads `render.yaml` and creates the **mlcshop** web service (Python, free plan,
   root directory `backend`, health check `/up`).
2. Fill the `sync: false` values (Render asks during setup, or set them later under
   **Environment**). Copy from `backend/.env.production.example`:

   | Key | Value |
   | --- | --- |
   | `FRONTEND_URL` | your Vercel URL, e.g. `https://your-app.vercel.app` (**required**) |
   | `DB_HOST` / `DB_USERNAME` / `DB_PASSWORD` | from Supabase (**Connect → Session pooler**) |
   | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | only to enable Google sign-in |
   | `APP_URL` | optional — blank auto-detects from `RENDER_EXTERNAL_URL` |
   | `CORS_ALLOWED_ORIGINS` | leave empty unless you add extra domains |
3. **Create Web Service.** On boot the service creates any missing tables (retrying 5× if the
   database is not reachable yet) and then serves on Render's `$PORT`.
4. Seed the catalogue once: set **`RUN_SEED=true`** → **Manual Deploy → Deploy latest commit**
   → watch the logs for the seed line → set `RUN_SEED=false` again.
5. Verify: open `https://mlcshop.onrender.com/up` → “OK”, and `/api/products` → JSON.

> **Free tier notes:** the service sleeps after ~15 min idle (first request after that takes
> ~30–60 s) and has no shell — use `RUN_SEED` and env vars instead of a one-off command.
> Deploy logs live in the **Events**/**Logs** tabs.

### 2. Frontend → Vercel

1. [vercel.com/new](https://vercel.com/new) → **Import** the same GitHub repo.
2. Configure the project:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite (auto-detected) — build `npm run build`, output `dist`
   - **Environment Variables:** `VITE_API_URL` = `https://mlcshop.onrender.com/api`
     (your Render URL **+ `/api` suffix**)
3. **Deploy.** Vercel runs `npm ci && npm run build` and serves the SPA — the `vercel.json`
   rewrite keeps deep links like `/product/…` working.

CLI alternative: `cd frontend && npm i -g vercel && vercel --prod`.

### 3. Wire the two together (do this once URLs exist)

| Where | Change |
| --- | --- |
| Render → `FRONTEND_URL` | set to the Vercel URL → **Manual Deploy** (drives email links + CORS + Google callback) |
| Vercel → `VITE_API_URL` | already set in step 2 → every change here needs a **redeploy** (Vite bakes it at build time) |
| Google Cloud Console | add `https://<service>.onrender.com/api/auth/google/callback` to the OAuth client's **Authorized redirect URIs** — the API derives the same value automatically, so `GOOGLE_REDIRECT_URI` is optional |
| Resend | set `MAIL_MAILER=resend` + `RESEND_API_KEY` on Render when ready to send real email |
 
 Order of operations for a clean first rollout: **push → Render deploy → get API URL → Vercel
 deploy with `VITE_API_URL` → get Vercel URL → back to Render, set `FRONTEND_URL` (and, if using
 Google sign-in, register the callback in the Cloud Console) → redeploy Render.**
 
 ### Production checklist
 
 - [ ] `/up` returns “OK” and `/api/products` returns JSON from the Render URL
 - [ ] Storefront loads and the catalogue shows products (VITE_API_URL correct)
 - [ ] Register/login works (check Render Logs if requests fail — usually CORS = wrong `FRONTEND_URL`)
 - [ ] `APP_ENV=production`, `APP_DEBUG=false`, `RUN_SEED=false`
 - [ ] Test checkout places an order and (with Resend) the confirmation email arrives
 - [ ] Google sign-in works in production

---

## 10. Notes & troubleshooting

- **Dark mode** follows the OS on first visit and is remembered in `localStorage`.
- **Checkout is simulated.** Card numbers are validated with the Luhn algorithm and a test card is
  required, but nothing is ever charged and no card data leaves the app.
- **The API uses opaque bearer tokens** (not JWTs): the plaintext is shown once and only a SHA-256
  digest is stored, so `Authorization: Bearer <token>` works exactly like it did with Sanctum.
- **`too many requests` from `/api/auth/*` or `/api/checkout`** → the per-IP throttle
  (10/min and 8/min). Wait a minute, or raise the limits in `app/ratelimit.py`.
- **Talking to Postgres fails with SSL errors** → keep `DB_SSLMODE=require`; if your password has
  special characters and you use `DATABASE_URL`, URL-encode them.
- **Google sign-in fails after deploy (redirect lands on `/login?error=google`)** → check the Render
  logs: the API prints the exact callback URL and Google's response. `redirect_uri_mismatch` means
  that URL is missing from the OAuth client's *Authorized redirect URIs* — add it. Any `localhost`
  in the printed URL means a stale `APP_URL` / `GOOGLE_REDIRECT_URI` is set in the Render dashboard;
  clear it so the value is auto-detected from `RENDER_EXTERNAL_URL`.
- **Users land on the wrong site after Google sign-in** → set `FRONTEND_URL` to your Vercel URL.
  The SPA's own origin is trusted automatically, so a leftover `localhost` is tolerated; a wrong
  custom domain is not.
- **Frontend can't reach the API** → make sure `uvicorn app.main:app --reload` is running on port
  8000; the Vite proxy target lives in `frontend/vite.config.ts`.
- **Port already in use** → `uvicorn app.main:app --port 8001` and update the proxy target.
- **Rate limiting is in-process** — fine for a single Render instance; move it to Redis if you
  scale horizontally.
