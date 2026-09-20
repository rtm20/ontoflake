"""Persona consistency harness.

Runs every golden question against the semantic view under every persona role and proves that:
  * global personas get byte-identical answers (same rows, same numbers),
  * scoped personas get exactly the global answer filtered to their scope,
  * masked metrics come back NULL for non-entitled personas (never a different number).
Exit code 1 on any failure. Writes harness/report.json for the UI.
"""
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

import snowflake.connector
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
TOL = Decimal("0.000001")
# Baseline = an unscoped, unmasked role. ACCOUNTADMIN locally; a global persona in CI (service user is not admin).
BASELINE_ROLE = os.environ.get("HARNESS_BASELINE_ROLE", "ACCOUNTADMIN")
PERSIST = os.environ.get("HARNESS_NO_PERSIST", "") == ""


def load_spec():
    with open(os.path.join(HERE, "golden_questions.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_sql(view, q):
    sql = f"SELECT * FROM SEMANTIC_VIEW({view} DIMENSIONS {', '.join(q['dimensions'])} METRICS {', '.join(q['metrics'])})"
    if q.get("where"):
        sql += f" WHERE {q['where']}"
    return sql


def run(cur, role, sql, n_dims):
    cur.execute(f"USE ROLE {role}")
    cur.execute(sql)
    cols = [c[0].lower() for c in cur.description]
    rows = {}
    for r in cur.fetchall():
        rows[tuple(r[:n_dims])] = dict(zip(cols[n_dims:], r[n_dims:]))
    return cols, rows


def num_equal(a, b):
    if a is None or b is None:
        return a is None and b is None
    return abs(Decimal(str(a)) - Decimal(str(b))) <= TOL


def check(baseline, actual, persona, q, cols):
    """Return list of failure strings."""
    scope = persona.get("scope", "global")
    masked = {m.split(".")[-1] for m in persona.get("masked_metrics", [])}
    dims = [d.split(".")[-1] for d in q["dimensions"]]
    failures = []

    if scope == "global":
        expected = baseline
    else:
        (col, val), = scope.items()
        idx = dims.index(col)
        expected = {k: v for k, v in baseline.items() if k[idx] == val}

    if set(expected) != set(actual):
        failures.append(f"row-set differs: expected {len(expected)} rows, got {len(actual)}")
        return failures

    for key, exp_metrics in expected.items():
        for metric, exp_val in exp_metrics.items():
            act_val = actual[key][metric]
            if metric in masked:
                if act_val is not None:
                    failures.append(f"{key} {metric}: expected NULL (masked), got {act_val}")
            elif not num_equal(exp_val, act_val):
                failures.append(f"{key} {metric}: {exp_val} != {act_val}")
    return failures


def persist(cur, report):
    cur.execute("USE ROLE ACCOUNTADMIN")
    cur.execute("""CREATE TABLE IF NOT EXISTS ONTOFLAKE.GOV.CONSISTENCY_RUN (
        run_ts TIMESTAMP_LTZ, question_id STRING, question_text STRING, sql_text STRING, persona STRING,
        status STRING, row_count INT, baseline_rows INT, failures VARIANT)""")
    run_ts = datetime.now(timezone.utc).isoformat()
    rows = [
        (run_ts, q["id"], q["text"], q["sql"], name, r["status"], r["rows"], q["baseline_rows"], json.dumps(r["failures"]))
        for q in report["questions"] for name, r in q["results"].items()
    ]
    cur.execute("BEGIN")
    for row in rows:
        cur.execute(
            "INSERT INTO ONTOFLAKE.GOV.CONSISTENCY_RUN SELECT %s, %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s)",
            row,
        )
    cur.execute("COMMIT")


def main():
    spec = load_spec()
    conn = snowflake.connector.connect(connection_name=os.environ.get("SNOWFLAKE_CONNECTION", "hackathon"))
    cur = conn.cursor()
    report = {"semantic_view": spec["semantic_view"], "personas": list(spec["personas"]), "questions": []}
    total_fail = 0

    print(f"{'Q':<5}{'question':<62}" + "".join(f"{p:<20}" for p in spec["personas"]))
    for q in spec["questions"]:
        sql = build_sql(spec["semantic_view"], q)
        n_dims = len(q["dimensions"])
        cols, baseline = run(cur, BASELINE_ROLE, sql, n_dims)
        qrep = {"id": q["id"], "text": q["text"], "sql": sql, "baseline_rows": len(baseline), "results": {}}
        line = f"{q['id']:<5}{q['text'][:60]:<62}"
        for name, persona in spec["personas"].items():
            _, actual = run(cur, name, sql, n_dims)
            failures = check(baseline, actual, persona, q, cols)
            status = "PASS" if not failures else "FAIL"
            total_fail += bool(failures)
            qrep["results"][name] = {"status": status, "rows": len(actual), "failures": failures[:5]}
            line += f"{status + ' (' + str(len(actual)) + ' rows)':<20}"
        report["questions"].append(qrep)
        print(line)

    report["summary"] = {"questions": len(spec["questions"]), "personas": len(spec["personas"]), "failed_cells": total_fail}
    with open(os.path.join(HERE, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    if PERSIST:
        persist(cur, report)

    print(f"\n{len(spec['questions'])} questions x {len(spec['personas'])} personas -> {total_fail} failing cells")
    for qrep in report["questions"]:
        for name, res in qrep["results"].items():
            for fl in res["failures"]:
                print(f"  {qrep['id']} {name}: {fl}")
    sys.exit(1 if total_fail else 0)


if __name__ == "__main__":
    main()
