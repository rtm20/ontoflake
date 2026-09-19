"""OntoFlake - governed supply chain analytics on a Snowflake Semantic View.

Runs in Streamlit in Snowflake (active session), Streamlit Community Cloud (st.secrets key-pair), or locally (connections.toml).
Natural-language questions go to Cortex Analyst against the semantic view; a synonym router is the offline fallback.
"""
import json
import re
from collections import defaultdict
from decimal import Decimal

import pandas as pd
import streamlit as st

SV = "ONTOFLAKE.SEMANTIC.SUPPLY_CHAIN"
PERSONAS = ["SC_PLANNING", "SC_PROCUREMENT", "SC_LOGISTICS", "SC_LOGISTICS_APAC"]
ENTITY_LABEL_DIM = {"SUPPLIER": "supplier.supplier_name", "PART": "part.part_number", "PLANT": "plant.plant_name",
                    "CUSTOMER": "customer.customer_name", "CARRIER": "carrier.carrier_name"}
ACCENT, ACCENT2 = "#29B5E8", "#8B5CF6"

st.set_page_config(page_title="OntoFlake", page_icon="❄️", layout="wide", initial_sidebar_state="collapsed")

# ---------- theme ----------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Inter', sans-serif; }}
.stApp {{
  background: radial-gradient(1200px 600px at 10% -10%, rgba(41,181,232,.18), transparent 60%),
              radial-gradient(900px 500px at 100% 0%, rgba(139,92,246,.16), transparent 55%),
              #070B14;
  color: #E6EDF7;
}}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 1rem; max-width: 1600px; }}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li {{ font-size:.9rem; }}
.of-brand {{ display:flex; align-items:center; gap:.7rem; }}
.of-logo {{ width:38px; height:38px; border-radius:11px;
  background: linear-gradient(135deg,{ACCENT},{ACCENT2}); display:flex; align-items:center; justify-content:center;
  font-size:20px; box-shadow: 0 0 24px rgba(41,181,232,.45); }}
