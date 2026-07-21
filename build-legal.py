#!/usr/bin/env python3
"""Build the site's legal pages (privacy.html, terms.html, refund.html) from the
source markdown in legal/. Fills the placeholders from CONFIG below, adds the
Google Analytics / cookie disclosure to the privacy policy, and wraps everything
in the site's shell (nav, dark/light theme, GA, footer). Unknown legal fields
(mailing address, governing state, venue) render as highlighted [fill] markers
until you set them here and re-run.

    python3 build-legal.py
"""
import html, os, re

SITE = os.path.dirname(os.path.abspath(__file__))
GA_ID = "G-365JP65BHP"

# --- Fill these in, then re-run to finalize -------------------------------
CONFIG = {
    "EFFECTIVE_DATE": "July 15, 2026",
    "LEGAL_ENTITY":   "C3D Prints",
    "SUPPORT_EMAIL":  "Hi@c3dprints.com",
    "MAILING_ADDRESS": "42 Revere Beach Pkwy, Chelsea, MA, USA",
    "GOVERNING_STATE": "the Commonwealth of Massachusetts, USA",
    "VENUE":           "Suffolk County, Massachusetts",
    "REFUND_DAYS":    "14",
}

def fill(v, label):
    return v if v else f"@@FILL:{label}@@"

# --- Markdown -> HTML (small, tailored to these docs) ---------------------
def inline(t):
    t = html.escape(t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"@@FILL:(.*?)@@", r'<mark class="fill">[\1]</mark>', t)
    return t

def md_to_html(md):
    blocks, cur = [], []
    for ln in md.splitlines():
        if ln.strip() == "":
            if cur: blocks.append(cur); cur = []
        else:
            cur.append(ln)
    if cur: blocks.append(cur)
    out, title = [], None
    for blk in blocks:
        first = blk[0].lstrip()
        if first.startswith(">"):
            continue  # drop DRAFT banners
        if first.startswith("#"):
            level = len(first) - len(first.lstrip("#"))
            text = first[level:].strip()
            if level == 1 and title is None:
                title = text  # H1 becomes the page hero, not repeated in body
                continue
            tag = "h2" if level == 2 else "h3"
            out.append(f"<{tag}>{inline(text)}</{tag}>")
            continue
        if first.startswith("- "):
            items, buf = [], None
            for ln in blk:
                s = ln.strip()
                if s.startswith("- "):
                    if buf is not None: items.append(buf)
                    buf = s[2:].strip()
                else:
                    buf = (buf + " " + s) if buf else s
            if buf is not None: items.append(buf)
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            continue
        out.append(f"<p>{inline(' '.join(l.strip() for l in blk))}</p>")
    return title or "", "\n".join(out)

# --- Per-document substitutions -------------------------------------------
def sub_common(md):
    md = md.replace("[EFFECTIVE_DATE]", CONFIG["EFFECTIVE_DATE"])
    md = md.replace('[C3D Prints — your legal entity, e.g. "C3D Prints, LLC"]', CONFIG["LEGAL_ENTITY"])
    md = md.replace("[C3D Prints — your legal entity]", CONFIG["LEGAL_ENTITY"])
    md = md.replace("[C3D Prints — legal entity]", CONFIG["LEGAL_ENTITY"])
    md = md.replace("[SUPPORT_EMAIL]", CONFIG["SUPPORT_EMAIL"])
    return md

def build_privacy(md):
    md = sub_common(md)
    md = md.replace(
        "- **Website:** makerq.io may use basic, privacy-respecting analytics and cookies. [Confirm/adjust with\n  your actual site setup.]",
        "- **Website analytics:** makerq.io uses Google Analytics (provided by Google LLC) to measure "
        "traffic and improve the site. Google Analytics sets cookies and collects usage data such as pages "
        "viewed, approximate location, and device and browser type. You can opt out via your browser "
        "settings or Google's opt-out browser add-on (tools.google.com/dlpage/gaoptout).")
    return md

def build_terms(md):
    md = sub_common(md)
    md = md.replace("[Refund Policy](refund.md)", "[Refund Policy](refund.html)")
    md = md.replace(
        '[SUMMARY — e.g., "14-day refund on Pro; Lifetime\nrefundable within 14 days of purchase; renewals are non-refundable but cancelable anytime."]',
        f"you have a {CONFIG['REFUND_DAYS']}-day money-back window on your initial Pro purchase and on "
        f"Lifetime; renewals are non-refundable but you can cancel anytime to stop future charges.")
    md = md.replace("[STATE/COUNTRY]", fill(CONFIG["GOVERNING_STATE"], "your state / country"))
    md = md.replace("[VENUE]", fill(CONFIG["VENUE"], "your county / state"))
    return md

