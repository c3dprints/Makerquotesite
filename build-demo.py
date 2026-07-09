#!/usr/bin/env python3
"""Rebuild demo/app.html from the CURRENT app source (admin.html).

    ~/Documents/c3dprints-quote-portal/backend/.venv/bin/python build-demo.py

Boots the real backend with sample data, records the API responses the UI
needs, then writes demo/app.html: the real admin UI + a fetch mock serving
that canned data. Demo-specific patches: auto-login, Settings hidden and
disabled (with a toast), smaller header logo for the framed view, demo pill.
Run this whenever admin.html changes so the demo matches the app.
"""

import json, os, re, signal, subprocess, sys, tempfile, time
import urllib.request

REPO = os.path.expanduser("~/Documents/c3dprints-quote-portal")
SITE = os.path.dirname(os.path.abspath(__file__))
PORT = 8856
BASE = f"http://127.0.0.1:{PORT}"

sys.path.insert(0, os.path.join(REPO, "tools"))
import gen_license  # noqa: E402

def http(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(req, data, timeout=15) as r:
        return json.loads(r.read().decode())

def record_canned():
    data_dir = tempfile.mkdtemp(prefix="mq_demo_")
    key, _ = gen_license.mint_key("Demo Shop", "demo@makerq.io", "lifetime", 0)
    json.dump({"license_key": key}, open(os.path.join(data_dir, "license.json"), "w"))
    env = dict(os.environ, DB_ENGINE="sqlite", SQLITE_PATH=os.path.join(data_dir, "c3d.db"),
               STORAGE_BACKEND="local", UPLOAD_DIR=os.path.join(data_dir, "uploads"),
               LICENSE_STATE_PATH=os.path.join(data_dir, "license.json"),
               JWT_SECRET="demo", ADMIN_USERNAME="admin", ADMIN_PASSWORD="admin", PORT=str(PORT))
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
                             "--port", str(PORT), "--log-level", "warning"],
                            cwd=os.path.join(REPO, "backend"), env=env)
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen(BASE + "/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        tok = http("POST", "/admin/login", body={"username": "admin", "password": "admin"})["token"]
        seed = [("Jordan Alvarez", "jordan@example.com", "Cosplay helmet, smooth finish", "PLA", "Metallic Silver", "Quoted", 2),
                ("Marisol Chen", "marisol@example.com", "FPV drone frame, carbon look", "PETG", "Black", "Approved", 4),
                ("Devin Wright", "devin@example.com", "Tabletop miniatures set (12)", "Resin", "Grey Primer", "Printing", 12),
                ("Priya Nair", "priya@example.com", "Enclosure prototype for sensor", "ABS", "White", "New", 1),
                ("Sam Okafor", "sam@example.com", "Replacement planetary gear", "Nylon", "Natural", "Need Info", 3),
                ("Lena Fischer", "lena@example.com", "Architectural model, 1:100", "PLA", "White", "Completed", 1),
                ("Owen Brooks", "owen@example.com", "Desk phone stand, matte", "PLA", "Matte Black", "Quoted", 2),
                ("Hannah Lee", "hannah@example.com", "Custom keycaps, 6 unit", "Resin", "Translucent Blue", "Approved", 6)]
        for n, e, d, mt, c, s, q in seed:
            http("POST", "/admin/requests", tok, {"name": n, "email": e, "project_description": d,
                 "material_preference": mt, "color_preference": c, "quantity": q,
                 "delivery_method": "Ship", "deadline": "2026-07-25"})
        want = {n: s for (n, _, _, _, _, s, _) in seed}
        for r in http("GET", "/admin/requests", tok):
            nm = r.get("name")
            if nm in want and want[nm] != "New":
                try:
                    http("PATCH", f"/admin/requests/{r['id']}/status", tok, {"status": want[nm]})
                except Exception:
                    pass
        try:
            http("POST", "/admin/printers", tok, {"name": "Bambu X1C", "model": "X1 Carbon", "status": "Printing"})
        except Exception:
            pass
        canned = {}
        for ep in ["/health", "/admin/requests", "/admin/license", "/admin/analytics", "/admin/account",
                   "/admin/settings/email", "/admin/settings/smtp", "/admin/settings/shop-links",
                   "/admin/settings/pricing", "/admin/forms", "/admin/production-queue"]:
            try:
                canned[ep] = http("GET", ep, tok)
            except Exception as ex:
                print("skip", ep, ex)
        return canned
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)

