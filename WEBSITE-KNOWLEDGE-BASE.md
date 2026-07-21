# MakerQ Website, Knowledge Base

> Single source of truth for the MakerQ **marketing website** (makerq.io). Covers the repo,
> hosting/deploy, every page, the design system, pricing copy, analytics, downloads, forms,
> legal, the interactive demo, SEO, the generation scripts, and the gotchas.
> This is the *site* KB; the desktop app has its own at
> `c3dprints-quote-portal/MAKERQ-KNOWLEDGE-BASE.md`. Last update: 2026-07-20.

---

## Contents
1. [What this is](#1-what-this-is)
2. [Repo, domain & hosting](#2-repo-domain--hosting)
3. [Deploy pipeline & the Jekyll gotcha](#3-deploy-pipeline--the-jekyll-gotcha)
4. [Page inventory](#4-page-inventory)
5. [Design system & brand](#5-design-system--brand)
6. [Pricing copy](#6-pricing-copy)
7. [Analytics (GA4) & the /stats dashboard](#7-analytics-ga4--the-stats-dashboard)
8. [Downloads & the release-sync gotcha](#8-downloads--the-release-sync-gotcha)
9. [Forms & Stripe touchpoints](#9-forms--stripe-touchpoints)
10. [Legal pages (privacy/terms/refund)](#10-legal-pages-privacyterms refund)
11. [The interactive demo](#11-the-interactive-demo)
12. [SEO: OG, canonicals, robots, sitemap, noindex](#12-seo-og-canonicals-robots-sitemap-noindex)
13. [Generation scripts reference](#13-generation-scripts-reference)
14. [Working conventions](#14-working-conventions)
15. [Gotchas](#15-gotchas)
16. [Open items / TODO](#16-open-items--todo)
17. [Quick "how do I…" index](#17-quick-how-do-i-index)

---

## 1. What this is
The **static marketing site** for MakerQ, the self-hosted desktop quoting app for 3D-print shops
(by C3D Prints, Chelsea MA). The site's job: explain the product, funnel visitors to **download**
(Windows now, macOS soon) and to **get-started**, and host the **legal** pages and the **Stripe
post-purchase** page. The site **never processes payment**; all checkout happens inside the desktop
app. Everything is hand-written static HTML/CSS/JS, no framework, no build step for most pages.

---

## 2. Repo, domain & hosting
- **Repo:** `c3dprints/Makerquotesite` (public). Local: `~/Documents/Makerquotesite`.
- **Live domain:** **makerq.io** (custom domain via the `CNAME` file = `makerq.io`). The old
  `makerquote.c3dprints.com` is retired (NXDOMAIN); don't reference it.
- **Host:** GitHub Pages, **legacy build**, source = `main` branch, root path.
- **`.nojekyll`** is present at the root, Pages serves files **as-is, no Jekyll**. Keep it.
- **Extensionless URLs work:** Pages serves `foo.html` at `/foo`. So `/get-started`, `/thanks`,
  `/stats`, `/privacy`, `/terms`, `/refund`, `/download`, `/contact` all resolve (200, text/html).
  Canonicals + internal links use the extensionless form for these.

---

## 3. Deploy pipeline & the Jekyll gotcha
- Every push to `main` triggers the auto-generated **"pages build and deployment"** GitHub Action.
  A commit is live ~1-2 min after it succeeds.
- **The Jekyll 503 gotcha (why we added `.nojekyll`):** the Jekyll `github-metadata` plugin calls
  GitHub's API mid-build and **intermittently fails the whole deploy on a `503`** ("No server is
  currently available"). Symptom: a new page 404s while everything else stays on the previous
  deploy. `.nojekyll` bypasses Jekyll entirely, so this can't happen and JS with `{{ }}` can't be
  mis-parsed by Liquid.
- **Check a deploy:** `gh api repos/c3dprints/Makerquotesite/actions/runs --jq '.workflow_runs[0]|{status,conclusion,head_sha}'`.
  Re-run a failed one: `gh run rerun <id> --repo c3dprints/Makerquotesite`.
- **Coordination:** a second Claude/session sometimes edits this same repo (e.g. it added the OG
  tags + `og-image.png` in commit "1"). **Always `git fetch` and check `HEAD..origin/main` before
  committing**, and push promptly to shrink the conflict window.

---

## 4. Page inventory
All at the site root unless noted. "indexed" = in sitemap / crawlable.

| URL | File | Purpose | Indexed |
|---|---|---|---|
| `/` | `index.html` | Landing: hero, value cards, feature sections (intake, pricing, manage, **customers**, **customer status page**, own-your-data), how-it-works, **pricing cards + compare grid** | yes |
| `/get-started?plan=free\|pro\|lifetime` | `get-started.html` | Plan-aware onboarding + Windows download + activation steps. Pills switch plan without reload | yes |
| `/download` | `download.html` | Download page. Windows live; macOS "coming soon" card | yes |
| `/contact` | `contact.html` | Contact form → FormSubmit to MooseDesk intake (c3dprints@email.moosedesk.com) | yes |
| `/demo/` | `demo/index.html` | Framed wrapper around the interactive demo (`demo/app.html` in an iframe) | yes |
| `/privacy` `/terms` `/refund` | `privacy/terms/refund.html` | Legal (generated, see §10) | yes |
| `/thanks?checkout=success` | `thanks.html` | **Stripe post-purchase** redirect target. `noindex` | no |
| `/stats` | `stats.html` | **Hidden** live download dashboard (GitHub API). `noindex` | no |
| `/pricing-backup.html` | `pricing-backup.html` | Old priced landing copy kept as reference. `noindex` | no |
| `/shopify-page.html` | `shopify-page.html` | Scoped `.mq-landing` block to paste into a Shopify page. Headless (no `<head>`); blocked via robots.txt. **Stale, refresh before using** | no |
| `/demo/app.html` | `demo/app.html` | Auto-generated mocked app UI (see §11). Not linked as a page | no |

Primary CTAs ("Start free", "Get the app", "Get MakerQ") → `get-started?plan=free`. The three
pricing buttons → `get-started?plan={free\|pro\|lifetime}`. The plain nav **Download** → `download.html`.

---

## 5. Design system & brand
- **Palette (CSS vars):** `--bg:#0b1623` (dark navy), `--card:#162236`, `--border:#1e3550`,
  `--blue:#00aaff`/`--blue-l:#33ccff`, `--orange:#ff6b1a`/`--orange-l:#ff8c3a`, `--green:#00e890`,
  `--text:#ddeeff`, `--muted:#9fb6d0`. Accent = blue→orange gradient (`.mq-grad` / `.grad`).
- **Wordmark:** text "Maker" + orange "**Q**" (`<span>`), no image logo in the nav.
- **Light/dark theme:** every page has a `.mq-theme-btn` (sun/moon) toggle. Default follows
  `prefers-color-scheme`; choice saved in `localStorage["mq-theme"]`; `data-theme="light"` on
  `<html>` drives the overrides. index/pricing-backup use a floating `.mq-theme-fab` that hides on
  scroll and hands off to a nav toggle; other pages put it in the nav.
- **Favicon:** `favicon.svg` (+ `favicon.ico`, `apple-touch-icon.png`), a "Q" mark (dark rounded
  tile, blue→orange gradient Q). Linked on every page. Source can be re-rendered from `favicon.svg`.
- **Landing CSS is scoped under `.mq-landing`** (so `index.html` / `pricing-backup.html` /
  `shopify-page.html` can be pasted into Shopify without clashing). Other pages use `:root` vars.
- **Images:** `img/` holds the app screenshots (`queue.png`, `kanban.png`, `analytics.png`,
  `calculator.png`, `form.png`, `customers.png`, `status.png`) + `og-image.png` (1200x630 social
  card) + `_og-template.html` (source to re-render the OG image via headless Chrome).

---

## 6. Pricing copy
Shown on the landing pricing section (`#pricing`) as three cards + a **Compare plans** grid.

| Plan | Price shown | Notes |
|---|---|---|
| **Free** | **$0 · to try** | Framed as a **free trial / "start free"** (NOT "free forever", that wording was removed 2026-07-20). Real caps: 5 active projects, 1 printer, local features. |
| **Pro** | **$8.99/mo** or **$89.99/yr** | "Most popular", everything unlocked. |
| **Lifetime** | **$249.99** one-time | "Own it **forever**" is fine here (accurate, one-time). |

- **All payment happens inside the desktop app** (Stripe). The site has **no** Stripe keys / price
  IDs / checkout, and must not. Pricing buttons route to `/get-started?plan=…`.
- The **Compare plans** grid (`.mq-compare` in index) lists 13 features across Free/Pro/Lifetime
  with the Pro column highlighted. Keep it in sync with the tier model if features change.
- Founder/Standard tiers were removed; don't reintroduce. "no monthly fees" phrasing was removed
  from meta descriptions (Pro is monthly).

---

## 7. Analytics (GA4) & the /stats dashboard
- **GA4 Measurement ID: `G-365JP65BHP`**, on every page's `<head>`.
- **Custom events:**
  - `file_download` (download buttons on `download.html` + `get-started.html`) with
    `{file_name, file_extension, platform:'windows', source, plan}`. Mark it a **key event** in GA4
    to track it as a conversion. (The GitHub CDN link is otherwise invisible to the site.)
  - `purchase` (thanks.html) fires **only** when `?checkout=success` is present. Currently has no
    `transaction_id`/`value` (open item).
  - `select_plan` (get-started pills).
- **`/stats`** (hidden, noindex): a live dashboard that reads the **GitHub public API**
  (`api.github.com/repos/c3dprints/MakerQ-download/releases`) client-side, sums `.exe` download
  counts across releases, and shows total + per-release table + a refresh button. No auth (public
  repo). GitHub's `download_count` is **per release** and resets each version; the page sums them.
- **Two different numbers:** GA `file_download` = clicks from the *site*; GitHub `download_count` =
  *every* download of the installer (site + shared direct links). They won't match, by design.

---

## 8. Downloads & the release-sync gotcha
- **Windows button/link (permanent):**
  `https://github.com/c3dprints/MakerQ-download/releases/latest/download/MakerQ-Setup.exe`
  It's a **plain `<a … download>`**, the browser downloads straight from GitHub's CDN, nothing is
  proxied through the site. `/releases/latest/` always resolves to the newest release.
- **`c3dprints/MakerQ-download` is a separate PUBLIC repo** that the website (button + `/stats`)
  reads. It is NOT the app's updater feed.
- **THE GOTCHA (release sync):** the app's release process publishes to the **private** updater
  repos (`c3dprints/MakerQ-releases`, legacy `MakerQuote-releases`) but must **also** publish to
  the public `MakerQ-download`, or the site serves the old version. Requirements for MakerQ-download:
  - a Release tagged `vX.Y.Z`, marked **latest** (not draft/prerelease), and
  - the asset named **exactly `MakerQ-Setup.exe`** (unversioned). The build outputs
    `MakerQ-1.1.20-Setup.exe`, so it must be renamed/copied to `MakerQ-Setup.exe` before upload
    (the `file#label` gh trick only sets a display label, not the download filename).
  - One-liner: `cp MakerQ-1.1.20-Setup.exe MakerQ-Setup.exe && gh release create v1.1.20 --repo c3dprints/MakerQ-download --title "MakerQ 1.1.20" --notes "…" MakerQ-Setup.exe`
- **macOS:** the card is "coming soon". When the `.dmg` ships, wire it to the **public**
  `cdezbch/MakerQ-mac-releases` (per the app KB) and flip the macOS card the same way as Windows.

---

## 9. Forms & Stripe touchpoints
- **Contact form (`contact.html`):** submits on-page via **FormSubmit** to **MooseDesk's email-to-ticket intake**
  `c3dprints@email.moosedesk.com`, so submissions become MooseDesk tickets. No account, but needs a
  **one-time FormSubmit activation**: the first real submission emails a confirm link to that address
  (it arrives as a MooseDesk ticket), click it once, then submissions flow. Honeypot field included.
  (Support email switched from Hi@c3dprints.com to MooseDesk on 2026-07-20.)
- **Thanks page (`thanks.html`):** the Stripe **`BILLING_SUCCESS_URL`** redirect target is
  `https://makerq.io/thanks?checkout=success`. It reads fine without the param; the activation-key
  email is the source of truth, this page is reassurance ("Payment received, check your email,
  Settings → License → paste key → Activate").

---

## 10. Legal pages (privacy/terms/refund)
- **Generated** by `build-legal.py` from `legal/*.md` into `privacy.html` / `terms.html` /
  `refund.html`. Re-run after editing the md: `python3 build-legal.py`.
- **Config** lives in `CONFIG` at the top of `build-legal.py` (finalized 2026-07-15):
  entity **C3D Prints**, address **42 Revere Beach Pkwy, Chelsea, MA, USA**, support
  **Hi@c3dprints.com**, governing law **Massachusetts** / venue **Suffolk County**, 14-day refund.
  Unset fields render as highlighted `[fill]` markers.
- The template bakes in **favicon + OG + canonical** (added after a rebuild once stripped them, so
  a rebuild now keeps them). Privacy includes the **Google Analytics / cookie disclosure**;
  Service Providers section is generic (does NOT name Supabase/Resend/GitHub, only Stripe).
- **PDFs for Stripe:** `legal/pdf/MakerQ-{privacy,terms,refund}.pdf`, regenerate with the
  Playwright print-to-pdf script (headless Chrome, `emulate_media("print")`), and copy to the
  Desktop. Regenerate whenever the md changes.

---

## 11. The interactive demo
- **`demo/app.html`** is a mocked copy of the real admin UI, generated by **`build-demo.py`** (run
  with the app repo's venv python). It reads **`backend/admin.html`** from the app repo (`origin/main`,
  the canonical Windows-pushed UI), boots the backend to record canned API responses, then writes
  `demo/app.html` = the real UI + a `fetch` mock serving canned data. `enrich()` fills sample data
  (AI summary, structured quote, uploaded files, per-customer email log, richer request fields) and
  pins the footer version via `APP_VERSION` (bump this constant to match the current app version).
- **`demo/index.html`** is the framed "browser window" wrapper that iframes `app.html`.
- Rebuild when the app UI changes: point a copy of the script at a fresh `origin/main` worktree
  (build-demo hardcodes the repo path), or edit `REPO`. The app's `updater.VERSION` lags, so the
  demo version comes from `APP_VERSION` in `build-demo.py`, not `/health`.

---

## 12. SEO: OG, canonicals, robots, sitemap, noindex
- **Open Graph + Twitter Card** tags on all public pages (index, get-started, download, contact,
  demo, privacy, terms, refund). Shared image: `https://makerq.io/img/og-image.png` (1200x630).
  Legal pages get theirs from the `build-legal.py` template.
- **Canonicals** are extensionless: `/`, `/get-started`, `/download`, `/contact`, `/demo/`,
  `/privacy`, `/terms`, `/refund`. Sitemap URLs match these exactly.
- **`robots.txt`** allows all, disallows `/pricing-backup.html`, `/shopify-page.html`, `/stats`,
  `/thanks`, and points to `sitemap.xml`.
- **`sitemap.xml`** lists the 8 public URLs above.
- **`noindex`** meta on `thanks.html`, `stats.html`, `pricing-backup.html`. `shopify-page.html` is
  headless so it's blocked via robots.txt instead.
- **Style rule enforced site-wide:** **no em dashes / en dashes** (`—` `–`), commas or hyphens only.

---

## 13. Generation scripts reference
| Script | What it does |
|---|---|
| `build-legal.py` | Generates `privacy/terms/refund.html` from `legal/*.md`; fills `CONFIG`; bakes OG/favicon/canonical. |
| `build-demo.py` | Generates `demo/app.html` from the app's `backend/admin.html` + a mock backend; `enrich()` adds sample data; `APP_VERSION` sets the footer version. |
| `favicon.svg` | Source of the favicon; re-render to PNG/ICO via headless Chrome + PIL if it changes. |
| `img/_og-template.html` | Source of `og-image.png` (1200x630); render via headless Chrome. |
| (ad-hoc) legal PDF render | Playwright headless, `emulate_media("print")`, `page.pdf(format="Letter")` → `legal/pdf/`. |

---

## 14. Working conventions
- **No em/en dashes** in any copy, commas or hyphens only.
- **Payment lives only in the app**, never add Stripe/keys/price IDs to the site.
- **Keep the backend stack private** in the privacy policy (don't name Supabase/Resend/GitHub).
- **Fetch before you push** (a concurrent session may be editing this repo); push promptly.
- Commit identity used for this repo: `git -c user.name=cdezbch -c user.email=christopher.hernandez@childrens.harvard.edu commit …`.
- Verify visual changes by rendering with Playwright (system Chrome, `channel="chrome"`), the app
  repo's venv has Playwright installed: `~/Documents/c3dprints-quote-portal/backend/.venv/bin/python`.

---

## 15. Gotchas
- **Jekyll 503** fails deploys → fixed with `.nojekyll` (§3). If a deploy fails, re-run it.
- **Release sync:** the site's Windows download won't update unless the release is also published to
  the public `MakerQ-download` repo with the asset named exactly `MakerQ-Setup.exe` (§8).
- **build-legal / build-demo overwrite generated files** from templates, edit the *source*
  (`legal/*.md`, `build-legal.py` template, `build-demo.py`), not the generated HTML, or a rebuild
  wipes your change (this bit us: a rebuild once stripped favicon/OG from the legal pages).
- **Concurrent session** edits this repo (added OG tags in commit "1"); coordinate.
- **`demo/app.html` is generated**, don't hand-edit it; change the app UI or `build-demo.py`.
- Old domain `makerquote.c3dprints.com` is dead, purge any lingering references (they still exist in
  the stale `shopify-page.html`).

---

## 16. Open items / TODO
- **Refresh or retire `shopify-page.html`** (stale pricing + dead-domain links; currently just robots-blocked).
- **Contact form:** confirm the FormSubmit activation actually delivers (live test).
- **Accessibility:** primary orange buttons are ~2.9:1 contrast (below WCAG AA); a mobile nav menu
  is missing (6 links can overflow < ~400px).
- **`thanks.html` purchase event** lacks `transaction_id`/`value` (no revenue reporting).
- **macOS download** wiring when the `.dmg` ships (public `cdezbch/MakerQ-mac-releases`).
- Optional: mirror the Compare-plans grid onto `pricing-backup.html`; add lastmod automation to sitemap.

---

## 17. Quick "how do I…" index
- **Update a legal page:** edit `legal/<x>.md` → `python3 build-legal.py` → regenerate the PDF → commit.
- **Refresh the demo to the latest app UI:** worktree `origin/main` of the app repo, point
  `build-demo.py` at it, bump `APP_VERSION`, run it, commit `demo/app.html`.
- **See download counts:** open `/stats` (site) or the GitHub releases page; total via
  `gh api --paginate repos/c3dprints/MakerQ-download/releases --jq '[.[].assets[]|select(.name|endswith(".exe"))|.download_count]|add'`.
- **Windows download still old after a release?** The release wasn't published to `MakerQ-download`
  (or the asset isn't named `MakerQ-Setup.exe`), see §8.
- **A deploy 404s a new page:** the Pages build failed (likely Jekyll 503), re-run it
  (`gh run rerun <id> --repo c3dprints/Makerquotesite`); `.nojekyll` should prevent recurrence.
- **Change the GA ID:** it's `G-365JP65BHP` in every page `<head>` + the `/stats` and demo pages.
- **Add a page:** create `name.html` at root (served at `/name`), add GA + favicon + OG + a
  canonical, add it to `sitemap.xml` (or `noindex` + robots-disallow if internal).
</content>
