"""Result-set comparison — grade SQL by OUTCOME, not query text.

SQL text is a proxy; what matters is whether the user gets the right answer. Two
correct queries can look nothing alike, and wrong-looking SQL can be right. So we
compare the *result sets* the queries produce:

  Tier 1  EXACT       — same rows (as sets, order-independent)      provable
  Tier 2  CONTAINMENT — golden rows ⊆ agent rows (agent returned a  provable
                        superset that still contains the answer)
  Tier 3  DERIVABLE   — column shapes differ / the answer must be   LLM-judge
                        derived from a wider result (handled in     (over results,
                        grader.py by judging the rendered rows)      not SQL text)

This module owns the provable tiers (1 & 2) as pure Python — no BigQuery, no LLM —
so they're fast and unit-testable. grader.py executes the golden SQL to get the
reference rows and calls in here; tier 3 falls back to an LLM judge over the
rendered results.
"""


def _canonical_row(row):
    """A hashable, order-independent key for a result row.

    Rows are dicts {column: value}. We key on the SET of (column, value) pairs so
    column ORDER doesn't matter. Values are stringified so 3 and 3.0 and Decimal(3)
    compare equal at the surface level (see _norm_value)."""
    return frozenset((str(k), _norm_value(v)) for k, v in row.items())


def _norm_value(v):
    """Normalize a cell for comparison: numbers compare by value (3 == 3.0),
    everything else by trimmed string. Keeps 1000 == 1000.0 == '1000' from being
    spurious mismatches while staying dependency-free."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        f = float(v)
        return str(int(f)) if f.is_integer() else str(round(f, 4))
    s = str(v).strip()
    # currency / percentage / numeric-looking strings normalize like numbers
    cleaned = s.lstrip("$€£¥").rstrip("%").strip().replace(",", "")
    if cleaned.upper().startswith("USD"):
        cleaned = cleaned[3:].strip()
    elif cleaned.upper().endswith("USD"):
        cleaned = cleaned[:-3].strip()
    try:
        f = float(cleaned)
        return str(int(f)) if f.is_integer() else str(round(f, 4))
    except (ValueError, AttributeError):
        return s


def _values_multiset(rows):
    """All normalized cell VALUES across rows, ignoring column names/positions.
    Used for containment when column names differ but the numbers are present."""
    out = []
    for r in rows:
        for v in r.values():
            out.append(_norm_value(v))
    return sorted(out)


def compare_results(golden_rows, agent_rows):
    """Compare two result sets (lists of {column: value} dicts) by outcome.

    Returns a dict:
        tier      : 'exact' | 'containment' | 'value_containment' | 'derivable_aggregation'
                    | 'mismatch' | 'empty_golden' | 'no_agent_data'
        equivalent: bool  (exact set match)
        contains  : bool  (golden rows ⊆ agent rows, as row sets)
        passed    : bool  (equivalent OR contains OR value_containment OR derivable_aggregation)
        detail    : short human string
    Row-set logic is order-independent; column order is ignored. When column NAMES
    differ (agent renamed/added columns) row-set containment can miss, so we also
    check value-containment (every golden cell value appears in the agent result)
    as a weaker positive signal. Anything murkier is left to the tier-3 LLM judge.
    """
    if agent_rows is None:
        return {"tier": "no_agent_data", "equivalent": False, "contains": False,
                "passed": False, "detail": "agent returned no data"}
    golden_rows = golden_rows or []
    agent_rows = agent_rows or []
    if not golden_rows:
        return {"tier": "empty_golden", "equivalent": False, "contains": False,
                "passed": False, "detail": "golden result is empty"}

    g_set = [_canonical_row(r) for r in golden_rows]
    a_set = [_canonical_row(r) for r in agent_rows]
    from collections import Counter
    gc, ac = Counter(g_set), Counter(a_set)

    if gc == ac:
        return {"tier": "exact", "equivalent": True, "contains": True,
                "passed": True, "detail": "identical result sets"}
    # golden ⊆ agent  (agent returned a superset that still contains the answer)
    if all(ac[k] >= gc[k] for k in gc):
        return {"tier": "containment", "equivalent": False, "contains": True,
                "passed": True,
                "detail": f"agent result contains all {len(golden_rows)} "
                          "golden row(s) (superset)"}
    # column names differ but the answer values are all present in the agent result
    gv, av = Counter(_values_multiset(golden_rows)), Counter(_values_multiset(agent_rows))
    if all(av[k] >= gv[k] for k in gv):
        return {"tier": "value_containment", "equivalent": False,
                "contains": False, "passed": True,
                "detail": "all golden values present in agent result "
                          "(columns differ)"}

    # check aggregation derivability (e.g. golden sum equals sum of a metric column in agent rows)
    if len(golden_rows) == 1 and len(golden_rows[0]) == 1:
        g_val = list(golden_rows[0].values())[0]
        try:
            g_num = float(_norm_value(g_val))
            keys = {k for r in agent_rows for k in r.keys()}
            for k in keys:
                col_nums = []
                for r in agent_rows:
                    if k in r:
                        try:
                            col_nums.append(float(_norm_value(r[k])))
                        except (ValueError, TypeError):
                            pass
                if len(col_nums) == len(agent_rows) and abs(sum(col_nums) - g_num) < 1.0:
                    return {"tier": "derivable_aggregation", "equivalent": False,
                            "contains": False, "passed": True,
                            "detail": f"golden scalar {g_num} matches sum of agent column '{k}'"}
        except (ValueError, TypeError):
            pass

    if len(agent_rows) == 1 and len(agent_rows[0]) == 1:
        a_val = list(agent_rows[0].values())[0]
        try:
            a_num = float(_norm_value(a_val))
            keys = {k for r in golden_rows for k in r.keys()}
            for k in keys:
                col_nums = []
                for r in golden_rows:
                    if k in r:
                        try:
                            col_nums.append(float(_norm_value(r[k])))
                        except (ValueError, TypeError):
                            pass
                if len(col_nums) == len(golden_rows) and abs(sum(col_nums) - a_num) < 1.0:
                    return {"tier": "derivable_aggregation", "equivalent": False,
                            "contains": False, "passed": True,
                            "detail": f"agent scalar {a_num} matches sum of golden column '{k}'"}
        except (ValueError, TypeError):
            pass

    return {"tier": "mismatch", "equivalent": False, "contains": False,
            "passed": False, "detail": "agent result does not contain the "
                                       "golden answer"}
