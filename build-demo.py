#!/usr/bin/env python3
"""Rebuild demo/app.html from the CURRENT app source (admin.html).

    "D:/git projects/printcost/c3dprints-quote-portal/backend/backend/.buildvenv/Scripts/python.exe" build-demo.py
    (or set MAKERQ_REPO to the c3dprints-quote-portal checkout)

Boots the real backend with sample data, records the API responses the UI
needs, then writes demo/app.html: the real admin UI + a fetch mock serving
that canned data. Demo-specific patches: auto-login, Settings hidden and
disabled (with a toast), smaller header logo for the framed view, demo pill.
Run this whenever admin.html changes so the demo matches the app.
"""

import datetime, json, os, re, signal, subprocess, sys, tempfile, time
import urllib.request

_REPO_CANDIDATES = [os.environ.get("MAKERQ_REPO") or "",
                    "D:/git projects/printcost/c3dprints-quote-portal",
                    os.path.expanduser("~/Documents/c3dprints-quote-portal")]
REPO = next(p for p in _REPO_CANDIDATES if p and os.path.isdir(p))
# The live app tree is backend/backend (main.py + updater.py); older checkouts had it in backend/.
BACKEND = next(p for p in (os.path.join(REPO, "backend", "backend"), os.path.join(REPO, "backend"))
               if os.path.isfile(os.path.join(p, "main.py")))
SITE = os.path.dirname(os.path.abspath(__file__))
PORT = 8856
BASE = f"http://127.0.0.1:{PORT}"
APP_VERSION = re.search(r'VERSION\s*=\s*"([^"]+)"',
                        open(os.path.join(BACKEND, "updater.py"), encoding="utf-8").read()).group(1)
TODAY = datetime.date.today()


def days_from_today(n):
    return (TODAY + datetime.timedelta(days=n)).isoformat()

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

def demo_license():
    """Sign the sample "Demo Shop" lifetime license.

    Uses the vendor key when this machine has it. Otherwise it makes a throwaway Ed25519
    pair that lives only in memory for this run: the temporary recording server below is
    told to trust its public half, the shipped app is untouched, and the demo page never
    contains a key (only the /admin/license status, which has no key in it)."""
    try:
        gen_license._load_private_key("")
        return gen_license.mint_key("Demo Shop", "demo@makerq.io", "lifetime", 0)[0], None
    except SystemExit:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
        priv = ed25519.Ed25519PrivateKey.generate()
        raw = priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                 serialization.NoEncryption())
        pub = priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        print("vendor key not found: signing the demo license with a throwaway key")
        return gen_license.mint_key("Demo Shop", "demo@makerq.io", "lifetime", 0, private_key=raw.hex())[0], pub.hex()


