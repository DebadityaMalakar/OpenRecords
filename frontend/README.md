# OpenRecords Frontend

Next.js frontend for OpenRecords. Provides the notebook UI, chat, tools, and theme system.

## Setup

```bash
pnpm install
pnpm dev
```

Frontend runs at http://localhost:3000.

## Environment

Create `frontend/.env.local` if you need to point to a different backend:

```env
BACKEND_URL=http://localhost:8000
```

The frontend proxies `/api/*` to the backend via `pages/api/[...path].ts`.

## Useful Scripts

- `pnpm dev` - start dev server
- `pnpm build` - production build
- `pnpm start` - start production server
- `pnpm lint` - lint with Biome
- `pnpm format` - format with Biome
