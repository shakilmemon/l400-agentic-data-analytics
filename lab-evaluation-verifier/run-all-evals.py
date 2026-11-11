#!/usr/bin/env python3
"""
Run all evaluations in sequential order.
Supports both Automatic submission (local proxy) and Manual submission (web upload).
"""

import os
import re
import sys
import glob
import json
import subprocess


def extract_eval_status(output: str, returncode: int) -> str:
    """Extracts PASS/FAIL from validator JSON output, or fallback status."""
    # Look for "pass-fail": "PASS" / "FAIL" in the validator JSON output
    matches = re.findall(r'"pass-fail"\s*:\s*"([^"]+)"', output, flags=re.IGNORECASE)
    if matches:
        return matches[-1].upper()

    if returncode != 0:
        return f"ERROR (exit code {returncode})"

    if "Manual Submission Instructions" in output:
        return "PACKAGED (Manual Upload)"

    return "COMPLETED"


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scripts = sorted(glob.glob(os.path.join(script_dir, "[0-9][0-9]-*.py")))

    if not scripts:
        print(f"No evaluation scripts found in {script_dir}")
        sys.exit(1)

    print("================================================================================")
    print(f" Running All Lab Evaluations ({len(scripts)} scripts)")
    print("================================================================================")

    results = []
    for script in scripts:
        script_name = os.path.basename(script)
        print("\n--------------------------------------------------------------------------------")
        print(f"Running: {script_name}")
        print("--------------------------------------------------------------------------------", flush=True)
        cmd = [sys.executable, "-u", script] + sys.argv[1:]
        output_lines = []
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as proc:
            for line in proc.stdout:
                print(line, end="", flush=True)
                output_lines.append(line)
            proc.wait()
            returncode = proc.returncode

        full_output = "".join(output_lines)
        status = extract_eval_status(full_output, returncode)
        results.append((script_name, status))

    print("\n================================================================================")
    print(" Evaluation Run Summary")
    print("================================================================================")
    pass_count = 0
    fail_count = 0
    for sname, status in results:
        if status == "PASS":
            pass_count += 1
        elif status.startswith("FAIL") or status.startswith("ERROR"):
            fail_count += 1
        print(f"  {sname:<42} : {status}")
    print("--------------------------------------------------------------------------------")
    print(f"  Total: {len(results)} | PASS: {pass_count} | FAIL: {fail_count}")
    print("================================================================================")

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