def record_canned():
    data_dir = tempfile.mkdtemp(prefix="mq_demo_")
    key, demo_pub = demo_license()
    json.dump({"license_key": key}, open(os.path.join(data_dir, "license.json"), "w"))
    env = dict(os.environ, DB_ENGINE="sqlite", SQLITE_PATH=os.path.join(data_dir, "c3d.db"),
               STORAGE_BACKEND="local", UPLOAD_DIR=os.path.join(data_dir, "uploads"),
               LICENSE_STATE_PATH=os.path.join(data_dir, "license.json"),
               JWT_SECRET="demo", ADMIN_USERNAME="admin", ADMIN_PASSWORD="admin", PORT=str(PORT),
               MAKERQ_DATA_DIR=data_dir, MAKERQ_CLOUD_BETA="0")
    if demo_pub:
        cmd = [sys.executable, "-c",
               "import sys, licensing; licensing.LICENSE_PUBLIC_KEY_HEX = sys.argv[1]; import uvicorn; "
               "uvicorn.run('main:app', host='127.0.0.1', port=int(sys.argv[2]), log_level='warning')",
               demo_pub, str(PORT)]
    else:
        cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
               "--port", str(PORT), "--log-level", "warning"]
    proc = subprocess.Popen(cmd, cwd=BACKEND, env=env)
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen(BASE + "/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        tok = http("POST", "/admin/login", body={"username": "admin", "password": "admin"})["token"]
        try:
            http("PUT", "/admin/settings/project-number", tok,
                 {"enabled": True, "prefix": "MQ-", "suffix": "", "digits": 4, "next": 1})
        except Exception as ex:
            print("project numbers:", ex)
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
                 "delivery_method": "Ship", "deadline": days_from_today(10)})
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
        # Folders, including a subfolder, so the demo shows the folder tree and drag and drop.
        try:
            ids = {r.get("name"): r["id"] for r in http("GET", "/admin/requests", tok)}
            cos = http("POST", "/admin/folders", tok, {"name": "Cosplay"})
            cos_id = (cos.get("folder") or cos).get("id")
            hel = http("POST", "/admin/folders", tok, {"name": "Helmets", "parent_id": cos_id})
            hel_id = (hel.get("folder") or hel).get("id")
            dr = http("POST", "/admin/folders", tok, {"name": "Drone builds"})
            dr_id = (dr.get("folder") or dr).get("id")
            for who, fid in (("Jordan Alvarez", hel_id), ("Marisol Chen", dr_id), ("Devin Wright", cos_id)):
                if who in ids and fid:
                    http("PATCH", f"/admin/requests/{ids[who]}/folder", tok, {"folder_id": fid})
        except Exception as ex:
            print("folders:", ex)
        try:
            http("POST", "/admin/edit-lock/acquire", tok, {"device": "Demo", "force": True})
        except Exception:
            pass
        canned = {}
        for ep in ["/health", "/admin/requests", "/admin/license", "/admin/analytics", "/admin/account",
                   "/admin/settings/email", "/admin/settings/smtp", "/admin/settings/shop-links",
                   "/admin/settings/pricing", "/admin/forms", "/admin/production-queue",
                   "/admin/folders", "/admin/printers", "/admin/edit-lock", "/cloud/info",
                   "/admin/settings/project-number", "/admin/settings/invoice", "/admin/settings/inventory",
                   "/admin/settings/workform", "/admin/settings/roll-products", "/admin/settings/supplies",
                   "/admin/settings/quote-template", "/admin/settings/checkout-links",
                   "/admin/settings/auto-logout", "/admin/failures/summary"]:
            try:
                canned[ep] = http("GET", ep, tok)
            except Exception as ex:
                print("skip", ep, ex)
        return canned
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)

