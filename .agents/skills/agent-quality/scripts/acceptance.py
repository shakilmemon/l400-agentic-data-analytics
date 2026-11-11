"""Acceptance testing — the synchronous quality GATE at agent create/update.

Given an acceptance set (golden questions + expected behavior, authored as an OKF
file alongside the agent def — see mike-files/ca-acceptance-okf-proposal.md), run
each question against a deployed CA agent and produce gradable ROWS. Those rows go
to a grader (grader.py) to decide pass/fail.

This is the "run it right after create" capability: acceptance can gate an agent
the moment it exists, before any production traffic (which observability/evaluation
need). It reuses the conversational-analytics skill to actually talk to the agent —
this module is the harness, not a second CAI client.

Row shape (the trust trio's currency):
    {"id", "question", "category", "expectation_type", "ground_truth",
     "agent_response"}
"""

import os
import sys

from common import _ok, _fail, EXPECTATION_TYPES, load_env_config


def _load_ca():
    """Import the conversational-analytics skill's `ca` facade.

    agent-quality DEPENDS ON the CAI skill for talking to agents (correct
    direction: quality points at agents the CAI skill builds). Resolve the
    sibling skill on disk; allow CA_SKILL_SCRIPTS override for portability.
    """
    candidates = [
        os.environ.get("CA_SKILL_SCRIPTS"),
        os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     "..", "..", "conversational-analytics",
                                     "scripts")),
    ]
    for path in candidates:
        if path and os.path.isdir(path):
            if path not in sys.path:
                sys.path.insert(0, path)
            import ca  # noqa: E402
            return ca
    raise ImportError(
        "Could not find the conversational-analytics skill's scripts/ dir. "
        "Set CA_SKILL_SCRIPTS to <repo>/.agents/skills/"
        "conversational-analytics/scripts.")