def build_refund(md):
    md = sub_common(md)
    md = md.replace("[CHOOSE ONE — recommended: 14-day money-back]\n", "")
    md = md.replace("[14]", CONFIG["REFUND_DAYS"])
    return md

# --- Page shell -----------------------------------------------------------
def page(title, subtitle, body, active, updated):
    nav = """<nav class="nav" aria-label="MakerQ">
  <div class="nav-inner">
    <a class="brand" href="./">Maker<span>Q</span></a>
    <div class="links">
      <a href="index.html#features">Features</a>
      <a href="index.html#pricing">Pricing</a>
      <a href="demo/">Demo</a>
      <a href="download.html">Download</a>
      <a href="contact.html">Contact</a>
    </div>
    <div class="right">
      <a class="nav-mail" href="mailto:c3dprints@email.moosedesk.com">Support</a>
      <button class="mq-theme-btn" type="button" aria-label="Toggle light or dark theme" title="Toggle theme">
        <svg class="mq-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
        <svg class="mq-moon" viewBox="0 0 24 24" fill="currentColor" style="display:none"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
      </button>
    </div>
  </div>
</nav>"""

    legal_active = lambda p: ' class="on"' if p == active else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}
gtag('js',new Date());gtag('config','{GA_ID}');</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}, MakerQ</title>
<meta name="description" content="{title} for MakerQ, quoting software for 3D print shops.">
<meta property="og:type" content="website">
<meta property="og:site_name" content="MakerQ">
<meta property="og:url" content="https://makerq.io/{active}">
<meta property="og:title" content="{title}, MakerQ">
<meta property="og:description" content="{title} for MakerQ, quoting software for 3D print shops.">
<meta property="og:image" content="https://makerq.io/img/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="MakerQ, quoting software for 3D print shops">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}, MakerQ">
<meta name="twitter:description" content="{title} for MakerQ, quoting software for 3D print shops.">
<meta name="twitter:image" content="https://makerq.io/img/og-image.png">
<link rel="canonical" href="https://makerq.io/{active}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<style>
:root{{--bg:#0b1623;--surface:#111e2e;--card:#162236;--input:#0d1928;--border:#1e3550;
  --blue:#00aaff;--blue-l:#33ccff;--orange:#ff6b1a;--orange-l:#ff8c3a;--green:#00e890;
  --text:#ddeeff;--muted:#9fb6d0}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.6}}
a{{color:var(--blue-l);text-decoration:none}}a:hover{{text-decoration:underline}}
.nav{{position:sticky;top:0;z-index:100;background:rgba(11,22,35,.9);backdrop-filter:blur(14px);
  -webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--border)}}
.nav-inner{{max-width:1120px;margin:0 auto;padding:10px 24px;display:flex;align-items:center;gap:18px}}
.brand{{font-weight:800;font-size:20px;letter-spacing:-.5px;color:var(--text)}}.brand span{{color:var(--orange-l)}}
.links{{display:flex;gap:4px}}
.links a{{padding:8px 12px;border-radius:10px;color:var(--muted);font-weight:600;font-size:14px;transition:color .15s,background .15s}}
.links a:hover{{color:var(--text);background:rgba(0,170,255,.12);text-decoration:none}}
.right{{margin-left:auto;display:flex;align-items:center;gap:14px}}
.nav-mail{{color:var(--muted);font-size:13px;font-weight:600}}.nav-mail:hover{{color:var(--blue-l)}}
@media(max-width:820px){{.nav-mail{{display:none}}.links a{{padding:8px 7px;font-size:13px}}}}
.mq-theme-btn{{width:38px;height:38px;border-radius:11px;border:1px solid var(--border);
  background:var(--card);color:var(--text);cursor:pointer;display:inline-grid;place-items:center;padding:0;
  transition:transform .15s ease,border-color .2s,box-shadow .2s,background .2s}}
.mq-theme-btn:hover{{transform:translateY(-2px) rotate(-8deg);border-color:var(--blue);box-shadow:0 8px 22px rgba(0,170,255,.22)}}
.mq-theme-btn svg{{width:19px;height:19px}}
.wrap{{max-width:800px;margin:0 auto;padding:52px 24px 60px}}
.eyebrow{{display:inline-block;font-size:13px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--blue-l);background:rgba(0,170,255,.1);border:1px solid rgba(0,170,255,.3);padding:6px 14px;border-radius:999px}}
h1{{font-size:clamp(30px,5vw,44px);margin:16px 0 6px;letter-spacing:-.5px}}
.updated{{color:var(--muted);font-size:14px;margin:0 0 30px}}
.prose h2{{font-size:20px;margin:34px 0 10px;padding-top:8px}}
.prose h3{{font-size:16px;margin:22px 0 8px;color:var(--blue-l)}}
.prose p{{margin:0 0 14px;color:var(--text)}}
.prose ul{{margin:0 0 16px;padding-left:22px}}
.prose li{{margin:0 0 8px}}
.prose strong{{color:var(--text)}}
mark.fill{{background:rgba(255,196,0,.28);color:var(--orange-l);border:1px dashed rgba(255,140,0,.6);
  border-radius:5px;padding:0 6px;font-weight:600;font-style:normal}}
