# Cloudflare Free CDN setup (recommended)

This project serves:
- **Frontend static assets** via nginx (HTML/JS/CSS)
- **Backend API** via FastAPI behind nginx at `/api/`

For a small server, Cloudflare’s free plan is the simplest way to:
- cache static frontend assets globally
- reduce origin bandwidth
- get baseline DDoS protection

## 1) Put DNS behind Cloudflare (Free plan)
- Create a Cloudflare account and add your domain.
- Choose the **Free** plan.
- Update your registrar nameservers to Cloudflare-provided nameservers.
- In Cloudflare DNS, create an `A`/`AAAA` record for your site (orange-cloud enabled = proxied).

## 2) Enable HTTPS
- Use Cloudflare “Full (strict)” if you have a valid origin cert.
- Otherwise use “Full” while you set up origin TLS.

## 3) Cache policy (safe defaults)
### Frontend (`/`)
- Cache **static assets** aggressively (JS/CSS/images).
- Keep `index.html` short-TTL or no-cache to avoid “stuck” deployments.

Suggested headers from nginx:
- Versioned assets: `Cache-Control: public, max-age=31536000, immutable`
- `index.html`: `Cache-Control: no-cache`

### API (`/api/*`)
- Do **not** cache POST responses.
- Safe GET caching candidates:
  - `GET /api/viirs/latest-available` (short TTL, e.g. 1 hour)
  - `GET /health` (no-cache)

If you later add `GET /suggest` (hotlist autocomplete), it’s also safe to cache.

## 4) Cloudflare rate limiting / WAF (optional)
Cloudflare Free doesn’t include all advanced WAF/rate-limit features, but you can still:
- Enable “I’m under attack mode” during abuse.
- Use “Bot Fight Mode” if needed.

## 5) Origin safety (still required)
Even with a CDN, keep origin protections enabled:
- backend rate limits
- bounded concurrency for network work (OSM/GEE/NOAA)
- clear 429/503 errors for overload