def parse_acceptance_set(path):
    """Parse an acceptance OKF file (YAML frontmatter) into test-case dicts.

    Accepts the schema in ca-acceptance-okf-proposal.md: testCases[{id, question,
    category, expectationType, groundTruth{...}, notes}]. groundTruth is flattened
    to a single string reference for grading (sql / value / mustAsk / mustRefuse).
    """
    tool = "parse_acceptance_set"
    try:
        text = open(path, encoding="utf-8").read().strip()
        if text.startswith("---"):
            text = text.split("---", 2)[1] if text.count("---") >= 2 else text[3:]
        try:
            import yaml
            spec = yaml.safe_load(text) or {}
        except ImportError:
            # Fallback pure-Python YAML parser for testCases schema
            spec = {"testCases": []}
            import re
            agent_id_match = re.search(r'(?:dataAgentId|data_agent_id):\s*(.*)', text)
            if agent_id_match:
                spec["dataAgentId"] = agent_id_match.group(1).strip().strip('"').strip("'")
            disp_match = re.search(r'(?:displayName|display_name):\s*(.*)', text)
            if disp_match:
                spec["displayName"] = disp_match.group(1).strip().strip('"').strip("'")
            desc_match = re.search(r'description:\s*(.*)', text)
            if desc_match:
                spec["description"] = desc_match.group(1).strip().strip('"').strip("'")
            case_blocks = re.split(r'\n\s*-\s+id:\s*', text)
            for idx, cb in enumerate(case_blocks):
                if idx == 0 and not cb.startswith("id:"):
                    continue
                lines = cb.splitlines()
                tc_id = lines[0].strip().strip('"').strip("'")
                
                # Extract fields with regex
                q_match = re.search(r'question:\s*"(.*?)"|question:\s*\'(.*?)\'|question:\s*(.*)', cb)
                question = (q_match.group(1) or q_match.group(2) or q_match.group(3) or "").strip() if q_match else ""
                
                cat_match = re.search(r'category:\s*"(.*?)"|category:\s*\'(.*?)\'|category:\s*(.*)', cb)
                category = (cat_match.group(1) or cat_match.group(2) or cat_match.group(3) or "").strip() if cat_match else ""
                
                et_match = re.search(r'expectationType:\s*(\w+)|expectation_type:\s*(\w+)', cb)
                et = (et_match.group(1) or et_match.group(2) or "answer").strip() if et_match else "answer"
                
                notes_match = re.search(r'notes:\s*"(.*?)"|notes:\s*\'(.*?)\'|notes:\s*(.*)', cb)
                notes = (notes_match.group(1) or notes_match.group(2) or notes_match.group(3) or "").strip() if notes_match else ""
                
                # Build a structured groundTruth dict (mirrors the yaml path) so
                # multi-turn fields survive; the shared loop below flattens it.
                gt = {}
                sql_match = re.search(r'sql:\s*\|?\n(.*?)(?=\n\s*\w+:|\Z)', cb, re.DOTALL)
                if not sql_match:
                    sql_match_inline = re.search(r'sql:\s*([^\n]+)', cb)
                    if sql_match_inline:
                        gt["sql"] = sql_match_inline.group(1).strip()
                else:
                    gt["sql"] = sql_match.group(1).strip()

                must_ask_match = re.search(r'mustAsk:\s*"(.*?)"|mustAsk:\s*\'(.*?)\'|mustAsk:\s*(.*)', cb)
                must_refuse_match = re.search(r'mustRefuse:\s*"(.*?)"|mustRefuse:\s*\'(.*?)\'|mustRefuse:\s*(.*)', cb)
                follow_match = re.search(r'followUpUserResponse:\s*"(.*?)"|followUpUserResponse:\s*\'(.*?)\'|followUpUserResponse:\s*(.*)', cb)


                if must_ask_match:
                    gt["mustAsk"] = (must_ask_match.group(1) or must_ask_match.group(2) or must_ask_match.group(3) or "").strip()
                if must_refuse_match:
                    gt["mustRefuse"] = (must_refuse_match.group(1) or must_refuse_match.group(2) or must_refuse_match.group(3) or "").strip()
                if follow_match:
                    gt["followUpUserResponse"] = (follow_match.group(1) or follow_match.group(2) or follow_match.group(3) or "").strip()

                spec["testCases"].append({
                    "id": tc_id,
                    "question": question,
                    "category": category,
                    "expectationType": et,
                    "groundTruth": gt,
                    "notes": notes
                })

        cases = []
        for tc in spec.get("testCases", []) or []:
            et = tc.get("expectationType") or tc.get("expectation_type") or "answer"
            if et not in EXPECTATION_TYPES:
                et = "answer"
            gt = tc.get("groundTruth") or tc.get("ground_truth") or {}
            gt = gt if isinstance(gt, dict) else {"value": gt}
            # For clarification_then_answer the golden SQL is what the RESOLVED
            # answer is graded against, so it is the primary ground_truth; the
            # mustAsk + followUpUserResponse drive/verify the first (ask) turn.
            if et == "clarification_then_answer":
                ref = gt.get("sql") or gt.get("value") or gt.get("expected")
            else:
                ref = (gt.get("sql") or gt.get("value") or gt.get("mustAsk")
                       or gt.get("mustRefuse") or gt.get("expected"))
            cases.append({
                "id": tc.get("id"),
                "question": tc.get("question"),
                "category": tc.get("category"),
                "expectation_type": et,
                "ground_truth": ref,
                # multi-turn fields (present only for clarification_then_answer):
                "must_ask": gt.get("mustAsk"),
                "follow_up_user_response": gt.get("followUpUserResponse"),
                "notes": tc.get("notes"),
            })
        meta = {"data_agent_id": spec.get("dataAgentId"),
                "display_name": spec.get("displayName"),
                "case_count": len(cases)}
        return _ok(tool, {"cases": cases, "meta": meta},
                   [f"Parsed {len(cases)} acceptance case(s)."])
    except Exception as e:
        return _fail(tool, f"parse_acceptance_set failed: {e}")


