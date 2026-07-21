// MakerQ /stats GA relay (Supabase Edge Function).
// Authenticates to the Google Analytics Data API with a service account and returns
// aggregated download/purchase stats for the hidden /stats dashboard. The service
// account credential stays server-side; the page just fetches JSON from here.
//
// Deploy:  supabase functions deploy ga-stats --no-verify-jwt --project-ref enyimtvgqzmpaiaeiyxj
// Secrets (Dashboard > Edge Functions > Secrets):
//   GA_PROPERTY_ID      = <your GA4 numeric property id, e.g. 123456789>   (NOT the G- id)
//   GA_SERVICE_ACCOUNT  = <the full service-account JSON, pasted as one value>
// The service account needs the "Google Analytics Data API" enabled and Viewer access
// on the GA4 property.

const ALLOWED = new Set(["https://makerq.io", "https://www.makerq.io"]);
const PROPERTY_ID = Deno.env.get("GA_PROPERTY_ID") ?? "";
const SA_RAW = Deno.env.get("GA_SERVICE_ACCOUNT") ?? "";
const DL = "file_download";
const BUY = "purchase";

function cors(origin: string | null): HeadersInit {
  const allow = origin && ALLOWED.has(origin) ? origin : "https://makerq.io";
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Vary": "Origin",
  };
}

function b64url(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function importKey(pem: string): Promise<CryptoKey> {
  const body = pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  const der = Uint8Array.from(atob(body), (c) => c.charCodeAt(0));
  return await crypto.subtle.importKey(
    "pkcs8", der.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"],
  );
}

async function accessToken(sa: any): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const tokenUri = sa.token_uri || "https://oauth2.googleapis.com/token";
  const enc = (o: unknown) => b64url(new TextEncoder().encode(JSON.stringify(o)));
  const unsigned = enc({ alg: "RS256", typ: "JWT" }) + "." +
    enc({ iss: sa.client_email, scope: "https://www.googleapis.com/auth/analytics.readonly",
          aud: tokenUri, exp: now + 3600, iat: now });
  const key = await importKey(sa.private_key);
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, new TextEncoder().encode(unsigned));
  const jwt = unsigned + "." + b64url(new Uint8Array(sig));
  const r = await fetch(tokenUri, {
    method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion: jwt }),
  });
  const j = await r.json();
  if (!j.access_token) throw new Error("token error: " + JSON.stringify(j));
  return j.access_token;
}

function eventFilter(name: string) {
  return { filter: { fieldName: "eventName", stringFilter: { value: name } } };
}

async function runReport(token: string, body: unknown) {
  const r = await fetch(
    `https://analyticsdata.googleapis.com/v1beta/properties/${PROPERTY_ID}:runReport`,
    { method: "POST", headers: { Authorization: `Bearer ${token}`, "content-type": "application/json" }, body: JSON.stringify(body) },
  );
  if (!r.ok) throw new Error("GA " + r.status + ": " + (await r.text()).slice(0, 300));
  return await r.json();
}

// rows -> [{name, count}]
function pairs(rep: any): { name: string; count: number }[] {
  return (rep.rows || []).map((row: any) => ({
    name: row.dimensionValues?.[0]?.value ?? "(unknown)",
    count: Number(row.metricValues?.[0]?.value ?? 0),
  }));
}
const sum = (a: { count: number }[]) => a.reduce((t, x) => t + x.count, 0);

Deno.serve(async (req) => {
  const origin = req.headers.get("origin");
  const headers = { ...cors(origin), "content-type": "application/json" };
  if (req.method === "OPTIONS") return new Response("ok", { headers });

  if (!PROPERTY_ID || !SA_RAW) {
    return new Response(JSON.stringify({ configured: false }), { headers });
  }
  try {
    const sa = JSON.parse(SA_RAW);
    const token = await accessToken(sa);
    const range = [{ startDate: "30daysAgo", endDate: "today" }];
    const [country, device, source, trend, buyCountry] = await Promise.all([
      runReport(token, { dateRanges: range, dimensions: [{ name: "country" }], metrics: [{ name: "eventCount" }], dimensionFilter: eventFilter(DL), orderBys: [{ metric: { metricName: "eventCount" }, desc: true }] }),
      runReport(token, { dateRanges: range, dimensions: [{ name: "deviceCategory" }], metrics: [{ name: "eventCount" }], dimensionFilter: eventFilter(DL), orderBys: [{ metric: { metricName: "eventCount" }, desc: true }] }),
      runReport(token, { dateRanges: range, dimensions: [{ name: "sessionSourceMedium" }], metrics: [{ name: "eventCount" }], dimensionFilter: eventFilter(DL), orderBys: [{ metric: { metricName: "eventCount" }, desc: true }] }),
      runReport(token, { dateRanges: range, dimensions: [{ name: "date" }], metrics: [{ name: "eventCount" }], dimensionFilter: eventFilter(DL), orderBys: [{ dimension: { dimensionName: "date" } }] }),
      runReport(token, { dateRanges: range, dimensions: [{ name: "country" }], metrics: [{ name: "eventCount" }], dimensionFilter: eventFilter(BUY), orderBys: [{ metric: { metricName: "eventCount" }, desc: true }] }),
    ]);
    const countries = pairs(country), devices = pairs(device), sources = pairs(source);
    const days = pairs(trend).map((d) => ({ date: d.name, count: d.count }));
    const purchaseCountries = pairs(buyCountry);
    return new Response(JSON.stringify({
      configured: true,
      range: "Last 30 days",
      totalDownloads: sum(countries),
      totalPurchases: sum(purchaseCountries),
      countries, devices, sources, days, purchaseCountries,
    }), { headers });
  } catch (e) {
    console.error(e);
    return new Response(JSON.stringify({ error: String(e).slice(0, 300) }), { status: 502, headers });
  }
});
