"""OntoFlake - governed supply chain analytics on a Snowflake Semantic View.

Runs as Streamlit in Snowflake (get_active_session) or locally (connections.toml).
"""
import json
import re
from collections import defaultdict

import pandas as pd
import streamlit as st

SV = "ONTOFLAKE.SEMANTIC.SUPPLY_CHAIN"
PERSONAS = ["SC_PLANNING", "SC_PROCUREMENT", "SC_LOGISTICS", "SC_LOGISTICS_APAC"]

st.set_page_config(page_title="OntoFlake", page_icon="❄️", layout="wide")


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
    df = session.sql(q).to_pandas()
    df.columns = [c.strip('"') for c in df.columns]
    return df


# ---------- semantic view metadata ----------
@st.cache_data(ttl=600)
def load_metadata():
    df = sql(f"DESCRIBE SEMANTIC VIEW {SV}")
    df.columns = [c.lower() for c in df.columns]
    df = df.fillna("")
    objs = defaultdict(dict)
    for _, r in df.iterrows():
        key = (r["object_kind"], r["object_name"], r["parent_entity"])
        objs[key][r["property"]] = r["property_value"]
    meta = {"TABLE": [], "DIMENSION": [], "METRIC": [], "RELATIONSHIP": []}
    for (kind, name, parent), props in objs.items():
        if kind not in meta:
            continue
        syn = props.get("SYNONYMS")
        meta[kind].append({
            "name": name, "table": parent or name,
            "ref": f"{(parent or name).lower()}.{name.lower()}",
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


def semantic_query(dims, mets, where=None, limit=500):
    q = f"SELECT * FROM SEMANTIC_VIEW({SV}"
    if dims:
        q += " DIMENSIONS " + ", ".join(dims)
    q += " METRICS " + ", ".join(mets) + ")"
    if where:
        q += f" WHERE {where}"
    return q + f" LIMIT {limit}"


# ---------- header ----------
st.title("❄️ OntoFlake")
st.caption("One ontology. One definition per metric. One answer for every persona. "
           f"Semantic view: `{SV}` · {len(meta['TABLE'])} entities · {len(meta['RELATIONSHIP'])} relationships · "
           f"{len(METRICS)} governed metrics")

k = sql(semantic_query([], ["shipment.supplier_otd_pct", "so_line.customer_otd_pct", "so_line.fill_rate_pct",
                            "inventory.days_of_inventory", "shipment.landed_cost_per_unit"])).iloc[0]
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Supplier OTD", f"{k['SUPPLIER_OTD_PCT']:.1f}%")
c2.metric("Customer OTD", f"{k['CUSTOMER_OTD_PCT']:.1f}%")
c3.metric("Fill Rate", f"{k['FILL_RATE_PCT']:.1f}%")
c4.metric("Days of Inventory", f"{k['DAYS_OF_INVENTORY']:.0f} d")
c5.metric("Landed Cost / Unit", f"${k['LANDED_COST_PER_UNIT']:.2f}")

tab_ask, tab_explore, tab_proof, tab_glossary, tab_ontology = st.tabs(
    ["💬 Ask", "🔎 Explore", "✅ Consistency Proof", "📖 Metric Glossary", "🕸️ Ontology"])


# ---------- Ask: synonym-driven intent → semantic query (Cortex Analyst slot) ----------
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


with tab_ask:
    st.markdown("Ask in business language. Synonyms in the semantic view route the question to the governed metric; "
                "the generated `SEMANTIC_VIEW()` SQL is shown as evidence. *(Cortex Analyst replaces the router when enabled.)*")
    examples = ["What is supplier on time delivery by plant region?",
                "Show fill rate and backorders by plant",
                "Landed cost per unit by transport mode and supplier region",
                "Days of supply by category",
                "Which vendors have the worst defect rate?",
                "PO spend and PPV by category"]
    ex = st.selectbox("Examples", [""] + examples)
    question = st.text_input("Your question", value=ex)
    if question:
        mets = match_objects(question, meta["METRIC"])
        dims = match_objects(question, meta["DIMENSION"])
        dims = [d for d in dims if not d.endswith("_date")][:3]
        if not mets:
            st.warning("No governed metric recognised. Try one of the glossary synonyms.")
        else:
            q = semantic_query(dims, mets[:3])
            df = sql(q)
            if "worst" in question.lower() or "lowest" in question.lower():
                df = df.sort_values(df.columns[-len(mets[:3])], ascending=("defect" not in question.lower())).head(10)
            st.dataframe(df, use_container_width=True, hide_index=True)
            if dims and len(df) <= 60:
                st.bar_chart(df.set_index(df.columns[0])[df.columns[len(dims)]])
            with st.expander("Evidence: resolved objects and SQL", expanded=True):
                st.markdown("**Metrics:** " + ", ".join(f"`{m}` — {METRICS[m]['comment'] or METRICS[m]['expression']}" for m in mets[:3]))
                if dims:
                    st.markdown("**Dimensions:** " + ", ".join(f"`{d}`" for d in dims))
                st.code(q, language="sql")


# ---------- Explore ----------
with tab_explore:
    col_a, col_b = st.columns(2)
    dims_sel = col_a.multiselect("Dimensions", list(DIMENSIONS), default=["plant.plant_region"],
                                 format_func=lambda r: f"{r}  ({', '.join(DIMENSIONS[r]['synonyms'][:2])})" if DIMENSIONS[r]["synonyms"] else r)
    mets_sel = col_b.multiselect("Metrics", list(METRICS), default=["shipment.supplier_otd_pct", "so_line.fill_rate_pct"],
                                 format_func=lambda r: f"{r}  ({', '.join(METRICS[r]['synonyms'][:2])})" if METRICS[r]["synonyms"] else r)
    where = st.text_input("Optional WHERE (on output columns)", placeholder="e.g. plant_region = 'APAC'")
    if mets_sel:
        q = semantic_query(dims_sel, mets_sel, where or None)
        try:
            df = sql(q)
            st.dataframe(df, use_container_width=True, hide_index=True)
            if len(dims_sel) == 1 and len(df) <= 60:
                st.bar_chart(df.set_index(df.columns[0]))
        except Exception as e:
            st.error(str(e))
        st.code(q, language="sql")


# ---------- Consistency proof ----------
with tab_proof:
    st.markdown("Every golden question is executed **as each persona role** (real `USE ROLE`, real row-access and masking "
                "policies). Global personas must match byte-for-byte; scoped personas must equal the global answer filtered "
                "to their scope; non-entitled metrics must be `NULL`, never a different number.")
    try:
        runs = sql("SELECT * FROM ONTOFLAKE.GOV.CONSISTENCY_RUN WHERE run_ts = (SELECT MAX(run_ts) FROM ONTOFLAKE.GOV.CONSISTENCY_RUN)")
    except Exception:
        runs = pd.DataFrame()
    if runs.empty:
        st.info("No harness run found. Run `harness/consistency_check.py`.")
    else:
        runs.columns = [c.lower() for c in runs.columns]
        st.caption(f"Latest run: {runs['run_ts'].iloc[0]}")
        piv = runs.pivot(index=["question_id", "question_text"], columns="persona", values="status")[PERSONAS]
        rows = runs.pivot(index=["question_id", "question_text"], columns="persona", values="row_count")[PERSONAS]
        cells = piv.astype(str) + " (" + rows.astype(int).astype(str) + " rows)"
        fails = int((piv != "PASS").sum().sum())
        st.metric("Failing cells", f"{fails} / {piv.size}", delta=None)
        st.dataframe(cells.style.map(lambda v: "background-color:#d4edda;color:#155724" if v.startswith("PASS")
                                     else "background-color:#f8d7da;color:#721c24"), use_container_width=True)
        scope = sql("SELECT * FROM ONTOFLAKE.GOV.PERSONA_SCOPE")
        st.markdown("**Persona scopes** (roles absent from this table are global):")
        st.dataframe(scope, hide_index=True)
        with st.expander("Policies in force"):
            try:
                st.code(sql("SELECT policy_name, policy_kind, ref_entity_name, ref_column_name FROM TABLE(ONTOFLAKE.INFORMATION_SCHEMA.POLICY_REFERENCES(REF_ENTITY_NAME => 'ONTOFLAKE.CONFORMED.FACT_PURCHASE_ORDER_LINE', REF_ENTITY_DOMAIN => 'TABLE'))").to_string(index=False))
            except Exception:
                st.code("PLANT_REGION_RAP  ROW_ACCESS_POLICY  FACT_* (plant_region)\nCOST_MASK         MASKING_POLICY     FACT_PURCHASE_ORDER_LINE (unit_price, po_line_value, price_variance_value)")


# ---------- Glossary ----------
with tab_glossary:
    st.markdown("Canonical definitions live **in the semantic view**, not in dashboards or people's heads.")
    owner = {"SHIPMENT": "procurement", "PO_LINE": "procurement", "SO_LINE": "logistics / planning", "INVENTORY": "planning"}
    g = pd.DataFrame([{
        "metric": m["ref"], "owner": owner.get(m["table"], ""), "definition": m["comment"],
        "formula": m["expression"], "synonyms": ", ".join(m["synonyms"]),
    } for m in meta["METRIC"]])
    st.dataframe(g, use_container_width=True, hide_index=True, height=650)


# ---------- Ontology ----------
with tab_ontology:
    st.markdown("Entities and relationships as declared in the semantic view.")
    facts = {"PO_LINE", "SHIPMENT", "SO_LINE", "INVENTORY"}
    dot = ["digraph G { rankdir=LR; bgcolor=transparent; node [style=filled, fontname=Helvetica, fontcolor=white, color=white];",
           "edge [color=gray70, fontcolor=gray70, fontname=Helvetica, fontsize=10];"]
    for t in meta["TABLE"]:
        shape, fill = ("box", "#1f6feb") if t["name"] in facts else ("ellipse", "#2da44e")
        dot.append(f'  {t["name"]} [shape={shape}, fillcolor="{fill}"];')
    for r in meta["RELATIONSHIP"]:
        dot.append(f'  {r["table"]} -> {r["ref_table"]} [label="{r["name"].lower()}"];')
    dot.append("}")
    st.graphviz_chart("\n".join(dot), use_container_width=True)
    st.caption("Blue boxes = facts (metric grains). Green = dimensions/entities.")
    st.dataframe(pd.DataFrame([{"entity": t["name"], "synonyms": ", ".join(t["synonyms"]), "comment": t["comment"]}
                               for t in meta["TABLE"]]), hide_index=True, use_container_width=True)