def run_acceptance(project_id, location, agent_id, cases, ca=None):
    """Run each acceptance case against a STORED agent (stateless 'agent' mode)
    and return gradable rows capturing the FULL trace of each turn.

    Uses stateless 'agent' mode: each case is independent (no shared history), so
    acceptance is deterministic and order-free. Each row keeps the complete signal
    the run exposes so the grader can use its strongest check:
      * generated_sql  -> unlocks SQL-equivalence grading (agent SQL vs the case's
                          golden SQL) instead of prose-only scoring;
      * thoughts, data -> reasoning + returned rows, for failure diagnostics.
    (Per-tool ADK trajectory is the only signal a stateless run can't provide; it
    needs the ADK plugin and acceptance doesn't require it.)
    `ca` may be injected for testing; otherwise the CAI skill facade is loaded.
    """
    tool = "run_acceptance"
    try:
        ca = ca or _load_ca()
        agent_name = (f"projects/{project_id}/locations/{location}"
                      f"/dataAgents/{agent_id}")

        def _trace(resp):
            """Pull the full trace out of a chat response (or empties on error)."""
            if resp.get("status") == "success":
                a = resp["results"]["answer"]
                return {"text": a.get("text"),
                        "followups": a.get("followups") or [],
                        "generated_sql": a.get("generated_sql"),
                        "thoughts": a.get("thoughts") or [],
                        "data": a.get("data"),
                        "history": resp["results"].get("history")}, True
            return {"text": None, "followups": [], "generated_sql": None,
                    "thoughts": [], "data": None, "history": None}, False

        rows, errors = [], 0
        for c in cases:
            row = {
                "id": c.get("id"),
                "question": c["question"],
                "category": c.get("category"),
                "expectation_type": c["expectation_type"],
                "ground_truth": c.get("ground_truth"),
            }
            resp = ca.chat(project_id, location, c["question"], "agent",
                           agent_name=agent_name, history=[])
            t1, ok = _trace(resp)
            if not ok:
                errors += 1

            if c["expectation_type"] == "clarification_then_answer":
                # Turn 1 = the agent's clarifying question; then send the simulated
                # user reply and grade the RESOLVED answer. Keep both turns so the
                # grader can check both "did it ask?" and "is the answer right?".
                reply = c.get("follow_up_user_response") or "yes"
                resp2 = ca.chat(project_id, location, reply, "agent",
                                agent_name=agent_name, history=t1.get("history") or [])
                t2, ok2 = _trace(resp2)
                if not ok2 and ok:
                    errors += 1
                row.update({
                    # turn 1 (the ask) — for the "did it clarify?" half
                    "clarification_response": t1["text"],
                    "clarification_followups": t1["followups"],
                    "must_ask": c.get("must_ask"),
                    "follow_up_user_response": reply,
                    # turn 2 (the resolved answer) is the primary graded response
                    "agent_response": t2["text"],
                    "generated_sql": t2["generated_sql"],
                    "followups": t2["followups"],
                    "thoughts": t2["thoughts"],
                    "data": t2["data"],
                })
            else:
                row.update({
                    "agent_response": t1["text"],
                    # the SQL the agent ran — lets the grader compare to golden SQL
                    "generated_sql": t1["generated_sql"],
                    # a clarification shows up as followups with no answer; keep
                    # them so the grader can judge 'did it ask?'
                    "followups": t1["followups"],
                    # fuller trace for diagnostics (not required by the grader)
                    "thoughts": t1["thoughts"],
                    "data": t1["data"],
                })
            rows.append(row)

        msg = f"Ran {len(rows)} case(s) against '{agent_id}'"
        msg += f" ({errors} chat error(s))." if errors else "."
        return _ok(tool, {"rows": rows, "error_count": errors}, [msg])
    except Exception as e:
        return _fail(tool, f"run_acceptance failed: {e}")


