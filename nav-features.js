/* Features dropdown for the MakerQ site nav.
 *
 * One shared file because the nav markup is duplicated across every page, in two
 * flavours: index.html uses .mq-nav-links / .mq-nav-menu, the sub-pages use
 * .links / .nav-menu. This upgrades whichever it finds: the desktop "Features"
 * link gains a dropdown, the mobile menu gains an indented sub-list. Without
 * JavaScript the plain Features link still works, so nothing is lost.
 *
 * Section ids live in index.html. Adding a feature means adding one line here.
 */
(function () {
  var FEATURES = [
    ["Intake forms and queue",   "intake"],
    ["Pricing calculator",       "quoting"],
    ["Quick Quote and stickers", "calculators"],
    ["Outline Tracer",           "tracer"],
    ["Kanban and production",    "manage"],
    ["Customers and orders",     "customers"],
    ["Customer status pages",    "status"],
    ["Runs on your computer",    "local"]
  ];

  // On index.html the links are bare hashes; elsewhere they have to point back at it.
  var onIndex = /(^|\/)(index\.html)?$/.test(location.pathname);
  var base = onIndex ? "" : "index.html";
  var href = function (id) { return base + "#" + id; };

  var css =
    '.mqf{position:relative;display:inline-flex;align-items:center}' +
    '.mqf-caret{margin-left:5px;width:9px;height:9px;flex:none;transition:transform .18s ease}' +
    '.mqf.open .mqf-caret{transform:rotate(180deg)}' +
    '.mqf-panel{position:absolute;top:calc(100% + 10px);left:0;z-index:200;min-width:248px;padding:8px;' +
      'border-radius:14px;border:1px solid var(--border,#1e3550);background:var(--card,#162236);' +
      'box-shadow:0 22px 50px rgba(0,0,0,.42);opacity:0;visibility:hidden;transform:translateY(-6px);' +
      'transition:opacity .16s ease,transform .16s ease,visibility .16s}' +
    '.mqf.open .mqf-panel{opacity:1;visibility:visible;transform:none}' +
    '.mqf-panel a{display:block;padding:9px 12px;border-radius:9px;font-size:14px;font-weight:600;' +
      'color:var(--muted,#9fb6d0);white-space:nowrap}' +
    '.mqf-panel a:hover,.mqf-panel a:focus-visible{color:var(--text,#ddeeff);background:rgba(0,170,255,.12)}' +
    // a sticky header would otherwise sit on top of the heading we jump to
    '#intake,#quoting,#calculators,#tracer,#manage,#customers,#status,#local,#features,#how,#pricing' +
      '{scroll-margin-top:86px}' +
    '.mqf-sub{margin:2px 0 6px 12px;padding-left:10px;border-left:1px solid var(--border,#1e3550)}' +
    '.mqf-sub a{font-size:14px!important;opacity:.92}' +
    '@media(max-width:760px){.mqf-panel{display:none}}';

  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  var CARET = '<svg class="mqf-caret" viewBox="0 0 12 12" fill="none" stroke="currentColor" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M2 4.5 6 8.5 10 4.5"/></svg>';

  function isFeaturesLink(a) {
    return /(^|\/)(index\.html)?#features$/.test(a.getAttribute("href") || "");
  }

  /* Desktop: wrap the Features link so it keeps working as a link, and hang a
     panel off it that opens on hover, focus, or click. */
  function buildDropdown(link) {
    var wrap = document.createElement("div");
    wrap.className = "mqf";
    link.parentNode.insertBefore(wrap, link);
    wrap.appendChild(link);
    link.insertAdjacentHTML("beforeend", CARET);
    link.setAttribute("aria-expanded", "false");

    var panel = document.createElement("div");
    panel.className = "mqf-panel";
    panel.innerHTML = FEATURES.map(function (f) {
      return '<a href="' + href(f[1]) + '">' + f[0] + "</a>";
    }).join("");
    wrap.appendChild(panel);

    var open = false, closeTimer;
    function setOpen(v) {
      open = v;
      wrap.classList.toggle("open", v);
      link.setAttribute("aria-expanded", v ? "true" : "false");
    }
    wrap.addEventListener("mouseenter", function () { clearTimeout(closeTimer); setOpen(true); });
    wrap.addEventListener("mouseleave", function () {
      closeTimer = setTimeout(function () { setOpen(false); }, 160);
    });
    wrap.addEventListener("focusin", function () { setOpen(true); });
    wrap.addEventListener("focusout", function () {
      setTimeout(function () { if (!wrap.contains(document.activeElement)) setOpen(false); }, 0);
    });
    // Tap or click on the link itself: the first press opens the menu instead of jumping.
    link.addEventListener("click", function (e) {
      if (!open) { e.preventDefault(); setOpen(true); }
    });
    panel.addEventListener("click", function () { setOpen(false); });
    document.addEventListener("click", function (e) { if (!wrap.contains(e.target)) setOpen(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") setOpen(false); });
  }

  /* Mobile menu: a plain indented list, always visible, no toggle to fumble with. */
  function buildSubList(link) {
    var sub = document.createElement("div");
    sub.className = "mqf-sub";
    sub.innerHTML = FEATURES.map(function (f) {
      return '<a href="' + href(f[1]) + '">' + f[0] + "</a>";
    }).join("");
    link.parentNode.insertBefore(sub, link.nextSibling);
  }

  function init() {
    var desktop = document.querySelector(".mq-nav-links, .links");
    var mobile = document.querySelector(".mq-nav-menu, .nav-menu");
    if (desktop) {
      var d = Array.prototype.filter.call(desktop.querySelectorAll("a"), isFeaturesLink)[0];
      if (d) buildDropdown(d);
    }
    if (mobile) {
      var m = Array.prototype.filter.call(mobile.querySelectorAll("a"), isFeaturesLink)[0];
      if (m) buildSubList(m);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
