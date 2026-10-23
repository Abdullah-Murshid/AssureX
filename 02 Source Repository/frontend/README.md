# AssureX Claim Engine — Frontend

React 19 + Vite 8 + Tailwind CSS v4 single-page application for the AssureX
Claim Engine REST API. It implements the full warranty workflow: authentication,
products and warranties, evidence vault, claim intake with dual-model
adjudication, claim dossiers, reviewer decisions, warranty alerts and the
administration console.

The design system follows the iWarranty tokens in
[`design_system_tokens.md`](./design_system_tokens.md): slate-950 canvas,
slate-800 surfaces, indigo-500 brand, emerald/amber/rose status colours, Inter
and glass borders.

## Stack

| Concern | Choice |
| --- | --- |
| UI | React 19, React Router 7 |
| Build | Vite 8 |
| Styling | Tailwind CSS v4 (`@theme` tokens in `src/index.css`) |
| State | Zustand (`auth`, `toast`) |
| HTTP | Axios with bearer-token interceptor |
| Tests | Vitest + Testing Library, Playwright E2E (`playwright-core`) |
| Lint | Oxlint |

## Getting started

```bash
npm install

# terminal 1 — backend (repository root)
uv run python backend/manage.py runserver 8011

# terminal 2 — frontend
npm run dev            # http://127.0.0.1:5173
```

Vite proxies `/api` to `http://127.0.0.1:8011`; override with
`VITE_API_TARGET=http://host:port` when the API runs elsewhere.

Demo accounts: `customer@assurex.com / customer123`,
`reviewer@assurex.com / reviewer123`, `admin@assurex.com / admin123`.

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Dev server with HMR on :5173 |
| `npm run build` | Production bundle in `dist/` |
| `npm run preview` | Serve the production bundle |
| `npm run lint` | Oxlint |
| `npm test` | Vitest unit/contract tests |
| `npm run e2e` | Playwright browser smoke test (needs dev server :5173) |

## Structure

```
src/
  api/            axios client, endpoint map (contract-tested against openapi.json)
  store/          zustand auth + toast stores
  lib/            constants, formatters, class helper
  components/
    ui/           Button, Card, Fields, Modal, Table, Badge, StatCard, …
    layout/       AppShell (sidebar/topbar), ProtectedRoute, AuthLayout
    claims/       badges, model comparison, reviewer override modal
  pages/          Login, Register, Dashboard, Products, ProductDetail,
                  ProductNew, Documents, Claims, ClaimNew (wizard),
                  ClaimDetail (dossier), ReviewQueue, Admin, Alerts,
                  Repairs, Profile, NotFound
e2e/              Playwright smoke script + screenshots (gitignored)
```

## API contract

`openapi.json` is the Django Ninja schema exported from the backend. Every
path used by `src/api/endpoints.js` is asserted against it in
`src/api/__tests__/contract.test.js`, so the UI cannot drift from the API.

Authentication is a signed bearer token stored in `localStorage`; a 401 clears
it and routes back to `/login`. Role-based routes: `/review` (reviewer/admin)
and `/admin` (admin) are guarded by `ProtectedRoute`.

## Routes

| Route | Page |
| --- | --- |
| `/login`, `/register` | Authentication |
| `/` | Dashboard (stats, recent claims, alerts) |
| `/products`, `/products/new`, `/products/:id` | Products & warranty detail |
| `/documents` | Evidence vault with upload/verify/replace/delete |
| `/claims`, `/claims/new`, `/claims/:id` | Claims, 4-step intake wizard, dossier |
| `/alerts` | Warranty alerts with dismiss |
| `/repairs` | Repair history |
| `/review` | Reviewer queue + decisions |
| `/admin` | Analytics, policies, audit log, settings |
| `/profile` | Profile & password |

## Tests

```bash
npm test       # 24 unit/contract tests
npm run e2e    # 23 browser checks (login → claim submission → admin)
```

The E2E suite drives Chrome/Edge headlessly through the complete flow:
customer login, inline product registration, claim submission through both ML
models, dossier rendering, reviewer queue modal, and all admin tabs. It fails
on any console or page error. Screenshots are written to `e2e/screenshots/`.

Set `BROWSER_PATH` to use a different Chromium executable and
`E2E_BASE_URL` to point at another dev server.

## Design system

The UI follows the tokens extracted from iwarranty.ai and documented in
[`DESIGN_TOKENS.md`](./DESIGN_TOKENS.md): warm white canvas, deep green brand,
DM Serif Display headlines, DM Sans UI text and JetBrains Mono for data.
Tokens live in `src/index.css` as Tailwind v4 `@theme` variables:

```css
--color-background: #fafaf8;   /* canvas */
--color-surface: #ffffff;      /* cards */
--color-surface-alt: #f4f2ee;  /* alternating bands */
--color-brand-500: #035948;    /* primary */
--color-brand-400: #0ca789;    /* live accent */
--color-ink: #0c1a14;          /* headlines */
--color-muted: #5c6b62;        /* body copy */
--color-line: #e2ddd8;         /* borders */
--font-display: "DM Serif Display", Georgia, serif;
--font-sans: "DM Sans", system-ui, sans-serif;
--font-mono: "JetBrains Mono", monospace;
--radius-xl: 6px;              /* controls */
--radius-2xl: 16px;            /* cards */
--shadow-card: 0 4px 32px rgba(3,89,72,0.08);
```

Motion mirrors the source: 200 ms `cubic-bezier(0.4, 0, 0.2, 1)` hover
transitions, a 1.5 s live-dot pulse, 420 ms page entrance and a 900 ms stat
count-up. Everything collapses under `prefers-reduced-motion: reduce`.
