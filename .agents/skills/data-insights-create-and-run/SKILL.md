---
name: data-insights-create-and-run
description: Create a new Dataplex Data Insights scan, run it, monitor its status until completion, and link its results to the target BigQuery table or dataset via publishing labels. Use this skill when the user asks to create and run a new data insight scan, run an insights scan on a table or dataset, run an insights scan workflow, or link a new insights scan to BigQuery.
---

# Skill: Data Insights Scan Create and Run

Create a new Dataplex Data Insights scan, run its job, wait synchronously until it completes successfully, and link its results to a BigQuery table or dataset so that they appear in the BigQuery user interface.

## Quick Start & Usage

This skill provides a helper script `run.py` that handles the end-to-end orchestration synchronously.
To use this script, you must append its directory to Python's system path and import the functions.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-insights-create-and-run/scripts'))
import run
```

## Available Functions

The following functions are available in [run.py](scripts/run.py):

### 1. `create_and_run_data_insight_scan_workflow(...) -> dict`
Performs the full end-to-end synchronous creation, execution, and BigQuery linking workflow.

**Signature:**
```python
def create_and_run_data_insight_scan_workflow(
    project_id: str,
    dataplex_region: str,
    data_insight_scan_name: str,
    data_insight_display_name: str,
    bigquery_dataset_name: str,
    bigquery_table_name: str = None  # Optional. Omit to run on the dataset resource path
) -> dict
```

**Example Usage (Dataset Level):**
```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-insights-create-and-run/scripts'))
import run

result = run.create_and_run_data_insight_scan_workflow(
    project_id="l400-agentic-da-966jz2x4id",
    dataplex_region="us-central1",
    data_insight_scan_name="my-dataset-data-insight-scan",
    data_insight_display_name="My Dataset Data Insight Scan",
    bigquery_dataset_name="l400_agentic_da"
)
print(result)
```

**Example Usage (Table Level):**
```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-insights-create-and-run/scripts'))
import run

result = run.create_and_run_data_insight_scan_workflow(
    project_id="l400-agentic-da-966jz2x4id",
    dataplex_region="us-central1",
    data_insight_scan_name="my-table-data-insight-scan",
    data_insight_display_name="My Table Data Insight Scan",
    bigquery_dataset_name="l400_agentic_da",
    bigquery_table_name="my_table"
)
print(result)
```

### 2. Fine-Grained Low-Level Functions
If you need to perform actions individually, you can use these individual functions:

- `exists_data_insight_scan(project_id, dataplex_region, data_insight_scan_name) -> bool`
- `create_data_insight_scan(project_id, dataplex_region, data_insight_scan_name, data_insight_display_name, bigquery_dataset_name, bigquery_table_name=None) -> dict`
- `start_data_insight_scan(project_id, dataplex_region, data_insight_scan_name) -> dict`
- `get_data_insight_scan_state(data_insight_scan_job_name) -> dict`
- `update_bigquery_resource_dataplex_labels(project_id, dataplex_region, dataplex_scan_name, bigquery_dataset_name, bigquery_table_name=None) -> dict`

## Expected Workflow Response Schema

Calling the master workflow function returns a unified JSON dictionary:

```json
{
  "status": "success",
  "messages": [
    "Step 1/5: Checking/creating scan definition 'my-table-data-insight-scan'...",
    "Successfully checked/created data insight scan definition.",
    "Step 2/5: Polling to verify scan registration...",
    "Data insight scan 'my-table-data-insight-scan' is registered.",
    "Step 3/5: Starting the data insight scan job...",
    "Started job: 'projects/248933586318/locations/us-central1/dataScans/my-table-data-insight-scan/jobs/7c30e082...'",
    "Step 4/5: Monitoring job execution...",
    "Job state: RUNNING (attempt 1/50)",
    "Job state: SUCCEEDED (attempt 2/50)",
    "Step 5/5: Linking data insight scan to BigQuery labels...",
    "Successfully linked data insight scan to BigQuery labels."
  ],
  "results": {
    "data_insight_scan_name": "my-table-data-insight-scan",
    "data_insight_display_name": "My Table Data Insight Scan",
    "bigquery_dataset_name": "l400_agentic_da",
    "bigquery_table_name": "my_table",
    "data_insight_scan_job_name": "projects/248933586318/locations/us-central1/dataScans/my-table-data-insight-scan/jobs/7c30e082-...",
    "data_insight_scan_job_state": "SUCCEEDED"
  }
}
```

Always prefer using this skill instead of trying to manually craft REST API calls to create and run scans.