def format_acceptance_report(graded_rows, meta=None):
    """Generate a clean, structured GitHub Markdown report from graded acceptance rows."""
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    total = len(graded_rows)
    passed = sum(1 for r in graded_rows if r.get("result_pass") is True or r.get("overall_pass") is True)
    failed = total - passed
    pass_rate = (passed / total * 100) if total else 0.0

    target_agent = (meta.get("data_agent_id") if meta else None) or "premium-outdoor-gear-agent"
    suite_title = (meta.get("displayName") if meta else None) or "Conversational Analytics Acceptance Suite"

    lines = [
        f"# {suite_title} — Evaluation Report",
        "",
        f"**Date:** {now_str}  ",
        f"**Target Agent:** `{target_agent}`  ",
        f"**Evaluation Strategy:** Outcome-Based Result Grading (Tiers 1–3 + BigQuery AI Judges)  ",
        "",
        "## Executive Summary",
        "",
        f"- **Pass Rate:** {pass_rate:.1f}% ({passed} / {total})",
        f"- **Total Cases:** {total}",
        f"- **Passed:** {passed}",
        f"- **Failed:** {failed}",
        "",
        "## Evaluation Results Matrix",
        "",
        "| ID | Category | Expectation Type | Status | Outcome Tier | Detail |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in graded_rows:
        tc_id = r.get("id", "unknown")
        cat = r.get("category", "General")
        et = r.get("expectation_type", "answer")
        p = r.get("result_pass") if r.get("result_pass") is not None else r.get("overall_pass")
        status = "✅ PASS" if p else "❌ FAIL"
        tier = r.get("result_tier") or ("exact" if p else "mismatch")
        detail = r.get("result_detail") or ("Passed" if p else "Failed")
        lines.append(f"| `{tc_id}` | {cat} | `{et}` | **{status}** | `{tier}` | {detail} |")

    lines.extend([
        "",
        "## Detailed Case-by-Case Breakdown",
        ""
    ])

    for idx, r in enumerate(graded_rows, 1):
        tc_id = r.get("id", "unknown")
        p = r.get("result_pass") if r.get("result_pass") is not None else r.get("overall_pass")
        verdict = "PASS" if p else "FAIL"
        badge = "✅" if p else "❌"
        lines.extend([
            f"### {idx}. `{tc_id}` — {badge} {verdict}",
            "",
            f"- **Category:** {r.get('category')}",
            f"- **Expectation Type:** `{r.get('expectation_type')}`",
            f"- **Outcome Tier:** `{r.get('result_tier')}`",
            f"- **Outcome Evaluation:** {r.get('result_detail')}",
            "",
            f"**Input Prompt:**",
            f"> {r.get('question')}",
            ""
        ])

        if r.get("expectation_type") == "clarification_then_answer":
            lines.extend([
                "**Multi-Turn Interaction:**",
                f"- **Turn 1 (Clarification Response):** {r.get('clarification_response') or '(None)'}",
                f"- **Follow-up User Reply:** `{r.get('follow_up_user_response')}`",
                ""
            ])

        if r.get("agent_response"):
            lines.extend([
                "**Agent Response:**",
                r.get("agent_response"),
                ""
            ])

        gen_sql = r.get("generated_sql")
        gt_sql = r.get("ground_truth")
        if gen_sql or (gt_sql and "SELECT" in str(gt_sql).upper()):
            lines.append("**SQL Comparison:**")
            if gen_sql:
                lines.extend([
                    "```sql",
                    "-- Agent Generated SQL",
                    gen_sql.strip(),
                    "```",
                    ""
                ])
            if gt_sql and "SELECT" in str(gt_sql).upper():
                lines.extend([
                    "```sql",
                    "-- Golden Reference SQL",
                    str(gt_sql).strip(),
                    "```",
                    ""
                ])

        data = r.get("data")
        if data:
            import json
            data_sample = data[:5] if isinstance(data, list) else data
            lines.extend([
                "<details>",
                f"<summary>Returned Agent Data ({len(data) if isinstance(data, list) else 1} rows)</summary>",
                "",
                "```json",
                json.dumps(data_sample, indent=2, default=str),
                "```",
                "</details>",
                ""
            ])

        thoughts = r.get("thoughts")
        if thoughts:
            lines.extend([
                "<details>",
                "<summary>Agent Reasoning Trace</summary>",
                "",
            ])
            for t in thoughts:
                lines.append(f"- {t}")
            lines.extend([
                "</details>",
                ""
            ])

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def run_acceptance_suite(acceptance_path, output_report_path=None, project_id=None,
                         location="global", agent_id=None, outcome_grading=True,
                         max_bytes_billed=10_000_000_000, knowledge="", ca=None):
    """Execute acceptance suite end-to-end:
    1. Parse acceptance test cases from markdown or YAML.
    2. Query Conversational Analytics agent.
    3. Grade outcomes.
    4. Format and save report.
    """
    tool = "run_acceptance_suite"
    try:
        parsed = parse_acceptance_set(acceptance_path)
        if parsed.get("status") != "success":
            return parsed
        cases = parsed["results"]["cases"]
        meta = parsed["results"]["meta"]

        target_agent = agent_id or meta.get("data_agent_id")
        if not project_id:
            env = load_env_config()
            project_id = env.get("gcp-project-id") or env.get("project_id")

        if not project_id:
            return _fail(tool, "No project_id provided and agent-config.json not found")
        if not target_agent:
            return _fail(tool, "No agent_id provided in acceptance set or parameters")

        # Run acceptance against the agent
        run_res = run_acceptance(project_id, location, target_agent, cases, ca=ca)
        if run_res.get("status") != "success":
            return run_res

        rows = run_res["results"]["rows"]

        # Outcome grading
        if outcome_grading:
            import grader
            grade_res = grader.grade_results(
                rows,
                project_id=project_id,
                max_bytes_billed=max_bytes_billed,
                knowledge=knowledge,
                judge_fallback=True
            )
            if grade_res.get("status") == "success":
                graded_rows = grade_res["results"]["graded"]
            else:
                graded_rows = rows
        else:
            graded_rows = rows

        report_md = format_acceptance_report(graded_rows, meta=meta)
        if output_report_path:
            import os
            os.makedirs(os.path.dirname(os.path.abspath(output_report_path)), exist_ok=True)
            with open(output_report_path, "w", encoding="utf-8") as f:
                f.write(report_md)

        pass_count = sum(1 for r in graded_rows if r.get("result_pass") is True)
        total_count = len(graded_rows)
        pass_rate = (pass_count / total_count) if total_count else 0.0

        return _ok(tool, {
            "cases": graded_rows,
            "pass_count": pass_count,
            "total_count": total_count,
            "pass_rate": pass_rate,
            "report_path": output_report_path
        }, [f"Acceptance suite finished: {pass_count}/{total_count} ({pass_rate:.1%}) passed."])
    except Exception as e:
        return _fail(tool, f"run_acceptance_suite failed: {e}")
