---
name: okf-to-bigquery-metadata
description: Parse local OKF table markdown files and synchronize their table and column descriptions back to BigQuery schemas.
---

# Skill: OKF to BigQuery Schema Synchronisation

Load and parse local Open Knowledge Format (OKF) table markdown schemas, extract table-level descriptions and column/field descriptions, and synchronize them directly back to your live Google Cloud BigQuery database schemas.

## Quick Start & Usage

This skill provides a helper script `run.py` that makes synchronous REST API calls to BigQuery to synchronize metadata cleanly.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/okf-to-bigquery-metadata/scripts'))
import run
```

## Available Functions

The following functions are available in [run.py](file:///.agents/skills/okf-to-bigquery-metadata/scripts/run.py):

### 1. Synchronise OKF Tables to BigQuery
- **Sync OKF Tables to BigQuery**: `sync_okf_to_bigquery(tables_dir: str = "okf/tables", project_id: str = None, dataset_id: str = None) -> dict`
  *Reads all OKF markdown files inside `tables_dir`, parses their schemas, and uploads descriptions back to BigQuery.*

  **Arguments:**
  - `tables_dir`: Path to the local directory containing table OKF references (defaults to `okf/tables`).
  - `project_id`: GCP Project ID (auto-loaded from `agent-config.json` or YAML frontmatter if omitted).
  - `dataset_id`: BigQuery Dataset ID (auto-loaded from `agent-config.json` or YAML frontmatter if omitted).

  *Upon successful synchronization, updates each table file's YAML frontmatter with `resource` and `rest_api` endpoints.*

### 2. Synchronise OKF Datasets to BigQuery
- **Sync OKF Datasets to BigQuery**: `sync_okf_datasets_to_bigquery(datasets_dir: str = "okf/datasets", project_id: str = None, dataset_id: str = None) -> dict`
  *Reads all OKF markdown files inside `datasets_dir`, parses their dataset metadata, and uploads descriptions back to BigQuery.*

  **Arguments:**
  - `datasets_dir`: Path to the local directory containing dataset OKF references (defaults to `okf/datasets`).
  - `project_id`: GCP Project ID (auto-loaded from `agent-config.json` or YAML frontmatter if omitted).
  - `dataset_id`: BigQuery Dataset ID (auto-loaded from `agent-config.json` or YAML frontmatter if omitted).

  *Upon successful synchronization, updates each dataset file's YAML frontmatter with `resource` and `rest_api` endpoints.*

## Example Usage

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/okf-to-bigquery-metadata/scripts'))
import run

result = run.sync_okf_to_bigquery(
    tables_dir="okf/tables"
)
print(result)
```

## Response Schema Format

All operations return a standard JSON dict structured like:
```json
{
  "status": "success",
  "tool_name": "sync_okf_to_bigquery",
  "messages": [
    "Found 19 table schema files under 'okf/tables' to synchronise.",
    "Syncing metadata for table 'GL_ACCT_MSTR' to BigQuery...",
    "Successfully synchronised 'GL_ACCT_MSTR' schema metadata.",
    "BigQuery metadata sync completed: 19/19 tables synchronised successfully."
  ],
  "results": {
    "tables_count": 19,
    "total_tables": 19
  }
}
```
