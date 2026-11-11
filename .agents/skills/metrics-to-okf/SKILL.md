---
name: metrics-to-okf
description: Parse legacy SQL scripts and export them to OKF-compliant reference metrics documents containing description prompts and SQL code blocks.
---

# Skill: Metric to OKF

This skill parses legacy SQL scripts (containing one or more metric SQL query definitions) and converts them into Open Knowledge Format (OKF) metrics reference documents under `okf/references/metrics/`. These metrics serve as golden queries for conversational analytics.

## Quick Start & Usage

This skill provides a helper script `run.py` that processes SQL files and outputs OKF metrics files.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/metrics-to-okf/scripts'))
import run
```

## Available Functions

The following core functions are available in [run.py](file:///.agents/skills/metrics-to-okf/scripts/run.py):

### 1. Export Metrics from SQL to OKF
- **Function**: `export_metrics_to_okf(sql_file_path: str, okf_root_dir: str = "okf") -> dict`
- **Description**: Parses the specified SQL script, extracts all Metric sections (titles, descriptions, and SQL queries), and outputs them as OKF metrics markdown documents inside `okf/references/metrics/`.

## Example Usage

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/metrics-to-okf/scripts'))
import run

# Export metrics from a legacy Oracle export SQL file
result = run.export_metrics_to_okf("docs/requirements/Legacy-SQL/Legacy_Oracle_Export.sql")
print(result)
```

## Response Schema Format

All operations return a standard JSON dict structured like:

```json
{
  "status": "success",
  "tool_name": "export_metrics_to_okf",
  "messages": [
    "Successfully read SQL script at 'docs/requirements/Legacy-SQL/Legacy_Oracle_Export.sql'.",
    "Parsed 2 metrics from SQL file.",
    "Exported metric: 'Blended D2C Customer Acquisition Cost (CAC)' -> 'okf/references/metrics/blended_d2c_customer_acquisition_cost_cac.md'",
    "Exported metric: 'Inventory Turn Ratio' -> 'okf/references/metrics/inventory_turn_ratio.md'",
    "Successfully processed and exported all metrics!"
  ],
  "results": {
    "metrics_exported_count": 2,
    "output_dir": "okf/references/metrics"
  }
}
```
