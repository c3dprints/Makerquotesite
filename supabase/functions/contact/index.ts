// MakerQ contact-form relay (Supabase Edge Function).
// Receives the makerq.io contact form, validates it, and sends the message via
// Resend FROM a verified makerq.io address (so it passes SPF/DKIM and MooseDesk
// ticketizes it instead of spam-filtering it), with reply-to set to the sender.
//
// Deploy:
//   supabase functions deploy contact --no-verify-jwt --project-ref enyimtvgqzmpaiaeiyxj
// Secrets (Dashboard > Edge Functions > Secrets, or `supabase secrets set`):
//   RESEND_API_KEY   = <your Resend API key>
//   CONTACT_TO       = c3dprints@email.moosedesk.com        (optional, this is the default)
//   RESEND_FROM      = MakerQ <support@makerq.io>           (optional; must be a Resend-verified domain)

const ALLOWED_ORIGINS = new Set([
  "https://makerq.io",
  "https://www.makerq.io",
]);
const TO = Deno.env.get("CONTACT_TO") ?? "c3dprints@email.moosedesk.com";
const FROM = Deno.env.get("RESEND_FROM") ?? "MakerQ <support@makerq.io>";
const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY") ?? "";

function corsHeaders(origin: string | null): HeadersInit {
  const allow = origin && ALLOWED_ORIGINS.has(origin) ? origin : "https://makerq.io";
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Vary": "Origin",
  };
}
function esc(s: string): string {
  return String(s).replace(/[&<>"]/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string
  ));
}
const isEmail = (e: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);

Deno.serve(async (req) => {
  const origin = req.headers.get("origin");
  const headers = { ...corsHeaders(origin), "content-type": "application/json" };

  if (req.method === "OPTIONS") return new Response("ok", { headers });
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405, headers });
  }

  // Parse JSON or form-encoded
  let body: Record<string, string> = {};
  try {
    const ct = req.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      body = await req.json();
    } else {
      const fd = await req.formData();
      fd.forEach((v, k) => (body[k] = String(v)));
    }
  } catch {
    return new Response(JSON.stringify({ error: "Bad request" }), { status: 400, headers });
  }

  // Honeypot: silently accept + drop bots
  if ((body._honey || "").toString().trim()) {
    return new Response(JSON.stringify({ success: true }), { headers });
  }

  const name = (body.name || "").toString().trim();
  const email = (body.email || "").toString().trim();
  const message = (body.message || "").toString().trim();
  const company = (body.company || "").toString().trim();
  const phone = (body.phone || "").toString().trim();

  if (!name) return new Response(JSON.stringify({ error: "Please enter your name." }), { status: 422, headers });
  if (!isEmail(email)) return new Response(JSON.stringify({ error: "Please enter a valid email address." }), { status: 422, headers });
  if (!message) return new Response(JSON.stringify({ error: "Please add a short message." }), { status: 422, headers });
  if (message.length > 5000) return new Response(JSON.stringify({ error: "Message is too long." }), { status: 422, headers });
  if (!RESEND_API_KEY) return new Response(JSON.stringify({ error: "Server not configured." }), { status: 500, headers });

  const html =
    `<h2 style="margin:0 0 12px">New MakerQ contact</h2>` +
    `<p><strong>Name:</strong> ${esc(name)}</p>` +
    `<p><strong>Email:</strong> ${esc(email)}</p>` +
    (company ? `<p><strong>Company:</strong> ${esc(company)}</p>` : "") +
    (phone ? `<p><strong>Phone:</strong> ${esc(phone)}</p>` : "") +
    `<p><strong>Message:</strong></p><p>${esc(message).replace(/\n/g, "<br>")}</p>`;
  const text =
    `New MakerQ contact\n\nName: ${name}\nEmail: ${email}\n` +
    (company ? `Company: ${company}\n` : "") +
    (phone ? `Phone: ${phone}\n` : "") +
    `\nMessage:\n${message}`;

  const resp = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { "Authorization": `Bearer ${RESEND_API_KEY}`, "content-type": "application/json" },
    body: JSON.stringify({
      from: FROM,
      to: [TO],
      reply_to: email,
      subject: `New MakerQ contact from ${name}`,
      html,
      text,
    }),
  });

  if (!resp.ok) {
    console.error("Resend error", resp.status, await resp.text());
    return new Response(JSON.stringify({ error: "Could not send your message right now." }), { status: 502, headers });
  }
  return new Response(JSON.stringify({ success: true }), { headers });
});
