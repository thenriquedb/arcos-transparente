# Arcos Transparente — Landing Page

Static marketing/landing page for the Arcos Transparente chatbot. Built with
Next.js 14 (App Router), Tailwind CSS and Lucide icons. No backend, no
database — deploys cleanly to Vercel.

## Develop

```bash
cd landing
npm install
npm run dev        # http://localhost:3000
npm run build      # production build
```

## Configuration

All wireable values live in `lib/constants.ts`:

- `URL_CHATBOT` — replace the `__URL_CHATBOT__` placeholder with the live
  chatbot URL.
- `LINK_GITHUB` — repository link.
- `CREATOR_NAME`, `CREATOR_ROLE`, `CREATOR_LINKEDIN` — fill in for the
  "Sobre o criador" section.
- `CREATOR_EMAIL`, `DATA_RANGE`, `PRODUCTION_URL`.

## Theme

The institutional blue is driven by three CSS variables in
`app/globals.css` (`--color-primary`, `--color-primary-hover`,
`--color-primary-foreground`). Change them to re-theme the whole page.

## Deploy

Point Vercel at the `landing/` directory (Root Directory = `landing`). The OG
image is generated at `/opengraph-image` via `next/og`.
