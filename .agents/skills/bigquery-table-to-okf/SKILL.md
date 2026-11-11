---
name: bigquery-table-to-okf
description: Export a single BigQuery table's metadata directly to an Open Knowledge Format (OKF) table file.
---

# Skill: BigQuery Table to OKF Export

Retrieve a single physical table's details and schema via the BigQuery REST API, then output its metadata into a clean, Open Knowledge Format (OKF) compliant table markdown file.

## Quick Start & Usage

This skill provides a helper script `run.py` that makes synchronous REST API calls to BigQuery, extracts the table's schema/metadata, and writes it into your OKF tables directory.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/bigquery-table-to-okf/scripts'))
import run
```

## Available Functions

 the following functions are available in [run.py](file:///.agents/skills/bigquery-table-to-okf/scripts/run.py):

### 1. Export a Single Table to OKF
- **Export Table to OKF**: `export_table_to_okf(project_id: str, dataset_id: str, table_id: str, tables_dir: str) -> dict`
  *Fetches table details and schema from BigQuery, then generates the table OKF markdown file.*

  **Arguments:**
  - `project_id`: GCP Project ID.
  - `dataset_id`: BigQuery Dataset ID.
  - `table_id`: BigQuery Table ID.
  - `tables_dir`: The destination path for OKF tables (e.g., `okf/tables`).

## Example Usage

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/bigquery-table-to-okf/scripts'))
import run

result = run.export_table_to_okf(
    project_id="l400-agentic-da-xxxxxxxxxx",
    dataset_id="l400_agentic_da",
    table_id="dim_business_events",
    tables_dir="okf/tables"
)
print(result)
```

## Output Location

- **Table OKF:** `{tables_dir}/{table_id_lower}.md`

All files are completely compliant with OKF spec 0.1 and exclude the `# Common query patterns` section.
