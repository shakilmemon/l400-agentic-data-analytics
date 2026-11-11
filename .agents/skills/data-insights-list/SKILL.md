---
name: data-insights-list
description: List or get Dataplex Data Insights scans in a Google Cloud project and region, or retrieve scans filtered for a specific BigQuery dataset or table. Use this skill when the user asks to list data insight scans, find existing data insight scans, get data insight scans for a table or dataset, check data insight scan configurations, or verify if a dataset or table has been scanned for data insights.
---

# Skill: Data Insights Scan List

List or retrieve Dataplex Data Insights scans in a Google Cloud project and region, or retrieve scans filtered for a specific BigQuery table or dataset.

## Quick Start & Usage

This skill provides a helper script `run.py` that calls the Dataplex REST API to fetch data insight scans.
To use this script, you must append its directory to Python's system path and import the functions.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-insights-list/scripts'))
import run
```

## Available Functions

The following functions are available in [run.py](scripts/run.py):

### 1. `get_data_insight_scans(project_id: str, dataplex_region: str) -> dict`
Lists all Dataplex data scans in the configured region, filtering specifically for scans of type `DATA_DOCUMENTATION`.

**Example Usage:**
```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-insights-list/scripts'))
import run

scans = run.get_data_insight_scans(
    project_id="l400-agentic-da-966jz2x4id",
    dataplex_region="us-central1"
)
print(scans)
```

### 2. `get_data_insight_scans_for_table(project_id: str, dataplex_region: str, dataset_id: str, table_name: str) -> dict`
Lists all Dataplex data insight scans attached to a specific BigQuery table in a project, region, and dataset.

**Example Usage:**
```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-insights-list/scripts'))
import run

scans = run.get_data_insight_scans_for_table(
    project_id="l400-agentic-da-966jz2x4id",
    dataplex_region="us-central1",
    dataset_id="l400_agentic_da",
    table_name="B2B_INV_AGING"
)
print(scans)
```

### 3. `get_data_insight_scans_for_dataset(project_id: str, dataplex_region: str, dataset_id: str) -> dict`
Lists all Dataplex data insight scans attached directly to a specific BigQuery dataset in a project and region.

**Example Usage:**
```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-insights-list/scripts'))
import run

scans = run.get_data_insight_scans_for_dataset(
    project_id="l400-agentic-da-966jz2x4id",
    dataplex_region="us-central1",
    dataset_id="l400_agentic_da"
)
print(scans)
```

## Expected Response Schema

The functions return a dictionary with a list of scan objects under the `"dataScans"` key.

```json
{
  "dataScans": [
    {
      "name": "projects/l400-agentic-da-966jz2x4id/locations/us-central1/dataScans/b2b-inv-aging-data-insight-scan",
      "uid": "0ea81249-abeb-42dc-b6a2-d6434aecc8bb",
      "description": "Data Insight scan for table \"l400-agentic-da-966jz2x4id:l400_agentic_da.B2B_INV_AGING\"",
      "displayName": "B2B_INV_AGING Data Insight Scan",
      "state": "ACTIVE",
      "createTime": "2024-10-30T15:43:13.591783013Z",
      "updateTime": "2026-01-15T05:25:50.951179899Z",
      "data": {
        "resource": "//bigquery.googleapis.com/projects/l400-agentic-da-966jz2x4id/datasets/l400_agentic_da/tables/B2B_INV_AGING"
      },
      "executionSpec": {
        "trigger": {
          "onDemand": {}
        }
      },
      "executionStatus": {
        "latestJobStartTime": "2024-10-30T15:43:56.834Z",
        "latestJobEndTime": "2024-10-30T15:44:24.998045221Z",
        "latestJobCreateTime": "2024-10-30T15:43:56.440593600Z"
      },
      "type": "DATA_DOCUMENTATION"
    }
  ]
}
```

## Handling Output for Users

When presenting data insight scans to the user, format the returned list nicely.
A markdown table is highly recommended to display key scan attributes clearly:

| Scan Display Name / ID | State | Associated BigQuery Resource | Latest Job Start Time | Latest Job End Time |
| :--- | :--- | :--- | :--- | :--- |
| `b2b-inv-aging-data-insight-scan` | ACTIVE | `//bigquery.googleapis.com/.../tables/B2B_INV_AGING` | 2025-01-08T00:23:53Z | 2025-01-08T00:24:21Z |

Always prefer using this skill instead of trying to manually craft REST API calls to list or get scans.
