"""Read-only dashboard server (stdlib only): JSON API + single-page UI.
Security posture: binds 127.0.0.1 by default, no auth (put it behind your own auth proxy before exposing it),
CSP + nosniff headers, request bodies capped, all user-derived text inserted with textContent (no innerHTML)."""
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from .creators import score_creators

MAX_BODY = 20_000
HEADERS = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Cache-Control": "no-store",
           "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:"}


def _json(obj, status=200):
    return status, "application/json", json.dumps(obj, default=str).encode()

class App:
    def __init__(self, conn):
        self.conn, self.lock = conn, threading.Lock()

    def meta(self):
        return {"sample_rows": int(self.conn.execute("SELECT COUNT(*) c FROM creators WHERE is_sample=1").fetchone()["c"])}

    def route(self, method, raw_path, body):
        if method != "GET":
            return _json({"error": "method not allowed"}, 405)
        u = urlsplit(raw_path)
        p, q = u.path, parse_qs(u.query)
        with self.lock:
            if p == "/":
                return 200, "text/html; charset=utf-8", PAGE.encode()
            if p == "/healthz":
                return _json({"ok": True})
            if p == "/api/meta":
                return _json(self.meta())
            if p == "/api/creators":
                cats = tuple(c for c in q.get("categories", [""])[0].split(",") if c)
                return _json(score_creators(self.conn, categories=cats))
        return _json({"error": "not found"}, 404)


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def _run(self, method):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if n > MAX_BODY:
                    status, ctype, body = _json({"error": "payload too large"}, 413)
                else:
                    status, ctype, body = app.route(method, self.path, self.rfile.read(n) if n else b"")
            except Exception as exc:  # never leak a stack trace to the client
                print(f"error on {self.path}: {exc!r}", file=sys.stderr)
                status, ctype, body = _json({"error": "internal error"}, 500)
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for k, v in HEADERS.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self._run("GET")

        def do_POST(self):
            self._run("POST")

        def log_message(self, fmt_, *args):
            pass
    return Handler


