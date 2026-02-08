# Frontend

Next.js UI for notebooks, chat, tools, and theme management.

## Structure

- `src/pages` - routes
- `src/components` - UI components
- `src/lib/store` - Zustand stores
- `src/styles` - global theme and utilities

## Dev

```bash
pnpm install
pnpm dev
```

The frontend proxies `/api/*` to the backend via `pages/api/[...path].ts`.

## Scripts

- `pnpm dev`
- `pnpm build`
- `pnpm start`
- `pnpm lint`
- `pnpm format`

## Key Screens

- `/` landing page
- `/login` and `/signup`
- `/Home` record list
- `/Records/[user]/[id]` record workspace

## Tools Panel

The record workspace includes a Tools panel for:

- Summary generator
- Outline generator
- Insights
- Infographic
- PDF generation