def enrich(canned):
    """Fill in the 'blanks' so a viewer sees populated panels: AI triage summary,
    structured quote data, uploaded files, and a per-customer email log. Also bump
    the /health version so the footer isn't stale."""
    try:
        canned.setdefault("/health", {})["version"] = APP_VERSION
    except Exception:
        pass
    # Mark the demo account fully set up so the first-run "Welcome to MakerQ"
    # email-gate modal (shown when email_configured is falsy) doesn't block the UI.
    try:
        acct = canned.get("/admin/account")
        if not isinstance(acct, dict):
            acct = {}
        acct["email_configured"] = True
        acct["admin_email"] = acct.get("admin_email") or "demo@makerq.io"
        acct["username"] = acct.get("username") or "admin"
        acct["password_is_default"] = False
        canned["/admin/account"] = acct
    except Exception:
        pass
    # The seed requests carry no prices/payments, so the analytics view is all
    # zeros. Fill in coherent numbers (4 approved-or-beyond of 6 quotes sent, a
    # handful of completed/paid jobs) so the dashboard reads like a real shop.
    try:
        a = canned.get("/admin/analytics")
        if isinstance(a, dict):
            a.update({
                "quotes_sent_count": 6,        # conversion = 4 of 6 -> ~67%
                "approved_or_beyond_count": 4,
                "average_quote": 78.5,
                "quoted_open_value": 214.0,    # 2 open quotes still out
                "active_job_value": 312.0,     # approved + printing in progress
                "revenue_tracked": 402.0,
                "actual_cost_tracked": 179.0,
                "estimated_profit": 223.0,     # margin = 223/402 -> ~55%
                "collected_revenue": 402.0,
                "paid_orders_count": 3,
            })
    except Exception:
        pass
    reqs = canned.get("/admin/requests", []) or []
    by_name = {r.get("name"): r for r in reqs}
    emails = {}

    def stl(name, grams, hours):
        return {"original_filename": name, "filename": name, "size_bytes": int(grams * 1024 * 1.7),
                "stl_analysis": {"estimated_grams": grams, "estimated_print_hours": hours,
                                 "bounding_box_mm": [82.4, 61.0, 45.2], "triangles": 128444}}

    def ai(material, complexity, mult, grams, hours, price, flags):
        lo, hi = round(price * 0.9, 2), round(price * 1.15, 2)
        return {"recommended_material": material, "complexity": complexity, "confidence": "High",
                "estimated_grams": grams, "estimated_hours": hours, "fail_rate": 10,
                "price_min": lo, "price_max": hi, "complexity_multiplier": mult, "risk_flags": flags}

    plan = {
        "Owen Brooks": dict(material="PLA Matte", complexity="Moderate", mult=1.1, grams=42, hours=5.5,
                            price=34.0, files=[("phone-stand-v3.stl", 42, 5.5)],
                            flags=["Overhang on the neck rest, add supports", "Thin 1.2mm base, verify bed adhesion"],
                            summary="Desk phone stand in matte black. Single-part print, low risk. "
                                    "Recommend 15% gyroid infill and tree supports under the lip. "
                                    "About 42g of PLA and ~5.5h on a 0.4mm nozzle at 0.2mm layers."),
        "Marisol Chen": dict(material="PETG Carbon", complexity="Hard", mult=1.5, grams=210, hours=14.0,
                             price=96.0, files=[("fpv-frame-arm.stl", 120, 8.0), ("fpv-frame-body.stl", 90, 6.0)],
                             flags=["Carbon-fill needs a hardened nozzle", "Functional part, print walls at 4 perimeters"],
                             summary="FPV drone frame, carbon look. Two structural parts, functional load. "
                                     "Suggest PETG-CF, 4 perimeters, 40% infill for stiffness. Higher fail risk, "
                                     "priced with a 1.5x complexity factor."),
        "Devin Wright": dict(material="Resin (Grey)", complexity="Moderate", mult=1.25, grams=95, hours=9.5,
                             price=120.0, files=[("miniatures-set-12.stl", 95, 9.5)],
                             flags=["12 minis on one plate, watch for cupping", "Hollow + drain holes recommended"],
                             summary="Tabletop miniatures set of 12 in grey primer resin. Nest on the plate, "
                                     "hollow to save material, add drain holes. ~95g resin, ~9.5h print + cure."),
    }
    extra = {
        "Owen Brooks": dict(phone="(415) 555-0142", use_case="Desk accessory", due=days_from_today(3)),
        "Marisol Chen": dict(phone="(408) 555-0177", use_case="FPV racing drone", due=days_from_today(6)),
        "Devin Wright": dict(phone="(503) 555-0119", use_case="Tabletop gaming", due=days_from_today(9)),
    }
    for name, cfg in plan.items():
        r = by_name.get(name)
        if not r:
            continue
        x = extra.get(name, {})
        r["phone"] = x.get("phone")
        r["use_case"] = x.get("use_case")
        r["due_date"] = x.get("due")
        r["final_price"] = cfg["price"]
        r["quoted_price"] = cfg["price"]
        r["deposit_paid"] = True
        r["ai_summary"] = cfg["summary"]
        r["ai_quote_structured"] = ai(cfg["material"], cfg["complexity"], cfg["mult"],
                                       cfg["grams"], cfg["hours"], cfg["price"], cfg["flags"])
        r["ai_quote_assist"] = (f"AI analysis for {name}: ~{cfg['grams']}g of {cfg['material']}, "
                                f"about {cfg['hours']}h. Suggested price ${cfg['price']:.2f}. "
                                f"{cfg['summary'].split('. ')[0]}.")
        r["uploaded_files"] = [stl(fn, g, h) for (fn, g, h) in cfg["files"]]

    # per-customer email log for a few requests that have been quoted/approved
    log_plan = {"Owen Brooks": [("Quote sent", True), ("Checkout link sent", True)],
                "Marisol Chen": [("Quote sent", True), ("Approval link sent", True), ("Order approved", True)],
                "Lena Fischer": [("Quote sent", True), ("Tracking link sent", True), ("Order completed", True)]}
    stamps = [days_from_today(-4) + "T15:04:00", days_from_today(-3) + "T09:22:00", days_from_today(-3) + "T16:41:00"]
    for name, items in log_plan.items():
        r = by_name.get(name)
        if not r:
            continue
        rid = r.get("id")
        emails[str(rid)] = {"email": r.get("email", ""), "count": len(items),
                            "emails": [{"request_id": rid, "label": subj, "ok": ok, "sent_at": stamps[i % len(stamps)]}
                                       for i, (subj, ok) in enumerate(items)]}
    canned["__emails__"] = emails
    return canned

