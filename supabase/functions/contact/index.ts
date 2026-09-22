// MakerQ contact-form relay (Supabase Edge Function).
// Sends the makerq.io contact form via Resend FROM a verified makerq.io address
// (so it passes SPF/DKIM and MooseDesk ticketizes it instead of spam-filtering),
// with reply-to set to the sender.
//
// Supports BOTH:
//  - native HTML form POST (form-encoded, with a "_next" field): responds with a
//    303 redirect to _next on success (no JavaScript / fetch required), and
//  - AJAX fetch (JSON): responds with {success:true} / {error:...}.
//
// Deploy:  supabase functions deploy contact --no-verify-jwt --project-ref enyimtvgqzmpaiaeiyxj
// Secret:  RESEND_API_KEY  (RESEND_FROM / CONTACT_TO optional)
//          RECAPTCHA_SECRET_KEY  (Google reCAPTCHA v2 checkbox; enforced when set)

const ALLOWED = new Set(["https://makerq.io", "https://www.makerq.io"]);
const TO = Deno.env.get("CONTACT_TO") ?? "c3dprints@email.moosedesk.com";
const FROM = Deno.env.get("RESEND_FROM") ?? "MakerQ <support@makerq.io>";
const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY") ?? "";
const SUPPORT = "c3dprints@email.moosedesk.com";
const RECAPTCHA_SECRET = Deno.env.get("RECAPTCHA_SECRET_KEY") ?? "";
const ALLOWED_HOSTS = new Set(["makerq.io", "www.makerq.io"]);

// Verify a reCAPTCHA v2 token with Google. Tokens are single-use and expire
// after 2 minutes, so this runs only once the form fields have validated.
async function verifyRecaptcha(token: string, ip: string | null): Promise<boolean> {
  if (!token) return false;
  const form = new URLSearchParams({ secret: RECAPTCHA_SECRET, response: token });
  if (ip) form.append("remoteip", ip);
  try {
    const r = await fetch("https://www.google.com/recaptcha/api/siteverify", { method: "POST", body: form });
    const d = await r.json();
    if (!d.success) console.warn("reCAPTCHA rejected", d["error-codes"]);
    return d.success === true && ALLOWED_HOSTS.has(d.hostname);
  } catch (e) {
    console.error("reCAPTCHA verify error", e);
    return false;
  }
}

function corsHeaders(origin: string | null): HeadersInit {
  const allow = origin && ALLOWED.has(origin) ? origin : "https://makerq.io";
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Vary": "Origin",
  };
}
function esc(s: string): string {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string));
}
const isEmail = (e: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);

Deno.serve(async (req) => {
  const origin = req.headers.get("origin");
  const cors = corsHeaders(origin);
  const jsonHeaders = { ...cors, "content-type": "application/json" };

  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405, headers: jsonHeaders });

  let body: Record<string, string> = {};
  try {
    const ct = req.headers.get("content-type") || "";
    if (ct.includes("application/json")) body = await req.json();
    else { const fd = await req.formData(); fd.forEach((v, k) => (body[k] = String(v))); }
  } catch {
    return new Response(JSON.stringify({ error: "Bad request" }), { status: 400, headers: jsonHeaders });
  }

  const next = (body._next || "").toString().trim();
  // Native (form POST) responses redirect; AJAX responses return JSON.
  const ok = () => next
    ? new Response(null, { status: 303, headers: { ...cors, Location: next } })
    : new Response(JSON.stringify({ success: true }), { headers: jsonHeaders });
  const fail = (msg: string, code: number) => next
    ? new Response(
        `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">` +
        `<body style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0b1623;color:#ddeeff;text-align:center;padding:64px 24px">` +
        `<h2 style="margin:0 0 10px">Sorry, that didn't go through</h2><p style="color:#9fb6d0">${esc(msg)}</p>` +
        `<p>Please email us at <a style="color:#33ccff" href="mailto:${SUPPORT}">${SUPPORT}</a>.</p>` +
        `<p style="margin-top:22px"><a style="color:#33ccff" href="https://makerq.io/contact">Back to the form</a></p></body>`,
        { status: code, headers: { ...cors, "content-type": "text/html; charset=utf-8" } })
    : new Response(JSON.stringify({ error: msg }), { status: code, headers: jsonHeaders });

  // Honeypot: real users never see or fill these hidden fields; bots fill every
  // field. Pretend success so the bot doesn't learn it was dropped.
  if ((body._honey || "").toString().trim() ||
      (body.website || "").toString().trim() ||
      (body.url || "").toString().trim()) return ok();
  // Time-trap: a genuine person can't read the form and submit in under ~2.5s.
  const ts = parseInt((body.ts || "").toString(), 10);
  if (ts && Date.now() - ts < 2500) return ok();

  const name = (body.name || "").toString().trim();
  const email = (body.email || "").toString().trim();
  const message = (body.message || "").toString().trim();
  const company = (body.company || "").toString().trim();
  const phone = (body.phone || "").toString().trim();

  if (!name) return fail("Please enter your name.", 422);
  if (!isEmail(email)) return fail("Please enter a valid email address.", 422);
  if (!message) return fail("Please add a short message.", 422);
  if (message.length > 5000) return fail("Message is too long.", 422);
  if (!RESEND_API_KEY) return fail("Server not configured.", 500);

  // Captcha: enforced once RECAPTCHA_SECRET_KEY is set (lets the page and the
  // function deploy in either order without dropping real messages).
  if (RECAPTCHA_SECRET) {
    const ip = req.headers.get("cf-connecting-ip") ?? req.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? null;
    const token = (body["g-recaptcha-response"] || "").toString();
    if (!(await verifyRecaptcha(token, ip))) {
      return fail("We couldn't verify you're human. Please go back, refresh the page, and try again.", 403);
    }
  } else {
    console.warn("RECAPTCHA_SECRET_KEY not set; captcha not enforced");
  }

  const html =
    `<h2 style="margin:0 0 12px">New MakerQ contact</h2>` +
    `<p><strong>Name:</strong> ${esc(name)}</p><p><strong>Email:</strong> ${esc(email)}</p>` +
    (company ? `<p><strong>Company:</strong> ${esc(company)}</p>` : "") +
    (phone ? `<p><strong>Phone:</strong> ${esc(phone)}</p>` : "") +
    `<p><strong>Message:</strong></p><p>${esc(message).replace(/\n/g, "<br>")}</p>`;
  const text =
    `New MakerQ contact\n\nName: ${name}\nEmail: ${email}\n` +
    (company ? `Company: ${company}\n` : "") + (phone ? `Phone: ${phone}\n` : "") +
    `\nMessage:\n${message}`;

  const resp = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${RESEND_API_KEY}`, "content-type": "application/json" },
    body: JSON.stringify({ from: FROM, to: [TO], reply_to: email, subject: `New MakerQ contact from ${name}`, html, text }),
  });
  if (!resp.ok) {
    console.error("Resend error", resp.status, await resp.text());
    return fail("Could not send your message right now.", 502);
  }
  return ok();
});