def build(canned):
    admin = open(os.path.join(REPO, "admin.html")).read()
    shim = """<script>
/* ===== MakerQ interactive demo shim: mock backend, sample data, nothing saved ===== */
window.__DEMO__ = """ + json.dumps(canned) + """;
try{ localStorage.setItem("c3d_admin_token","demo-token"); }catch(e){}
(function(){
  var D = window.__DEMO__;
  function J(obj, status){
    return Promise.resolve(new Response(JSON.stringify(obj), {status: status||200, headers:{"Content-Type":"application/json"}}));
  }
  window.fetch = function(url, opts){
    opts = opts || {};
    var method = (opts.method || "GET").toUpperCase();
    var path = String(url).replace(/^https?:\\/\\/[^\\/]+/, "").split("?")[0];
    var body = {};
    try{ if(opts.body) body = JSON.parse(opts.body); }catch(e){}
    if (path === "/admin/login") return J({token:"demo-token"});
    if (method === "GET") {
      if (D[path] !== undefined) return J(D[path]);
      var m = path.match(/^\\/admin\\/requests\\/(\\d+)$/);
      if (m) { var r=(D["/admin/requests"]||[]).find(function(x){return x.id==m[1]}); return J(r||{}); }
      if (/portal-link$/.test(path)) return J({url:"https://makerq-demo.example/portal/sample"});
      return J({});
    }
    var ms = path.match(/^\\/admin\\/requests\\/(\\d+)\\/status$/);
    if (ms && body.status) {
      (D["/admin/requests"]||[]).forEach(function(r){ if(r.id==ms[1]) r.status=body.status; });
      return J({success:true, status:body.status});
    }
    if (path === "/admin/requests" && method === "POST") {
      var list = D["/admin/requests"]||[]; var nid = list.length ? Math.max.apply(null,list.map(function(r){return r.id||0}))+1 : 1;
      var nr = Object.assign({id:nid, status:"New", created_at:new Date().toISOString(), files:[]}, body);
      list.unshift(nr); return J(Object.assign({success:true}, nr));
    }
    if (/ai-quote-assist$/.test(path)) return J({success:true, suggestion:"Demo mode: the AI quote assistant drafts pricing and a customer-ready reply here (Pro tier)."});
    if (/send-quote$|send-checkout$|send-portal-link$/.test(path)) return J({success:true, sent_to:"customer@example.com", demo:true});
    return J({success:true, demo:true});
  };
})();
</script>
<style>
#mq-demo-bar{position:fixed;left:50%;transform:translateX(-50%);bottom:14px;z-index:5000;background:#162236;border:1px solid #ff6b1a;color:#ddeeff;font:600 13px -apple-system,Segoe UI,Roboto,Arial,sans-serif;padding:9px 16px;border-radius:999px;box-shadow:0 10px 30px rgba(0,0,0,.5);display:flex;gap:14px;align-items:center}
#mq-demo-bar a{color:#33ccff;text-decoration:none}#mq-demo-bar a:hover{text-decoration:underline}
/* framed-view sizing: smaller header logo */
header .brand img{height:56px!important}
</style>
"""
    marker = "<script>\nconst API_BASE="
    assert admin.count(marker) == 1, "API_BASE script marker not found"
    demo = admin.replace(marker, shim + marker)

    # remove the header Settings button (robust to inline style changes)
    demo, n = re.subn(r'<button[^>]*onclick="openEmailImport\(\)"[^>]*>Settings</button>', "", demo)
    print("settings buttons removed:", n)

    # after-app patches: disable ALL settings entry points + demo pill
    tail = """<script>
/* demo: settings disabled everywhere (setup checklist etc.) */
window.openEmailImport = function(){ try{ toast("Settings are disabled in this demo.","error"); }catch(e){} };
</script>
<div id="mq-demo-bar">Interactive demo, sample data, nothing is saved.<a href="../" target="_top">&larr; Back to MakerQ</a></div>
</body>"""
    assert demo.count("</body>") == 1
    demo = demo.replace("</body>", tail)
    if "<title>" in demo and "MakerQ Demo" not in demo:
        demo = demo.replace("<title>", "<title>MakerQ Demo - ", 1)
    out = os.path.join(SITE, "demo", "app.html")
    open(out, "w").write(demo)
    print("wrote", out, round(len(demo) / 1024), "KB")

if __name__ == "__main__":
    build(record_canned())