def build(canned):
    _cands = [os.path.join(REPO, "backend", "admin.html"), os.path.join(REPO, "admin.html")]
    admin_path = next((p for p in _cands if os.path.exists(p)), _cands[-1])
    admin = open(admin_path, encoding="utf-8").read()
    print("admin source:", admin_path)
    shim = """<script>
/* ===== MakerQ interactive demo shim: mock backend, sample data, nothing saved ===== */
window.__DEMO__ = """ + json.dumps(canned) + """;
try{ localStorage.setItem("c3d_admin_token","demo-token"); }catch(e){}
/* Pre-dismiss the first-run guided-tour prompt so the demo opens straight to the board. */
try{ localStorage.setItem("mq_tour_offered","1"); localStorage.setItem("mq_tour_done","1"); }catch(e){}
(function(){
  var D = window.__DEMO__;
  var S={kwh:0.25,watts:150,spool_usd:25,spool_g:1000,nozzle_cost:12,nozzle_hours:600,
         sheet_cost:30,sheet_prints:800,shipping:8,boxing:2,tax:7,markup:100,labor_rate:25};
  function mny(v){ return Math.round(v*100)/100; }
  function demoQuoteText(q,h,g,unit,total,ship){
    var price = q>1 ? "Estimated quote: $"+total.toFixed(2)+" total ($"+unit.toFixed(2)+" each)"
                    : "Estimated quote: $"+unit.toFixed(2);
    var sh = ship ? "Shipping is included in this estimate." : "Shipping/pickup will be handled separately.";
    return "Hi! Thanks for sending over the details.\\n\\n"+price+"\\n\\nEstimated print time: "+(h*q).toFixed(1)+
      " hours total\\nEstimated material use: "+(g*q).toFixed(1)+"g total\\n"+sh+
      "\\n\\nThis quote is based on the information provided and may change if the file needs repair, resizing, extra supports, or additional finishing.\\n\\nIf you'd like to move forward, I can confirm the final details and get it added to the print queue.";
  }
  function demoCalc(p){
    var q=Math.max(1, p.quantity|0 || 1), g=p.grams, h=p.hours;
    var fil=g*(S.spool_usd/S.spool_g), elec=(S.watts/1000)*h*S.kwh;
    var noz=(S.nozzle_cost/S.nozzle_hours)*h, sheet=S.sheet_cost/S.sheet_prints;
    var shipC=p.include_shipping?S.shipping:0, labor=(p.labor_minutes||0)/60*S.labor_rate;
    var direct=fil+elec+noz+sheet+S.boxing+shipC+labor+(p.cad_fee||0)+(p.rush_fee||0);
    var withFail=direct*(1/(1-(p.fail_rate||0)/100));
    var adj=withFail*(p.complexity_multiplier||1);
    var tax=adj*(S.tax/100), sell=adj*(1+S.markup/100), profit=sell-adj;
    return {quantity:q,
      per_unit:{grams:mny(g),hours:mny(h),cost_to_make:mny(adj),tax:mny(tax),
                suggested_sell_price:mny(sell),profit:mny(profit)},
      totals:{grams:mny(g*q),hours:mny(h*q),cost_to_make:mny(adj*q),tax:mny(tax*q),
              suggested_sell_price:mny(sell*q),profit:mny(profit*q)},
      breakdown_per_unit:{filament:mny(fil),electricity:mny(elec),nozzle_wear:mny(noz),
        print_sheet_wear:mny(sheet),packaging:mny(S.boxing),shipping:mny(shipC),labor:mny(labor),
        cad_fee:mny(p.cad_fee||0),rush_fee:mny(p.rush_fee||0),fail_overhead:mny(withFail-direct),
        complexity_added_cost:mny(adj-withFail)},
      customer_quote:demoQuoteText(q,h,g,sell,sell*q,p.include_shipping)};
  }
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
    if (path === "/calculate") {
      if(!body.grams || body.grams<=0 || !body.hours || body.hours<=0)
        return J({detail:"Enter grams and print hours first."}, 400);
      return J(demoCalc(body));
    }
    if (method === "GET") {
      if (D[path] !== undefined) return J(D[path]);
      var m = path.match(/^\\/admin\\/requests\\/(\\d+)$/);
      if (m) { var r=(D["/admin/requests"]||[]).find(function(x){return x.id==m[1]}); return J(r||{}); }
      if (/portal-link$/.test(path)) return J({url:"https://makerq-demo.example/portal/sample"});
      var em = path.match(/^\\/admin\\/requests\\/(\\d+)\\/emails$/);
      if (em) { var E=(D["__emails__"]||{})[em[1]]; return J(E||{emails:[],count:0,email:""}); }
      return J({});
    }
    var list = D["/admin/requests"]||[];
    function findReq(id){ return list.find(function(r){ return Number(r.id)===Number(id); }); }
    var F = D["/admin/folders"] = (D["/admin/folders"]||[]);
    function recount(){ F.forEach(function(f){ f.count = list.filter(function(r){
      return Number(r.folder_id)===Number(f.id) && r.status!=="Archived"; }).length; }); }
    if (/^\\/admin\\/edit-lock\\//.test(path)) return J(Object.assign({success:true}, D["/admin/edit-lock"]||{}));
    var mv = path.match(/^\\/admin\\/requests\\/(\\d+)\\/folder$/);
    if (mv) { var rq=findReq(mv[1]); if(rq){ rq.folder_id = body.folder_id==null?null:Number(body.folder_id); } recount();
      return J({success:true, request:{id:Number(mv[1]), folder_id:rq?rq.folder_id:null}}); }
    if (path === "/admin/folders" && method === "POST") {
      var fid = F.length ? Math.max.apply(null, F.map(function(f){return f.id}))+1 : 1;
      var nf = {id:fid, name:String(body.name||"New folder"), position:F.length+1,
                parent_id:body.parent_id==null?null:Number(body.parent_id), count:0};
      F.push(nf); return J(Object.assign({success:true, folder:nf}, nf));
    }
    if ((path === "/admin/folders/layout" || path === "/admin/folders/order") && method === "PUT") {
      (body.items||body.ids||[]).forEach(function(it, i){ var id = typeof it==="object" ? it.id : it;
        var f = F.find(function(x){return Number(x.id)===Number(id)}); if(!f) return;
        f.position = i+1; if (typeof it==="object") f.parent_id = it.parent_id==null?null:Number(it.parent_id); });
      F.sort(function(a,b){return a.position-b.position}); return J({success:true, folders:F});
    }
    var fm = path.match(/^\\/admin\\/folders\\/(\\d+)$/);
    if (fm) { var fo = F.find(function(x){return Number(x.id)===Number(fm[1])});
      if (method === "PATCH" && fo && body.name) { fo.name = String(body.name); return J(Object.assign({success:true, folder:fo}, fo)); }
      if (method === "DELETE" && fo) { var up = fo.parent_id==null?null:fo.parent_id;
        list.forEach(function(r){ if(Number(r.folder_id)===Number(fo.id)) r.folder_id = up; });
        F.forEach(function(x){ if(Number(x.parent_id)===Number(fo.id)) x.parent_id = up; });
        F.splice(F.indexOf(fo),1); recount(); return J({success:true}); } }
    var mid = path.match(/^\\/admin\\/requests\\/(\\d+)\\/([a-z-]+)$/);
    if (mid) {
      var r = findReq(mid[1]); var act = mid[2];
      if (!r) return J({detail:"Not found"}, 404);
      if (act === "status" && body.status) { r.status = body.status; return J({success:true, status:r.status, request:r}); }
      if (act === "archive") { r.status = "Archived"; return J({success:true, request:r}); }
      if (act === "duplicate") {
        var nid1 = Math.max.apply(null, list.map(function(x){return x.id||0})) + 1;
        var cl = JSON.parse(JSON.stringify(r)); cl.id = nid1; cl.status = "New";
        cl.created_at = new Date().toISOString(); cl.final_price = null; cl.paid = false;
        list.unshift(cl); return J({success:true, new_request:cl, request:cl});
      }
      if (act === "auto-price") {
        // demo STL-style estimate; the UI then runs the calculator with these
        return J({inputs:{grams:20, hours:6, fail_rate:10, complexity_multiplier:1.1,
                          quantity:r.quantity||1}, source:"demo STL estimate"});
      }
      if (act === "ai-quote-assist") {
        var est = demoCalc({grams:20, hours:6, quantity:r.quantity||1, fail_rate:10,
                            complexity_multiplier:1.1, include_shipping:true});
        r.ai_quote_assist = "Demo AI analysis for "+(r.name||"this request")+": ~20g of "+
          (r.material_preference||"PLA")+", about 6 print hours. Suggested price $"+
          est.per_unit.suggested_sell_price.toFixed(2)+" per unit. Watch overhangs; add supports if needed.";
        r.ai_quote_structured = {recommended_material:(r.material_preference||"PLA"), complexity:"Moderate",
          confidence:"High", estimated_grams:20, estimated_hours:6, fail_rate:10,
          price_min:Math.round(est.per_unit.suggested_sell_price*0.9*100)/100,
          price_max:Math.round(est.per_unit.suggested_sell_price*1.15*100)/100,
          complexity_multiplier:1.1,
          risk_flags:["Demo data: verify wall thickness before printing"],
          customer_reply:est.customer_quote};
        return J({success:true, request:r});
      }
      if (act === "payment") { Object.assign(r, body); return J({success:true, request:r}); }
      if (act === "details" || act === "job-details") {
        Object.keys(body).forEach(function(k){ if(body[k]!==undefined) r[k]=body[k]; });
        return J({success:true, request:r});
      }
      if (act === "send-quote") { r.status = (r.status==="New"||r.status==="Need Info")?"Quoted":r.status;
        return J({success:true, sent_to:(r.email||"customer@example.com"), demo:true, request:r}); }
      if (act === "send-checkout" || act === "send-portal-link" || act === "send-customer-orders" || act === "tracking")
        return J({success:true, sent_to:(r.email||"customer@example.com"), demo:true, request:r});
      if (act === "assign-printer") return J({success:true, request:r});
      return J({success:true, demo:true, request:r});
    }
    if (path === "/admin/requests" && method === "POST") {
      var nid = list.length ? Math.max.apply(null,list.map(function(r){return r.id||0}))+1 : 1;
      var nr = Object.assign({id:nid, status:"New", created_at:new Date().toISOString(), files:[]}, body);
      list.unshift(nr); return J(Object.assign({success:true}, nr));
    }
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
    demo, n = re.subn(r'<button[^>]*onclick="openEmailImport\(\)".*?</button>', "", demo, flags=re.S)
    print("settings buttons removed:", n)

    # after-app patches: disable ALL settings entry points + demo pill
    tail = """<script>
/* demo: settings disabled everywhere (setup checklist etc.) */
window.openEmailImport = function(){ try{ toast("Settings are disabled in this demo.","error"); }catch(e){} };
/* demo: prefill the quote calculator with a sample job on every selection */
(function(){
  function fill(){ var g=document.getElementById("grams"), h=document.getElementById("hours");
    if(g && !g.value) g.value="20"; if(h && !h.value) h.value="6"; }
  fill();
  var _sr = window.selectRequest;
  window.selectRequest = function(id){ var out=_sr(id); setTimeout(fill, 80); return out; };
})();
</script>
<div id="mq-demo-bar">Interactive demo, sample data, nothing is saved.<a href="../" target="_top">&larr; Back to MakerQ</a></div>
</body>"""
    assert demo.count("</body>") == 1
    demo = demo.replace("</body>", tail)
    if "<title>" in demo and "MakerQ Demo" not in demo:
        demo = demo.replace("<title>", "<title>MakerQ Demo - ", 1)
    out = os.path.join(SITE, "demo", "app.html")
    open(out, "w", encoding="utf-8", newline="\n").write(demo)
    print("wrote", out, round(len(demo) / 1024), "KB")

if __name__ == "__main__":
    build(enrich(record_canned()))