def serve(conn, host="127.0.0.1", port=8000):
    srv = ThreadingHTTPServer((host, port), make_handler(App(conn)))
    print(f"dashboard on http://{host}:{port}  (read-only, no auth)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.server_close()


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CreatorScore</title><style>
:root{--paper:#f2ead8;--panel:#ebe2cb;--ink:#1c1a16;--muted:#6b6455;--rule:#cfc4a8;--accent:#c2410c;--cool:#1f4e5f;--good:#2f6b3a;--bad:#a4261b;
--serif:"Iowan Old Style","Palatino Linotype","Book Antiqua",Georgia,serif;--mono:ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root{--paper:#15130f;--panel:#1d1a14;--ink:#ece3cc;--muted:#a39a84;--rule:#3a3528;--accent:#f08a4b;--cool:#7fc0d4;--good:#7fc98a;--bad:#f08478}}
*{box-sizing:border-box}html,body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 var(--serif)}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.banner{background:var(--accent);color:var(--paper);font:600 12px var(--mono);letter-spacing:.08em;text-transform:uppercase;padding:6px 16px;text-align:center}
.wrap{display:grid;grid-template-columns:270px 1fr;min-height:100vh}
aside{border-right:1px solid var(--rule);padding:22px 0}
aside h2{font:600 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin:0 20px 10px}
.slate button{all:unset;display:flex;justify-content:space-between;gap:8px;width:100%;box-sizing:border-box;padding:9px 20px;cursor:pointer;border-left:3px solid transparent;border-bottom:1px solid var(--rule)}
.slate button:hover{background:var(--panel)}.slate button[aria-current=true]{border-left-color:var(--accent);background:var(--panel)}
.slate small{display:block;color:var(--muted);font:11px var(--mono);text-transform:uppercase;letter-spacing:.08em}
main{padding:26px 34px 60px;min-width:0}
.kicker{font:600 11px var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
h1{font:700 clamp(30px,4.4vw,52px)/1.02 var(--serif);letter-spacing:-.02em;margin:6px 0 18px}
.figs{display:grid;grid-template-columns:repeat(4,1fr);border-top:2px solid var(--ink);border-bottom:1px solid var(--rule);margin-bottom:22px}
.fig{padding:12px 16px;border-right:1px solid var(--rule)}.fig:last-child{border-right:0}
.fig b{display:block;font:600 clamp(20px,2.6vw,32px) var(--mono)}.fig span{font:11px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
nav.tabs{display:flex;gap:22px;border-bottom:1px solid var(--rule);margin-bottom:22px}
nav.tabs button{all:unset;cursor:pointer;padding:8px 0;font:600 12px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);border-bottom:2px solid transparent}
nav.tabs button[aria-selected=true]{color:var(--ink);border-bottom-color:var(--accent)}
.read{font-size:19px;max-width:64ch;margin:0 0 10px}
.badge{display:inline-block;font:600 11px var(--mono);letter-spacing:.06em;padding:3px 8px;border:1px solid currentColor;margin-bottom:18px}.ok{color:var(--good)}.fail{color:var(--bad)}
h3{font:600 11px var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin:26px 0 8px;border-bottom:1px solid var(--rule);padding-bottom:6px}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:7px 10px 7px 0;border-bottom:1px solid var(--rule);vertical-align:top}
th{font:600 11px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}td.n,th.n{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;padding-left:18px}
.dim{color:var(--muted)}.chip{font:600 11px var(--mono);padding:2px 6px;border:1px solid currentColor;text-transform:uppercase}
.bar{display:inline-block;height:8px;background:var(--cool);vertical-align:middle}.bar.neg{background:var(--accent)}
.call{border-left:3px solid var(--accent);background:var(--panel);padding:10px 14px;margin:8px 0}
svg text{font:11px var(--mono);fill:var(--muted)}.scroll{overflow-x:auto}
@media (max-width:820px){.wrap{grid-template-columns:1fr}aside{border-right:0;border-bottom:1px solid var(--rule);padding:12px 0 0}.slate{display:flex;overflow-x:auto}.slate button{flex:0 0 auto;width:auto;border-left:0;border-bottom:3px solid transparent}.slate button[aria-current=true]{border-bottom-color:var(--accent)}.figs{grid-template-columns:1fr 1fr}main{padding:20px 16px}}

.field{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin:0 0 18px}
select,textarea,button.act{font:14px var(--serif);color:var(--ink);background:var(--panel);border:1px solid var(--rule);padding:6px 10px}
textarea{width:100%;min-height:110px;resize:vertical;line-height:1.5}
button.act{cursor:pointer;font:600 12px var(--mono);letter-spacing:.08em;text-transform:uppercase;background:var(--ink);color:var(--paper);border-color:var(--ink)}
label.f{font:600 11px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted);display:flex;flex-direction:column;gap:4px}
mark{background:none;color:inherit;padding:0 3px;border-bottom:2px solid}
mark.ok{border-color:var(--good)}mark.unsupported{border-color:var(--bad);background:color-mix(in srgb,var(--bad) 14%,transparent)}
mark.misattributed{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 16%,transparent)}mark.style{border-color:var(--muted);border-bottom-style:dashed}
.legend{display:flex;gap:16px;flex-wrap:wrap;font:11px var(--mono);color:var(--muted);margin:8px 0 0}
.two{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:28px}@media (max-width:980px){.two{grid-template-columns:1fr}}
.pill{font:600 10px var(--mono);letter-spacing:.08em;text-transform:uppercase;padding:2px 6px;border:1px solid currentColor;margin-left:6px}
tr.sel td{background:var(--panel)}tr.click{cursor:pointer}tr.click:hover td{background:var(--panel)}
.wrap.single{grid-template-columns:1fr}
@media (max-width:820px){.wrap,.wrap.single{grid-template-columns:minmax(0,1fr)}aside,main{min-width:0}.slate{max-width:100vw}.figs{grid-template-columns:1fr 1fr}.fig{border-right:0;border-bottom:1px solid var(--rule)}}main{min-width:0}svg{max-width:100%;height:auto}@media (max-width:820px){th,td{padding:6px 6px 6px 0;font-size:13px}td.n,th.n{padding-left:6px}.bar2{max-width:44px}.chip{font-size:10px}}button.act.off{background:var(--panel);color:var(--ink);border-color:var(--rule)}.bar2{display:inline-block;height:10px;background:var(--cool);vertical-align:middle}.bar2.warn{background:var(--accent)}</style></head><body><div id="banner" class="banner" hidden>Synthetic demo data. Not real platform data.</div><div class="wrap single"><main><div class="kicker">Creator desk</div><h1 id="title">Who is worth the fee?</h1><div id="figs" class="figs"></div><section id="panel"></section></main></div><script>
"use strict";
const $=s=>document.querySelector(s);
function h(tag,attrs,...kids){const e=document.createElement(tag);for(const[k,v]of Object.entries(attrs||{})){if(k==="class")e.className=v;else if(k.startsWith("on"))e.addEventListener(k.slice(2),v);else e.setAttribute(k,v)}
 for(const c of kids.flat(Infinity)){if(c==null||c===false)continue;e.append(c.nodeType?c:document.createTextNode(String(c)))}return e}