.of-title {{ font-size:1.55rem; font-weight:700; letter-spacing:-.02em;
  background: linear-gradient(90deg,#FFFFFF 0%,{ACCENT} 60%,{ACCENT2} 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
.of-sub {{ color:#8B98AE; font-size:.82rem; margin-top:-2px; }}
.of-chip {{ display:inline-block; padding:.18rem .6rem; border-radius:999px; font-size:.72rem; font-weight:600;
  border:1px solid rgba(41,181,232,.35); background:rgba(41,181,232,.10); color:{ACCENT}; margin-right:.35rem; }}
.of-chip.v {{ border-color:rgba(139,92,246,.4); background:rgba(139,92,246,.12); color:#C4B5FD; }}
.of-chip.g {{ border-color:rgba(52,211,153,.4); background:rgba(52,211,153,.12); color:#6EE7B7; }}
.of-card {{ position:relative; border-radius:16px; padding:.9rem 1rem; background:rgba(255,255,255,.035);
  border:1px solid rgba(255,255,255,.08); backdrop-filter: blur(10px); min-height:112px; }}
.of-kpi-l {{ color:#8B98AE; font-size:.68rem; text-transform:uppercase; letter-spacing:.06em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.of-card::before {{ content:""; position:absolute; inset:0; border-radius:16px; padding:1px; pointer-events:none;
  background: linear-gradient(135deg, rgba(41,181,232,.55), rgba(139,92,246,.35), transparent 70%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude; }}
.of-kpi-l {{ color:#8B98AE; font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; }}
.of-kpi-v {{ font-size:1.45rem; font-weight:700; margin-top:.15rem; color:#F8FAFC; }}
.of-kpi-d {{ font-size:.7rem; color:#64748B; margin-top:.1rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.of-panel-h {{ font-size:.78rem; font-weight:600; letter-spacing:.1em; text-transform:uppercase; color:#8B98AE; margin:.2rem 0 .6rem; }}
.of-interp {{ border-left:3px solid {ACCENT}; padding:.55rem .8rem; border-radius:8px; background:rgba(41,181,232,.08); font-size:.92rem; }}
[data-testid="stChatMessage"] {{ background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.06); border-radius:14px; padding:.6rem .8rem; }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{ background:rgba(139,92,246,.10); border-color:rgba(139,92,246,.25); }}
[data-testid="stChatInput"] textarea {{ background:rgba(255,255,255,.04) !important; border-radius:14px !important; }}
[data-testid="stChatInput"] {{ border:1px solid rgba(41,181,232,.35); border-radius:14px; box-shadow:0 0 18px rgba(41,181,232,.15); }}
div[data-testid="stDataFrame"], div[data-testid="stCodeBlock"] {{ border-radius:12px; overflow:hidden; }}
button[kind="secondary"] {{ border-radius:999px !important; }}
/* suggestion chips (buttons keyed sug_*) */
.st-key-sug_0 button, .st-key-sug_1 button, .st-key-sug_2 button, .st-key-sug_3 button, .st-key-sug_4 button,
.st-key-sug_5 button, .st-key-sug_6 button, .st-key-sug_7 button, .st-key-sug_8 button {{
  font-size:.76rem; padding:.28rem .5rem; min-height:0; line-height:1.15; white-space:normal;
  background:rgba(41,181,232,.08); border:1px solid rgba(41,181,232,.30); color:#BFE9F8; }}
.st-key-sug_0 button p, .st-key-sug_1 button p, .st-key-sug_2 button p, .st-key-sug_3 button p, .st-key-sug_4 button p,
.st-key-sug_5 button p, .st-key-sug_6 button p, .st-key-sug_7 button p, .st-key-sug_8 button p {{
  white-space:normal !important; overflow:visible !important; text-overflow:clip !important; font-size:.76rem; }}
.st-key-sug_0 button:hover, .st-key-sug_1 button:hover, .st-key-sug_2 button:hover, .st-key-sug_3 button:hover, .st-key-sug_4 button:hover,
.st-key-sug_5 button:hover, .st-key-sug_6 button:hover, .st-key-sug_7 button:hover, .st-key-sug_8 button:hover {{
  border-color:{ACCENT}; color:#fff; background:rgba(41,181,232,.18); }}
.of-fade {{ color:#64748B; font-size:.75rem; font-family:'JetBrains Mono', monospace; }}
</style>
""", unsafe_allow_html=True)


# ---------- session ----------
@st.cache_resource
def get_session():
    # 1) Streamlit in Snowflake  2) Streamlit Community Cloud via st.secrets (key-pair)  3) local connections.toml
    try:
        from snowflake.snowpark.context import get_active_session
        return get_active_session()
    except Exception:
        pass
    from snowflake.snowpark import Session
    if "snowflake" in st.secrets:
        cfg = dict(st.secrets["snowflake"])
        pem = cfg.pop("private_key_pem", None)
        if pem:
            from cryptography.hazmat.primitives import serialization
            key = serialization.load_pem_private_key(pem.encode(), password=None)
            cfg["private_key"] = key.private_bytes(
                serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        return Session.builder.configs(cfg).create()
    return Session.builder.config("connection_name", "hackathon").create()


session = get_session()


def sql(q: str) -> pd.DataFrame:
    # collect() works for DESCRIBE/SHOW as well as SELECT; to_pandas() does not on all Snowpark versions.
    sdf = session.sql(q)
    rows = sdf.collect()
    df = pd.DataFrame([r.as_dict() for r in rows]) if rows else pd.DataFrame(columns=sdf.columns)
    df.columns = [str(c).strip('"') for c in df.columns]
    for c in df.columns:
        if df[c].dtype == object and df[c].map(lambda v: v is None or isinstance(v, Decimal)).all():
            df[c] = df[c].astype(float)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def cached_sql(q: str) -> pd.DataFrame:
    return sql(q)


# ---------- semantic view metadata ----------
@st.cache_data(ttl=600, show_spinner="Reading the ontology metadata…")
def load_metadata():
    df = sql(f"DESCRIBE SEMANTIC VIEW {SV}")
    df.columns = [c.lower() for c in df.columns]
    df = df.fillna("")
    objs = defaultdict(dict)
    for _, r in df.iterrows():
        objs[(r["object_kind"], r["object_name"], r["parent_entity"])][r["property"]] = r["property_value"]
    meta = {"TABLE": [], "DIMENSION": [], "METRIC": [], "RELATIONSHIP": []}
    for (kind, name, parent), props in objs.items():
        if kind not in meta:
            continue
        syn = props.get("SYNONYMS")
        meta[kind].append({
            "name": name, "table": parent or name, "ref": f"{(parent or name).lower()}.{name.lower()}",
            "expression": props.get("EXPRESSION", ""), "comment": props.get("COMMENT", ""),
            "synonyms": json.loads(syn) if syn else [], "data_type": props.get("DATA_TYPE", ""),
            "ref_table": props.get("REF_TABLE", ""),
        })
    for k in meta:
        meta[k].sort(key=lambda x: (x["table"], x["name"]))
    return meta


meta = load_metadata()
METRICS = {m["ref"]: m for m in meta["METRIC"]}
DIMENSIONS = {d["ref"]: d for d in meta["DIMENSION"]}
METRIC_NAMES = {m["name"].lower() for m in meta["METRIC"]}


def semantic_query(dims, mets, where=None, limit=500):
    q = f"SELECT * FROM SEMANTIC_VIEW({SV}"
    if dims:
        q += " DIMENSIONS " + ", ".join(dims)
    q += " METRICS " + ", ".join(mets) + ")"
    if where:
        q += f" WHERE {where}"
    return q + f" LIMIT {limit}"


# ---------- Cortex Analyst ----------
ANALYST_PATH = "/api/v2/cortex/analyst/message"


def analyst_ask(question: str) -> dict:
    """Return {'interpretation', 'sql', 'suggestions', 'request_id'} from Cortex Analyst over the semantic view."""
    body = {"messages": [{"role": "user", "content": [{"type": "text", "text": question}]}], "semantic_view": SV}
    try:
        import _snowflake  # only exists inside Streamlit in Snowflake
        resp = _snowflake.send_snow_api_request("POST", ANALYST_PATH, {}, {}, body, None, 60000)
        if resp["status"] != 200:
            raise RuntimeError(f"Cortex Analyst HTTP {resp['status']}: {resp['content'][:300]}")
        payload = json.loads(resp["content"])
    except ImportError:
        import requests
        conn = session.connection
        r = requests.post(f"https://{conn.host}{ANALYST_PATH}", json=body, timeout=90,
                          headers={"Authorization": f'Snowflake Token="{conn.rest.token}"',
                                   "Content-Type": "application/json", "Accept": "application/json"})
        if r.status_code != 200:
            raise RuntimeError(f"Cortex Analyst HTTP {r.status_code}: {r.text[:300]}")
        payload = r.json()
    out = {"interpretation": "", "sql": "", "suggestions": [], "request_id": payload.get("request_id", "")}
    for c in payload.get("message", {}).get("content", []):
        if c["type"] == "text":
            out["interpretation"] += c["text"]
        elif c["type"] == "sql":
            out["sql"] = c["statement"]
        elif c["type"] == "suggestions":
            out["suggestions"] = c["suggestions"]
    return out


def runnable(statement: str) -> str:
    return re.sub(r";\s*$", "", statement.strip())


# ---------- offline router ----------
def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def match_objects(question, objects):
    """Greedy longest-phrase matching: each span of the question is claimed by one object only."""
    q = " " + " ".join(tokenize(question)) + " "
    candidates = []
    for o in objects:
        phrases = [o["name"].lower().replace("_", " ")] + [s.lower() for s in o["synonyms"]]
        for p in phrases:
            pos = q.find(f" {p} ")
            if pos >= 0:
                candidates.append((len(p), pos, o["ref"]))
    candidates.sort(key=lambda c: (-c[0], c[1]))
    claimed, out = [], []
    for length, pos, ref in candidates:
        span = (pos, pos + length + 2)
        if ref in out or any(s[0] < span[1] and span[0] < s[1] for s in claimed):
            continue
        claimed.append(span)
        out.append(ref)
    return out


def router_answer(question):
    mets = match_objects(question, meta["METRIC"])
    dims = [d for d in match_objects(question, meta["DIMENSION"]) if not d.endswith("_date")][:3]
    for t in match_objects(question, meta["TABLE"]):
        ent = t.split(".")[0].upper()
        if ent in ENTITY_LABEL_DIM and not any(d.startswith(ent.lower() + ".") for d in dims):
            dims.append(ENTITY_LABEL_DIM[ent])
    return mets[:3], dims[:3]


# ---------- copilot self-knowledge (answered locally, never sent to Analyst) ----------
HELP_TEXT = (
    "I'm the **OntoFlake copilot**. I answer supply-chain questions from one governed ontology — "
    f"the Snowflake semantic view `{SV}` — so every persona gets the same number.\n\n"
    "**Ask me things like**\n"
    "- *supplier on-time delivery by plant region*\n"
    "- *which five suppliers have the worst defect rate*\n"
    "- *landed cost per unit by transport mode for APAC*\n"
    "- *monthly customer OTD trend for 2026*\n\n"
    "**Or ask about the ontology itself**\n"
    "- *what is fill rate?* · *how is days of inventory calculated?* · *list the metrics* · *who are the personas?*\n\n"
    "Answers appear on the **Insight canvas** to the left with the generated SQL as evidence. "
    "Use **Explore** for point-and-click, **Consistency Proof** to see the cross-persona test, **Glossary** for every definition."
)


def help_answer(question: str) -> str:
    """Return a markdown answer for greetings / meta questions, or '' if this is a data question."""
    q = " ".join(tokenize(question))
    words = set(q.split())
    data_signal = bool(match_objects(question, meta["METRIC"])) or bool(match_objects(question, meta["DIMENSION"]))

    if words & {"hello", "hi", "hey", "help", "start"} and not data_signal or \
       re.search(r"(how|what).*(can|do|could) (you|u) (help|do)|what (are|is) (you|this|ontoflake)|who are you|how (do|does|to) (i|this|it) (use|work)", q):
        return HELP_TEXT

    if re.search(r"\b(list|show|which|what)\b.*\bmetrics?\b", q) and not re.search(r"\bby\b", q):
        rows = "\n".join(f"- **{m['name'].lower()}** — {m['comment'] or m['expression']}" for m in meta["METRIC"] if m["comment"])
        return f"**Governed metrics in the ontology** ({len(meta['METRIC'])}):\n\n{rows}"

    if re.search(r"persona|role|who (can|sees)|governance|masking|row access", q):
        return ("**Personas** are Snowflake roles that query the *same* semantic view:\n\n"
                "- `SC_PLANNING` — global · sees costs\n- `SC_PROCUREMENT` — global · sees costs\n"
                "- `SC_LOGISTICS` — global · **cost columns masked to NULL**\n"
                "- `SC_LOGISTICS_APAC` — **APAC plants only** (row-access policy) · costs masked\n\n"
                "Definitions never change per persona; only visibility does. The **Consistency Proof** tab runs every golden "
                "question as every persona and asserts identical numbers.")

    if re.search(r"^(what is|what's|define|definition of|explain|how is|how do you (calculate|compute)|meaning of)\b", q) \
            and not re.search(r"\b(by|per|for|in)\b", q):
        hits = match_objects(question, meta["METRIC"])
        if hits:
            m = METRICS[hits[0]]
            syn = ("  \nAlso known as: " + ", ".join(f"*{s}*" for s in m["synonyms"])) if m["synonyms"] else ""
            return (f"**{m['name'].lower()}**  \n{m['comment'] or 'Canonical metric of the ontology.'}\n\n"
                    f"`{m['expression']}`{syn}\n\nAsk it *by* a dimension to see numbers, e.g. “{m['name'].lower().replace('_', ' ')} by plant region”.")
    return ""


def shape_result(df: pd.DataFrame, question: str):
    mets = [c for c in df.columns if c.lower() in METRIC_NAMES]
    dims = [c for c in df.columns if c not in mets]
    df = df[dims + mets]
    ql = question.lower()
    if mets and dims and len(df) > 1:
        if any(w in ql for w in ("worst", "lowest", "bottom")):
            worse_is_high = any(w in ql for w in ("defect", "backorder", "lead time", "cost", "variance"))
            df = df.sort_values(mets[0], ascending=not worse_is_high).head(10)
        elif any(w in ql for w in ("best", "highest", "top")):
            df = df.sort_values(mets[0], ascending=False).head(10)
    return df, dims, mets


def render_chart(df, dims, mets):
    if not (mets and dims and 1 < len(df) <= 60):
        return
    x = dims[0]
    is_time = any(k in x.lower() for k in ("month", "date", "year", "quarter", "week"))
    if is_time:
        df = df.sort_values(x)
    data = df.set_index(x)[mets[:2]]
    if is_time:
        st.line_chart(data, color=[ACCENT, ACCENT2][:len(mets[:2])], height=260)
    else:
        st.bar_chart(data[mets[0]], color=ACCENT, height=260, horizontal=len(df) > 8)


def chip(text, cls=""):
    return f'<span class="of-chip {cls}">{text}</span>'


def kpi(col, label, value, detail):
    col.markdown(f'<div class="of-card"><div class="of-kpi-l">{label}</div><div class="of-kpi-v">{value}</div>'
                 f'<div class="of-kpi-d">{detail}</div></div>', unsafe_allow_html=True)



# ============================== STATE ==============================
NAV = ["Insights", "Explore", "Consistency Proof", "Glossary", "Ontology"]
NAV_ALIASES = {
    "Insights": ["insight", "insights", "canvas", "answer", "answers", "home", "dashboard", "result", "results"],
    "Explore": ["explore", "explorer", "browse", "builder", "pivot", "slice", "point and click"],
    "Consistency Proof": ["proof", "consistency", "persona", "personas", "harness", "test", "tests", "governance", "policy", "policies", "masking", "row access"],
    "Glossary": ["glossary", "definitions", "dictionary", "metric list", "all metrics", "metrics list"],
    "Ontology": ["ontology", "graph", "entities", "relationships", "model", "schema", "erd", "diagram"],
}
EXAMPLES = ["What is supplier on time delivery by plant region?",
            "Which plant region has the lowest fill rate and how many backorders does it have?",
            "Compare landed cost per unit by transport mode for APAC suppliers",
            "Days of inventory and inventory value by category for the latest month",
            "Which five suppliers have the worst defect rate with at least 100 shipments?",
            "Monthly customer on-time delivery trend for 2026",
            "Show me the consistency proof",
            "Open the ontology graph",
            "Explore landed cost per unit by transport mode"]

ss = st.session_state
ss.setdefault("chat", [])            # list of result dicts
ss.setdefault("pending", None)       # question waiting to be answered on this run
ss.setdefault("view", NAV[0])        # current left-pane section
ss.setdefault("explore_dims", ["plant.plant_region"])
ss.setdefault("explore_mets", ["shipment.supplier_otd_pct", "so_line.fill_rate_pct"])


# ============================== COPILOT INTENTS ==============================
def nav_intent(question: str):
    """Return a NAV section if the question is a navigation request, else None."""
    q = " " + " ".join(tokenize(question)) + " "
    verbs = re.search(r"\b(open|show|go to|goto|take me|switch|navigate|bring up|display|see|view|jump)\b", q)
    for section, aliases in NAV_ALIASES.items():
        if any(f" {a} " in q for a in aliases) and (verbs or len(q.split()) <= 4):
            return section
    return None


def explore_intent(question: str):
    """'explore X by Y' -> pre-fill the Explore builder. Returns (mets, dims) or None."""
    q = " ".join(tokenize(question))
    if not re.match(r"^(explore|build|pivot|slice|break ?down)\b", q):
        return None
    mets, dims = router_answer(question)
    return (mets, dims) if mets else None


def answer(question: str) -> dict:
    """Run a question through intents -> Cortex Analyst (router as silent fallback). Returns a result dict."""
    res = {"question": question, "engine": "Cortex Analyst", "interpretation": "", "sql": "", "df": None,
           "suggestions": [], "request_id": "", "objects": [], "error": "", "help": "", "nav": None}

    ex = explore_intent(question)
    if ex:
        mets, dims = ex
        ss.explore_mets, ss.explore_dims = mets, dims or ["plant.plant_region"]
        res.update(nav="Explore", engine="Copilot",
                   help=f"Opened **Explore** with {', '.join(f'`{m}`' for m in mets)} by {', '.join(f'`{d}`' for d in ss.explore_dims)}. Adjust the pickers on the left.")
        return res

    section = nav_intent(question)
    if section:
        blurb = {"Insights": "the latest answer canvas", "Explore": "the point-and-click builder",
                 "Consistency Proof": "the cross-persona test matrix — every golden question run as every role",
                 "Glossary": "every governed metric with its definition, formula and synonyms",
                 "Ontology": "the entity-relationship graph declared in the semantic view"}[section]
        res.update(nav=section, engine="Copilot", help=f"Opened **{section}** — {blurb}.")
        return res

    helped = help_answer(question)
    if helped:
        res.update(help=helped, engine="Copilot")
        return res

    try:
        a = analyst_ask(question)
        res.update(interpretation=a["interpretation"], sql=a["sql"], suggestions=a["suggestions"], request_id=a["request_id"])
        if a["sql"]:
            res["df"] = sql(runnable(a["sql"]))
        res["nav"] = "Insights"
        return res
    except Exception as e:
        res["error"] = f"Cortex Analyst unavailable ({e}). Answered with the synonym router instead."
        res["engine"] = "Synonym router"
    mets, dims = router_answer(question)
    if not mets:
        res["error"] = res["error"] or "No governed metric recognised. Try one of the glossary synonyms, or say **help**."
        return res
    res["sql"] = semantic_query(dims, mets)
    res["objects"] = mets + dims
    res["interpretation"] = "Resolved via ontology synonyms: " + ", ".join(f"`{o}`" for o in mets + dims)
    res["df"] = sql(res["sql"])
    res["nav"] = "Insights"
    return res


def latest_insight():
    for r in reversed(ss.chat):
        if r["df"] is not None or r["suggestions"] or (r["sql"] and not r["help"]):
            return r
    return None


# ============================== RENDERERS ==============================
def render_assistant_bubble(r: dict):
    if r["help"]:
        st.markdown(r["help"])
    elif r["error"] and r["df"] is None:
        st.markdown(f"⚠️ {r['error']}")
    elif r["df"] is not None:
        n = len(r["df"])
        summary = r["interpretation"].split("\n\n")[-1] if r["interpretation"] else "Here's what the ontology says."
        st.markdown(f"{summary}\n\n{chip(r['engine'], 'g' if r['engine'] == 'Cortex Analyst' else 'v')} "
                    f"{chip(f'{n} row' + ('s' if n != 1 else ''))} → on the Insights canvas", unsafe_allow_html=True)
    elif r["suggestions"]:
        st.markdown("Could you be more specific? For example:\n" + "\n".join(f"- {s}" for s in r["suggestions"]))
    else:
        st.markdown("I couldn't turn that into a governed query. Try one of the examples, or say **help**.")


def render_insights(r, working: str | None = None):
    st.markdown('<div class="of-panel-h">Insights canvas</div>', unsafe_allow_html=True)
    if working:
        st.markdown(f'<div class="of-card" style="padding:1.2rem"><div style="font-weight:600">{working}</div>'
                    f'<div style="color:#8B98AE;margin-top:.4rem">Cortex Analyst is reading the ontology and Snowflake is '
                    f'computing the answer…</div></div>', unsafe_allow_html=True)
        return
    if r is None:
        st.markdown(f"""<div class="of-card" style="padding:1.4rem">
          <div style="font-size:1.1rem;font-weight:600">Ask the copilot to light up the canvas</div>
          <div style="color:#8B98AE;margin-top:.4rem">Every answer is computed by Snowflake from
          <code>{SV}</code>. Planning, procurement and logistics get the same number — governed by row-access
          and masking policies, proven by the consistency harness. The copilot can also open any section for you:
          try <em>“show me the consistency proof”</em> or <em>“explore landed cost by transport mode”</em>.</div>
          <div style="margin-top:.9rem">{chip('Supplier → Part → Plant → PO → Shipment → Inventory → Order → Customer','v')}</div>
        </div>""", unsafe_allow_html=True)
        return
    st.markdown(f"**{r['question']}**")
    if r["error"]:
        st.warning(r["error"])
    if r["interpretation"] and r["engine"] == "Cortex Analyst":
        st.markdown(f'<div class="of-interp">{r["interpretation"].split("question:")[-1].strip()}</div>', unsafe_allow_html=True)
    if r["df"] is not None:
        df, dims, mets = shape_result(r["df"], r["question"])
        if dims and any(k in dims[0].lower() for k in ("month", "date", "year", "quarter", "week")):
            df = df.sort_values(dims[0])
        render_chart(df, dims, mets)
        st.dataframe(df, use_container_width=True, hide_index=True, height=min(400, 40 + 35 * len(df)))
    elif r["suggestions"]:
        for s in r["suggestions"]:
            st.markdown(f"- {s}")
    if r["sql"]:
        with st.expander("Evidence · generated SQL", expanded=False):
            st.code(r["sql"], language="sql")
            if r["objects"]:
                st.markdown("**Resolved objects:** " + " ".join(chip(o) for o in r["objects"]), unsafe_allow_html=True)
            tag = f"request_id {r['request_id']}" if r["request_id"] else "synonym router"
            st.markdown(f'<div class="of-fade">semantic view {SV} · {r["engine"]} · {tag}</div>', unsafe_allow_html=True)


def render_explore():
    st.markdown('<div class="of-panel-h">Explore the semantic view</div>', unsafe_allow_html=True)
    fmt = lambda r, d: f"{r}  ({', '.join(d[r]['synonyms'][:2])})" if d[r]["synonyms"] else r
    col_a, col_b = st.columns(2)
    dims_sel = col_a.multiselect("Dimensions", list(DIMENSIONS), default=[d for d in ss.explore_dims if d in DIMENSIONS],
                                 format_func=lambda r: fmt(r, DIMENSIONS), key="explore_dims_w")
    mets_sel = col_b.multiselect("Metrics", list(METRICS), default=[m for m in ss.explore_mets if m in METRICS],
                                 format_func=lambda r: fmt(r, METRICS), key="explore_mets_w")
    where = st.text_input("Optional WHERE (on output columns)", placeholder="e.g. plant_region = 'APAC'")
    if not mets_sel:
        st.info("Pick at least one metric.")
        return
    q = semantic_query(dims_sel, mets_sel, where or None)
    try:
        with st.spinner("Querying the semantic view…"):
            df = cached_sql(q)
        left, right = st.columns([1.3, 1])
        with left:
            st.dataframe(df, use_container_width=True, hide_index=True)
        with right:
            if len(dims_sel) == 1 and len(df) <= 60:
                st.bar_chart(df.set_index(df.columns[0]), color=[ACCENT, ACCENT2, "#34D399", "#F59E0B"][:len(mets_sel)], height=320)
    except Exception as e:
        st.error(str(e))
    st.code(q, language="sql")


def render_proof():
    st.markdown('<div class="of-panel-h">Cross-persona consistency proof</div>', unsafe_allow_html=True)
    st.markdown("Every golden question is executed **as each persona role** (real `USE ROLE`, real row-access and masking "
                "policies). Global personas must match byte-for-byte; scoped personas must equal the global answer filtered "
                "to their scope; non-entitled metrics must be `NULL` — never a different number.")
    try:
        with st.spinner("Loading the latest harness run…"):
            runs = cached_sql("SELECT * FROM ONTOFLAKE.GOV.CONSISTENCY_RUN WHERE run_ts = (SELECT MAX(run_ts) FROM ONTOFLAKE.GOV.CONSISTENCY_RUN)")
    except Exception:
        runs = pd.DataFrame()
    if runs.empty:
        st.info("No harness run found. Run `harness/consistency_check.py`.")
        return
    runs.columns = [c.lower() for c in runs.columns]
    piv = runs.pivot(index=["question_id", "question_text"], columns="persona", values="status")[PERSONAS]
    rows = runs.pivot(index=["question_id", "question_text"], columns="persona", values="row_count")[PERSONAS]
    fails = int((piv != "PASS").sum().sum())
    a, b, c = st.columns(3)
    kpi(a, "Cells passing", f"{piv.size - fails} / {piv.size}", "questions × personas")
    kpi(b, "Personas", f"{len(PERSONAS)}", "3 global · 1 region-scoped")
    kpi(c, "Latest run", str(runs["run_ts"].iloc[0])[:19], "harness/consistency_check.py")
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    cells = piv.astype(str) + "  ·  " + rows.astype(int).astype(str) + " rows"
    st.dataframe(cells.style.map(lambda v: "background-color:rgba(52,211,153,.18);color:#6EE7B7" if v.startswith("PASS")
                                 else "background-color:rgba(248,113,113,.18);color:#FCA5A5"), use_container_width=True)
    left, right = st.columns(2)
    with left:
        st.markdown("**Persona scopes** — roles absent here are global")
        with st.spinner("Loading scopes…"):
            st.dataframe(cached_sql("SELECT * FROM ONTOFLAKE.GOV.PERSONA_SCOPE"), hide_index=True, use_container_width=True)
    with right:
        st.markdown("**Policies in force**")
        try:
            with st.spinner("Loading policies…"):
                st.dataframe(cached_sql("SELECT policy_name, policy_kind, ref_column_name FROM TABLE(ONTOFLAKE.INFORMATION_SCHEMA.POLICY_REFERENCES(REF_ENTITY_NAME => 'ONTOFLAKE.CONFORMED.FACT_PURCHASE_ORDER_LINE', REF_ENTITY_DOMAIN => 'TABLE'))"), hide_index=True, use_container_width=True)
        except Exception:
            st.code("PLANT_REGION_RAP  ROW_ACCESS_POLICY  FACT_* (plant_region)\nCOST_MASK         MASKING_POLICY     FACT_PURCHASE_ORDER_LINE (unit_price, po_line_value, price_variance_value)")


def render_glossary():
    st.markdown('<div class="of-panel-h">Metric glossary — definitions live in the semantic view</div>', unsafe_allow_html=True)
    owner = {"SHIPMENT": "procurement", "PO_LINE": "procurement", "SO_LINE": "logistics / planning", "INVENTORY": "planning"}
    g = pd.DataFrame([{"metric": m["ref"], "owner": owner.get(m["table"], ""), "definition": m["comment"],
                       "formula": m["expression"], "synonyms": ", ".join(m["synonyms"])} for m in meta["METRIC"]])
    st.dataframe(g, use_container_width=True, hide_index=True, height=640)


def render_ontology():
    st.markdown('<div class="of-panel-h">Ontology — entities and relationships as declared in Snowflake</div>', unsafe_allow_html=True)
    facts = {"PO_LINE", "SHIPMENT", "SO_LINE", "INVENTORY"}
    dot = ['digraph G { rankdir=LR; bgcolor=transparent; pad=0.3;',
           'node [style="filled,rounded", fontname=Inter, fontcolor=white, color="#1E293B", penwidth=1.2];',
           'edge [color="#475569", fontcolor="#94A3B8", fontname=Inter, fontsize=9, arrowsize=0.7];']
    for t in meta["TABLE"]:
        shape, fill = ("box", ACCENT) if t["name"] in facts else ("ellipse", ACCENT2)
        dot.append(f'  {t["name"]} [shape={shape}, fillcolor="{fill}"];')
    for r in meta["RELATIONSHIP"]:
        dot.append(f'  {r["table"]} -> {r["ref_table"]} [label="{r["name"].lower()}"];')
    dot.append("}")
    st.graphviz_chart("\n".join(dot), use_container_width=True)
    st.markdown(chip("blue = facts (metric grains)") + chip("violet = entities", "v"), unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"entity": t["name"], "synonyms": ", ".join(t["synonyms"]), "comment": t["comment"]}
                               for t in meta["TABLE"]]), hide_index=True, use_container_width=True)


def render_section(view, working=None):
    if view == "Insights":
        render_insights(latest_insight(), working)
    elif view == "Explore":
        render_explore()
    elif view == "Consistency Proof":
        render_proof()
    elif view == "Glossary":
        render_glossary()
    else:
        render_ontology()


# ============================== LAYOUT ==============================
pending = ss.pending
ss.pending = None

left, right = st.columns([1.75, 1], gap="large")

# ---------- LEFT: brand, nav, KPIs, section ----------
with left:
    st.markdown("""<div class="of-brand"><div class="of-logo">❄️</div><div>
      <div class="of-title">OntoFlake</div>
      <div class="of-sub">Governed supply-chain intelligence · one ontology, one answer for every persona</div></div></div>""",
                unsafe_allow_html=True)
    st.markdown('<div style="margin:.4rem 0 .6rem">' +
                chip(f"{len(meta['TABLE'])} entities") + chip(f"{len(meta['RELATIONSHIP'])} relationships") +
                chip(f"{len(METRICS)} governed metrics", "v") + chip("Cortex Analyst", "g") + "</div>", unsafe_allow_html=True)

    # Nav widget is keyed to the session view so the copilot can move it.
    if hasattr(st, "segmented_control"):
        picked = st.segmented_control("nav", NAV, default=ss.view, label_visibility="collapsed", key=f"nav_{ss.view}")
    else:
        picked = st.radio("nav", NAV, index=NAV.index(ss.view), horizontal=True, label_visibility="collapsed", key=f"nav_{ss.view}")
    if picked and picked != ss.view:
        ss.view = picked
        st.rerun()

    kpi_slot = st.empty()
    with kpi_slot.container():
        with st.spinner("Computing headline KPIs…"):
            k = cached_sql(semantic_query([], ["shipment.supplier_otd_pct", "so_line.customer_otd_pct", "so_line.fill_rate_pct",
                                              "inventory.days_of_inventory", "shipment.landed_cost_per_unit"])).iloc[0]
    with kpi_slot.container():
        c1, c2, c3, c4, c5 = st.columns(5)
        kpi(c1, "Supplier OTD", f"{k['SUPPLIER_OTD_PCT']:.1f}%", "vs PO promised date")
        kpi(c2, "Customer OTD", f"{k['CUSTOMER_OTD_PCT']:.1f}%", "vs requested date")
        kpi(c3, "Fill rate", f"{k['FILL_RATE_PCT']:.1f}%", "shipped / ordered")
        kpi(c4, "Inventory days", f"{k['DAYS_OF_INVENTORY']:.0f} d", "on-hand / daily demand")
        kpi(c5, "Landed cost/unit", f"${k['LANDED_COST_PER_UNIT']:.2f}", "all-in per unit")
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    section_slot = st.empty()
    with section_slot.container():
        # While a data question is in flight, show the working state on the Insights canvas.
        render_section(ss.view if not pending else "Insights", working=pending if pending else None)

# ---------- RIGHT: persistent copilot ----------
SUGGESTIONS = [  # (label shown on chip, full prompt sent)
    ("Supplier OTD by region", "What is supplier on time delivery by plant region?"),
    ("Lowest fill-rate region", "Which plant region has the lowest fill rate and how many backorders does it have?"),
    ("Landed cost · APAC modes", "Compare landed cost per unit by transport mode for APAC suppliers"),
    ("Worst 5 suppliers by defects", "Which five suppliers have the worst defect rate with at least 100 shipments?"),
    ("Customer OTD trend 2026", "Monthly customer on-time delivery trend for 2026"),
    ("Open consistency proof", "Show me the consistency proof"),
    ("Open ontology graph", "Open the ontology graph"),
    ("Explore cost by mode", "Explore landed cost per unit by transport mode"),
    ("What can you do?", "help"),
]

with right:
    st.markdown('<div class="of-panel-h">✦ Ontology copilot</div>', unsafe_allow_html=True)

    # Chat window on top: oldest first, in-flight exchange appended at the bottom, auto-scrolls to newest.
    history = st.container(height=420)
    with history:
        if not ss.chat and not pending:
            with st.chat_message("assistant", avatar="❄️"):
                st.markdown("Hi — I'm the OntoFlake copilot. I answer supply-chain questions from the governed ontology "
                            "and I can drive the screen on the left: *“show me the consistency proof”*, *“open the ontology”*, "
                            "*“explore fill rate by plant”*. Say **help** any time.")
        for r in ss.chat:
            with st.chat_message("user", avatar="🧑‍💼"):
                st.markdown(r["question"])
            with st.chat_message("assistant", avatar="❄️"):
                render_assistant_bubble(r)
        live = st.container()
        st.markdown('<div id="of-chat-end"></div>', unsafe_allow_html=True)

    # Suggestion chips: short labels, wrap onto multiple lines, never scroll off-screen.
    st.markdown('<div class="of-fade" style="margin:.35rem 0 .15rem">Try one</div>', unsafe_allow_html=True)
    chip_cols = st.columns(2)
    for i, (label, prompt) in enumerate(SUGGESTIONS):
        if chip_cols[i % 2].button(label, key=f"sug_{i}", use_container_width=True):
            ss.pending = prompt
            st.rerun()

    typed = st.chat_input("Ask a question, or say “open glossary”, “show the proof”, “help”…")
    if typed:
        ss.pending = typed
        st.rerun()

    c_clear, c_hint = st.columns([1, 3])
    if c_clear.button("Clear chat", use_container_width=True) and ss.chat:
        ss.chat = []
        st.rerun()
    c_hint.markdown('<div class="of-fade" style="padding-top:.55rem">Cortex Analyst over the governed semantic view · answers render on the left</div>',
                    unsafe_allow_html=True)

# ---------- run the in-flight question ----------
if pending:
    with live:
        with st.chat_message("user", avatar="🧑‍💼"):
            st.markdown(pending)
        with st.chat_message("assistant", avatar="❄️"):
            bubble = st.empty()
            with bubble.container():
                with st.spinner("Reading the ontology…"):
                    result = answer(pending)
            ss.chat.append(result)
            with bubble.container():
                render_assistant_bubble(result)
    if result["nav"] and result["nav"] != ss.view:
        ss.view = result["nav"]
        st.rerun()                      # nav widget must be rebuilt with the new selection
    with section_slot.container():
        render_section(ss.view)

# keep the chat window scrolled to the newest message
import streamlit.components.v1 as components
components.html("""<script>
const el = window.parent.document.getElementById('of-chat-end');
if (el) { el.scrollIntoView({block: 'end'}); }
</script>""", height=0)
