# MakerQuote marketing page

Two ready-to-use versions of the MakerQuote landing page. Both are self-contained
(no build step, no dependencies) and animated. Real app screenshots are already
wired in from `img/` (hero, queue, calculator, analytics, settings); to swap any
for your own, just replace the file in `img/` or change the `<img src="...">`.

## Files
- `index.html` — standalone page for **GitHub Pages** (or any static host).
- `shopify-page.html` — the same content as a scoped block to paste into a
  **Shopify page** (instructions are in the comment at the top of the file).

## Host on GitHub Pages
1. Put `index.html` in a repo (its own repo, or a `/docs` or `gh-pages` branch).
2. Repo Settings > Pages > set the source branch/folder.
3. Your page goes live at `https://<user>.github.io/<repo>/`.

## Add to Shopify (its own page)
1. Shopify admin > Online Store > Pages > Add page.
2. In the content box, click the `< >` (Show HTML) button.
3. Paste everything below the comment in `shopify-page.html`, then Save.
4. The styles are scoped under `.mq-landing`, so they will not affect your theme.
   If the editor strips the small `<script>`, the page still shows fully (only the
   scroll fade-in is skipped); to keep it, add the block via a custom Liquid section.

## Editing
- Colors, fonts, and spacing live in the `.mq-landing{ --... }` variables and the
  scoped CSS at the top of the block.
- Set your real prices where the tier cards show `$__`.
- Point the buttons (`href="#"`) at your download / checkout links.
- Fill in the `<!-- TODO -->` notes.

(c) C3D Prints
