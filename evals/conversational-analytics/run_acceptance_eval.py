#!/usr/bin/env python3
"""Runner script to execute Conversational Analytics acceptance evaluation suite

Uses the updated agent-quality skill with outcome-based grading (Tiers 1-3).
Outputs results to evals/conversational-analytics/premium-outdoor-gear-acceptance-output.md
"""

import os
import sys
import argparse

# Ensure agent-quality scripts are in path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
AQ_SCRIPTS = os.path.join(REPO_ROOT, ".agents/skills/agent-quality/scripts")
if AQ_SCRIPTS not in sys.path:
    sys.path.insert(0, AQ_SCRIPTS)

import run


def main():
    parser = argparse.ArgumentParser(description="Run Conversational Analytics Acceptance Suite")
    parser.add_argument("--acceptance-file", default="evals/conversational-analytics/premium-outdoor-gear-acceptance.md",
                        help="Path to acceptance suite markdown/yaml")
    parser.add_argument("--output-file", default="evals/conversational-analytics/premium-outdoor-gear-acceptance-output.md",
                        help="Path to output markdown report")
    parser.add_argument("--project-id", default=None,
                        help="Google Cloud project ID (defaults to agent-config.json)")
    parser.add_argument("--agent-id", default="premium-outdoor-gear-agent",
                        help="Data agent ID")
    parser.add_argument("--location", default="global",
                        help="Data agent location")
    args = parser.parse_args()

    acceptance_path = os.path.abspath(os.path.join(REPO_ROOT, args.acceptance_file))
    output_path = os.path.abspath(os.path.join(REPO_ROOT, args.output_file))

    print(f"Executing Acceptance Suite:")
    print(f"  Acceptance File : {acceptance_path}")
    print(f"  Output File     : {output_path}")
    print(f"  Agent ID        : {args.agent_id}")
    print("-" * 60)

    res = run.run_acceptance_suite(
        acceptance_path=acceptance_path,
        output_report_path=output_path,
        project_id=args.project_id,
        location=args.location,
        agent_id=args.agent_id,
        outcome_grading=True,
        max_bytes_billed=10_000_000_000,
    )

    if res.get("status") != "success":
        print(f"ERROR: Acceptance suite failed: {res.get('messages')}")
        sys.exit(1)

    pass_count = res["results"]["pass_count"]
    total_count = res["results"]["total_count"]
    pass_rate = res["results"]["pass_rate"]

    print("=" * 60)
    print(f"Evaluation Complete!")
    print(f"Passed: {pass_count} / {total_count} ({pass_rate:.1%})")
    print(f"Report saved to: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
