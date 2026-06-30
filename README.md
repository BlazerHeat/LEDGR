# LEDGR API

Backend for **LEDGR** — a unified personal-finance, bill-splitting and AI-analytics platform
(CSCI 5709, Assignment 2). Built with **FastAPI** + **Prisma (Client Python)** on
**Supabase Postgres**.

This deployment implements the **Personal Ledger** feature (transactions) and the supporting
**authentication** endpoints. The full API surface for all three core features is specified in
[`../docs/LEDGR-API-Design.md`](../docs/LEDGR-API-Design.md).

> **Live API:** https://ledgr-api-w93g.onrender.com — interactive docs at
> [`/docs`](https://ledgr-api-w93g.onrender.com/docs), health at
> [`/healthz`](https://ledgr-api-w93g.onrender.com/healthz).
> Hosted on Render's free tier, so the first request after ~15 min idle takes 30–50s to wake.

## Implemented endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET`  | `/healthz` | – | Health check |
| `POST` | `/api/v1/auth/register` | – | Create account + seed default categories, returns JWT |
| `POST` | `/api/v1/auth/login` | – | Authenticate, returns JWT access + refresh |
| `POST` | `/api/v1/auth/refresh` | – | Rotate refresh token |
| `POST` | `/api/v1/auth/logout` | – | Revoke refresh token |
| `GET`  | `/api/v1/auth/me` | JWT | Current user |
| `GET`  | `/api/v1/categories` | JWT | List the user's categories |
| `POST` | `/api/v1/categories` | JWT | Create a category |
| **`POST`** | **`/api/v1/transactions`** | **JWT** | **Graded endpoint 1 — create a transaction** |
| **`GET`**  | **`/api/v1/transactions`** | **JWT** | **Graded endpoint 2 — list / filter / search / paginate** |

Interactive OpenAPI docs are served at `/docs`.

**Demo login:** `vatsal.ghoghari@dal.ca` / `Ledgr@2026`

## Run locally

```bash
cd ledgr-api
python -m pip install -r requirements.txt

cp .env.example .env          # then fill in DATABASE_URL, DIRECT_URL, JWT_SECRET

python -m prisma generate     # generate the Prisma client
python -m prisma db push      # create tables in the database
python scripts/seed.py        # load demo data + (re)write db/seed.sql and db/seed.json

uvicorn app.main:app --reload # http://127.0.0.1:8000  (docs at /docs)
```

## Project layout

```
app/
  main.py            FastAPI app, CORS, exception handlers, router wiring
  core/
    config.py        settings from env (.env)
    db.py            shared Prisma client
    security.py      bcrypt hashing + JWT create/verify
    deps.py          deny-by-default JWT dependency + RBAC
    errors.py        consistent { error: {code,message,details} } envelope
    defaults.py      starter categories
  schemas/           Pydantic request/response models
  routers/           auth, categories, transactions
prisma/schema.prisma data model for ALL entities (Prisma Client Python)
scripts/seed.py      seeds the DB and exports the DB source files
db/                  schema.sql (DDL) · seed.sql (data) · seed.json (data)
postman/             importable Postman collection
render.yaml          Render Blueprint
```

## Security model (summary)

- **Authentication** — bcrypt password hashing; stateless JWT access tokens (30 min) +
  rotating, hashed refresh tokens (14 days).
- **Authorization** — every protected route depends on `get_current_user` (deny-by-default).
  Queries are always scoped to the authenticated user's id, so cross-user access is impossible;
  unauthorised object access returns `404` rather than `403` to avoid resource enumeration.
- **Validation** — Pydantic models validate every request body and query parameter; failures
  return `422` with a per-field `details` array.
- **Injection** — Prisma issues parameterised queries for every operation; no raw SQL is built
  from user input.

## Deploy to Render

1. Push this folder to a GitHub repo.
2. On Render: **New + → Blueprint**, select the repo (`render.yaml` is detected).
   If `ledgr-api` is a subfolder, set **Root Directory** to `ledgr-api`.
3. Add the `DATABASE_URL` and `DIRECT_URL` environment variables (Supabase pooler URLs).
   `JWT_SECRET` is generated automatically.
4. Deploy. Render runs
   `pip install -r requirements.txt && python -m prisma py fetch && python -m prisma generate`,
   then `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Health check path: `/healthz`.

### Prisma engine binary on Render (important)

The Prisma query-engine binary downloaded during build must still be present at runtime. Render's
default cache (`~/.cache` = `/opt/render/.cache`) is **not** carried into the run container, which
causes `prisma.engine.errors.BinaryNotFoundError` at startup. The Blueprint fixes this by setting
`PRISMA_BINARY_CACHE_DIR=/opt/render/project/src/.prisma-engine` (a path inside the persisted
project directory) and running `python -m prisma py fetch` in the build command.

If you configured the service **manually** instead of via the Blueprint, replicate both:
* **Build Command:** `pip install -r requirements.txt && python -m prisma py fetch && python -m prisma generate`
* **Environment variable:** `PRISMA_BINARY_CACHE_DIR` = `/opt/render/project/src/.prisma-engine`

## DB source files

- [`db/schema.sql`](db/schema.sql) — full DDL (tables, enums, indexes, foreign keys).
- [`db/seed.sql`](db/seed.sql) — `INSERT` statements for the demo data.
- [`db/seed.json`](db/seed.json) — the same demo data as JSON.