function sv(tag,attrs,...kids){const e=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const[k,v]of Object.entries(attrs||{}))e.setAttribute(k,v);for(const c of kids.flat(Infinity))if(c!=null)e.append(typeof c==="string"?document.createTextNode(c):c);return e}
const api=async p=>{const r=await fetch(p);if(!r.ok)throw new Error(p+" "+r.status);return r.json()};
const pct=(x,d=0)=>x==null?"n/a":(x*100).toFixed(d)+"%";const big=v=>v>=1e6?(v/1e6).toFixed(2)+"M":v>=1e3?(v/1e3).toFixed(0)+"K":Math.round(v)+"";


const state={rows:[],sel:null,f:{platform:"",tier:"",category:"",hideHigh:false}};
const RC={high:"var(--accent)",medium:"#b8860b",low:"var(--cool)","insufficient data":"var(--muted)"};
const med=a=>{const s=a.filter(x=>x!=null).sort((x,y)=>x-y);return s.length?(s.length%2?s[(s.length-1)/2]:(s[s.length/2-1]+s[s.length/2])/2):null};
const filtered=()=>state.rows.filter(r=>(!state.f.platform||r.platform===state.f.platform)&&(!state.f.tier||r.tier===state.f.tier)&&(!state.f.category||r.category===state.f.category)&&(!state.f.hideHigh||r.risk.label!=="high"));
const usd=v=>v==null?"n/a":"$"+v.toFixed(2);
function figs(rows){const sc=rows.filter(r=>r.score!=null);$("#figs").replaceChildren(...[["Creators shown",String(rows.length)],["Median score",sc.length?med(sc.map(r=>r.score)).toFixed(1):"n/a"],["High-risk flagged",String(rows.filter(r=>r.risk.label==="high").length)],["Median CPM",usd(med(rows.map(r=>r.cost.cpm_usd)))]].map(([l,v])=>h("div",{class:"fig"},h("b",{},v),h("span",{},l))))}
function select(label,key,opts){const s=h("select",{onchange:e=>{state.f[key]=e.target.value;render()}},h("option",{value:""},"All"),opts.map(o=>h("option",{value:o},o)));s.value=state.f[key];return h("label",{class:"f"},label,s)}
function scatter(rows){const W=470,H=330,L=48,B=40,T=12,R=14,pts=rows.filter(r=>r.metrics.reach_ratio>0);if(!pts.length)return h("p",{class:"dim"},"No creators to plot.");
 const xs=pts.map(r=>Math.log10(r.metrics.reach_ratio)),x0=Math.floor(Math.min(...xs)),x1=Math.ceil(Math.max(...xs)+.001),ymax=Math.max(.05,Math.ceil(Math.max(...pts.map(r=>r.metrics.engagement_rate))*20)/20);
 const X=v=>L+(Math.log10(v)-x0)/(x1-x0)*(W-L-R),Y=v=>H-B-v/ymax*(H-B-T);
 const g=sv("svg",{viewBox:`0 0 ${W} ${H}`,width:"100%",role:"img","aria-label":"Reach ratio versus engagement rate, coloured by risk"});
 for(let i=0;i<=4;i++){const v=ymax*i/4;g.append(sv("line",{x1:L,x2:W-R,y1:Y(v),y2:Y(v),stroke:"var(--rule)"}),sv("text",{x:L-6,y:Y(v)+4,"text-anchor":"end"},(v*100).toFixed(0)+"%"))}
 for(let e=x0;e<=x1;e++)g.append(sv("line",{x1:X(10**e),x2:X(10**e),y1:T,y2:H-B,stroke:"var(--rule)"}),sv("text",{x:X(10**e),y:H-B+14,"text-anchor":"middle"},(10**e)>=1?String(10**e):String(10**e)));
 g.append(sv("text",{x:(L+W-R)/2,y:H-6,"text-anchor":"middle"},"views / followers (log scale)"),sv("text",{x:12,y:T+4},"engagement"));
 pts.forEach(r=>{const c=sv("circle",{cx:X(r.metrics.reach_ratio),cy:Y(r.metrics.engagement_rate),r:r===state.sel?8:5.5,fill:RC[r.risk.label]||"var(--muted)",opacity:r.fit?".85":".3",stroke:r===state.sel?"var(--ink)":"none","stroke-width":2,style:"cursor:pointer"},sv("title",{},`@${r.handle}: score ${r.score==null?"withheld":r.score}, risk ${r.risk.label}`));c.addEventListener("click",()=>{state.sel=r;render()});g.append(c)});
 return h("div",{},g,h("div",{class:"legend"},["high","medium","low","insufficient data"].map(k=>h("span",{},h("span",{style:`display:inline-block;width:9px;height:9px;border-radius:50%;background:${RC[k]};margin-right:5px`}),k+" risk"))))}
