---
name: data-profile-scan-list
description: List or get Dataplex Data Profile scans in a Google Cloud project and region, or retrieve scans filtered for a specific BigQuery table. Use this skill when the user asks to list data profile scans, find existing data profile scans, get data profile scans for a table, check data profile scan configurations, or verify if a table has been profiled.
---

# Skill: Data Profile Scan List

List or retrieve Dataplex Data Profile scans in a Google Cloud project and region, or retrieve scans filtered for a specific BigQuery table.

## Quick Start & Usage

This skill provides a helper script `run.py` that calls the Dataplex REST API to fetch data profile scans.
To use this script, you must append its directory to Python's system path and import the functions.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-profile-scan-list/scripts'))
import run
```

## Available Functions

The following functions are available in [run.py](scripts/run.py):

### 1. `get_data_profile_scans(project_id: str, dataplex_region: str) -> dict`
Lists all Dataplex data profile scans in the configured region, filtering specifically for scans of type `DATA_PROFILE`.

**Example Usage:**
```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-profile-scan-list/scripts'))
import run

scans = run.get_data_profile_scans(
    project_id="data-analytics-preview",
    dataplex_region="us-central1"
)
print(scans)
```

### 2. `get_data_profile_scans_for_table(project_id: str, dataplex_region: str, dataset_id: str, table_name: str) -> dict`
Lists all Dataplex data profile scans attached to a specific BigQuery table in a project, region, and dataset.

**Example Usage:**
```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-profile-scan-list/scripts'))
import run

scans = run.get_data_profile_scans_for_table(
    project_id="data-analytics-preview",
    dataplex_region="us-central1",
    dataset_id="chocolate_ai",
    table_name="customer_marketing_profile_loyalty"
)
print(scans)
```

## Expected Response Schema

Both functions return a dictionary with a list of scan objects under the `"dataScans"` key.

```json
{
  "dataScans": [
    {
      "name": "projects/data-analytics-preview/locations/us-central1/dataScans/ad1312d90-f8e5-4da5-a214-e8be2d2295c1",
      "uid": "0ea81249-abeb-42dc-b6a2-d6434aecc8bb",
      "description": "Profile scan for table \"data-analytics-preview:chocolate_ai.customer_marketing_profile_loyalty\" with default configuration",
      "displayName": "data-analytics-preview:chocolate_ai.customer_marketing_profile_loyalty-default-profile",
      "state": "ACTIVE",
      "createTime": "2024-10-30T15:43:13.591783013Z",
      "updateTime": "2026-01-15T05:25:50.951179899Z",
      "data": {
        "resource": "//bigquery.googleapis.com/projects/data-analytics-preview/datasets/chocolate_ai/tables/customer_marketing_profile_loyalty"
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
      "type": "DATA_PROFILE"
    }
  ]
}
```

## Handling Output for Users

When presenting data profile scans to the user, format the returned list nicely.
A markdown table is highly recommended to display key scan attributes clearly:

| Scan Display Name / ID | State | Associated BigQuery Table Resource | Latest Job Start Time | Latest Job End Time |
| :--- | :--- | :--- | :--- | :--- |
| `taxi-dataset-artifact-profile-scan` | ACTIVE | `//bigquery.googleapis.com/.../tables/artifact` | 2025-01-08T00:23:53Z | 2025-01-08T00:24:21Z |

Always prefer using this skill instead of trying to manually craft REST API calls to list or get scans.