# Supply Chain Dashboard (Chainguard)

Next.js app for the supply chain disruption dashboard.

## Running locally

From this directory (`ui/`):

```bash
npm install
npm run dev
```

Data is read from `config/` and `data/` inside `ui/`.

## Hosting (e.g. Vercel, Netlify)

The app is **self-contained in the `ui/` folder** so it works when the repo root is a parent folder.

1. **Push your repo to GitHub** (entire project or just the `ui` folder).

2. **If the repo root is the parent folder** (e.g. `htf26/` with `ui/` inside):
   - In your host (Vercel, Netlify, etc.), set **Root Directory** to `ui`.
   - Build command: `npm run build` (runs in `ui`).
   - Output / publish: use the framework default (Next.js is auto-detected when root is `ui`).

3. **If the repo contains only the app**, use the repo root as the project root (no root directory override).

Data and config live under `ui/config/` and `ui/data/`, so they are deployed with the app.

### Vercel

- **Root Directory:** `ui`
- Framework: Next.js (auto)
- Build: `npm run build` (from `ui`)

### Netlify

- **Base directory:** `ui`
- Build command: `npm run build`
- Publish directory: `ui/.next` (or use the Next.js plugin / preset)