function detail(r){if(!r)return h("div",{class:"call"},"Click a creator in the table or on the plot to see exactly why it scores the way it does.");const m=r.metrics,p=r.percentiles;
 return h("div",{class:"call"},h("div",{style:"display:flex;justify-content:space-between;align-items:baseline"},h("b",{style:"font-size:20px"},"@"+r.handle),h("span",{class:"mono",style:"font-size:26px;font-weight:600"},r.score==null?"withheld":r.score.toFixed(1))),
 h("div",{class:"dim mono",style:"font-size:12px"},`${r.platform} · ${r.tier} · ${r.followers.toLocaleString()} followers · ${r.category||"no category"} · ${r.n_posts} posts · ${r.confidence} confidence`),
 h("table",{style:"margin-top:8px"},h("tbody",{},[["Median views",big(m.median_views)],["Engagement rate",pct(m.engagement_rate,1)],["Views / followers",pct(m.reach_ratio,1)],["Consistency (posts within 0.5-2x median)",pct(m.consistency)],["Percentile vs "+p.cohort,p.engagement==null?"n/a":`engagement ${p.engagement.toFixed(0)}, reach ${p.reach.toFixed(0)}`],["CPM / cost per engagement",`${usd(r.cost.cpm_usd)} / ${usd(r.cost.cpe_usd)}`]].map(([k,v])=>h("tr",{},h("td",{},k),h("td",{class:"n"},v))))),
 h("h3",{style:"margin-top:14px"},"Risk signals: "+r.risk.label),r.risk.signals.length?r.risk.signals.map(s=>h("div",{style:"padding:3px 0"},h("span",{class:"chip",style:`color:${s.triggered?"var(--accent)":"var(--good)"}`},s.triggered?"flag":"clear")," ",s.detail)):h("div",{class:"dim"},"No signal could be evaluated."),
 h("div",{class:"dim",style:"margin-top:8px;font-size:13px"},r.risk.disclaimer+"."),r.note?h("div",{class:"dim",style:"font-size:13px"},r.note):null)}
function table(rows){return h("div",{class:"scroll"},h("table",{},h("thead",{},h("tr",{},["#","Creator","Tier","Score","Risk","Data","CPM"].map((x,i)=>h("th",{class:i===3||i===6?"n":""},x)))),
 h("tbody",{},rows.map((r,i)=>h("tr",{class:"click"+(r===state.sel?" sel":""),onclick:()=>{state.sel=r;render()}},h("td",{class:"dim"},i+1),h("td",{},"@"+r.handle," ",h("span",{class:"dim"},r.platform)),h("td",{},r.tier),
  h("td",{class:"n"},r.score==null?"withheld":h("span",{},h("span",{class:"bar2",style:`width:${r.score*.6}px;margin-right:8px;opacity:${r.fit?1:.35}`}),r.score.toFixed(1))),
  h("td",{},h("span",{class:"chip",style:`color:${RC[r.risk.label]}`},r.risk.label)),h("td",{},r.confidence),h("td",{class:"n"},usd(r.cost.cpm_usd)))))))}
function render(){const rows=filtered();figs(rows);const uniq=k=>[...new Set(state.rows.map(r=>r[k]).filter(Boolean))].sort();
 const hide=h("input",{type:"checkbox",onchange:e=>{state.f.hideHigh=e.target.checked;render()}});hide.checked=state.f.hideHigh;
 $("#panel").replaceChildren(h("p",{class:"dim"},"Cohort-relative scores from public numbers. Risk signals are heuristics, not proof of fraud."),
  h("div",{class:"field"},select("Platform","platform",uniq("platform")),select("Tier","tier",uniq("tier")),select("Category","category",uniq("category")),h("label",{class:"f"},"Hide high risk",hide)),
  h("div",{class:"two"},table(rows),h("div",{},scatter(rows),detail(state.sel&&rows.includes(state.sel)?state.sel:null))))}
(async()=>{const m=await api("/api/meta");if(m.sample_rows)$("#banner").hidden=false;
 try{state.rows=await api("/api/creators");state.rows.length?render():$("#panel").replaceChildren(h("p",{class:"dim"},"No creators yet. Run `creatorscore import-creators`, or start with --demo."))}catch(e){$("#panel").replaceChildren(h("div",{class:"call fail"},"Could not load: "+e.message))}})();

</script></body></html>"""