.footer{{border-top:1px solid var(--border);margin-top:20px;padding:28px 0;text-align:center}}
.footer-links{{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-bottom:10px}}
.footer-links a{{color:var(--muted);font-weight:600;font-size:14px;padding:6px 12px;border-radius:8px;transition:color .15s,background .15s}}
.footer-links a:hover{{color:var(--text);background:rgba(0,170,255,.12);text-decoration:none}}
.footer-legal{{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-bottom:12px;font-size:13px}}
.footer-legal a{{color:var(--muted);padding:4px 10px;border-radius:8px}}
.footer-legal a.on{{color:var(--text)}}
.footer-copy{{color:var(--muted);font-size:13px}}
html[data-theme="light"]{{--bg:#eef3f9;--surface:#ffffff;--card:#ffffff;--input:#eef2f8;
  --border:#d7e2f0;--text:#13233a;--muted:#59708a}}
html[data-theme="light"] body{{background:var(--bg)}}
html[data-theme="light"] .nav{{background:rgba(255,255,255,.86)}}
@media print{{
  .nav,.footer-links,.mq-theme-btn{{display:none!important}}
  html,body{{background:#fff!important;color:#111!important}}
  .wrap{{max-width:none;padding:0 8px}}
  .prose p,.prose li,.prose strong,h1,.updated{{color:#111!important}}
  .prose h2{{color:#111!important}}.prose h3{{color:#0a4b78!important}}
  a{{color:#0a4b78!important}}
  .eyebrow{{border-color:#bbb;color:#0a4b78;background:#eef}}
  mark.fill{{background:#ffe9a8;color:#7a5200;border-color:#caa02a}}
  .footer{{border-color:#ccc}}
}}
</style>
</head>
<body>
{nav}
<div class="wrap">
  <span class="eyebrow">Legal</span>
  <h1>{title}</h1>
  <p class="updated">Effective {updated}</p>
  <div class="prose">
{body}
  </div>
</div>
<footer class="footer">
  <div class="footer-links">
    <a href="index.html#features">Features</a>
    <a href="index.html#pricing">Pricing</a>
    <a href="demo/">Demo</a>
    <a href="download.html">Download</a>
    <a href="contact.html">Contact</a>
  </div>
  <div class="footer-legal">
    <a href="privacy.html"{legal_active('privacy')}>Privacy</a>
    <a href="terms.html"{legal_active('terms')}>Terms</a>
    <a href="refund.html"{legal_active('refund')}>Refund</a>
  </div>
  <div class="footer-copy">MakerQ.io &middot; &copy; C3D Prints. Made for makers.</div>
</footer>
<script>
(function(){{
  var KEY="mq-theme",root=document.documentElement;
  function apply(t){{root.setAttribute("data-theme",t);
    document.querySelectorAll(".mq-theme-btn").forEach(function(b){{
      var s=b.querySelector(".mq-sun"),m=b.querySelector(".mq-moon");
      if(s)s.style.display=(t==="light")?"none":"block";
      if(m)m.style.display=(t==="light")?"block":"none";}});}}
  var saved;try{{saved=localStorage.getItem(KEY)}}catch(e){{}}
  var t=saved||((window.matchMedia&&matchMedia("(prefers-color-scheme: light)").matches)?"light":"dark");
  apply(t);
  document.addEventListener("click",function(e){{
    var b=e.target.closest&&e.target.closest(".mq-theme-btn");if(!b)return;e.preventDefault();
    t=(root.getAttribute("data-theme")==="light")?"dark":"light";
    apply(t);try{{localStorage.setItem(KEY,t)}}catch(e){{}}}});
}})();
</script>
</body>
</html>
"""

DOCS = [("privacy", build_privacy, "privacy"),
        ("terms", build_terms, "terms"),
        ("refund", build_refund, "refund")]

def main():
    for name, builder, active in DOCS:
        md = open(os.path.join(SITE, "legal", f"{name}.md")).read()
        title, body = md_to_html(builder(md))
        out = page(title, "", body, active, CONFIG["EFFECTIVE_DATE"])
        open(os.path.join(SITE, f"{name}.html"), "w").write(out)
        n_fill = out.count('mark class="fill"')
        print(f"wrote {name}.html  ({title})  fill-markers={n_fill}")

if __name__ == "__main__":
    main()
