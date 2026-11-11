---
name: bigquery-dataset-to-okf
description: Export BigQuery dataset and tables metadata directly to Open Knowledge Format (OKF) files.
---

# Skill: BigQuery Dataset to OKF Export

Retrieve dataset details and a list of physical tables via the BigQuery REST API, then output the dataset and table metadata into clean, Open Knowledge Format (OKF) compliant markdown files.

## Quick Start & Usage

This skill provides a helper script `run.py` that makes synchronous REST API calls to BigQuery, extracts the dataset and table schemas/metadata, and writes them into your OKF directories.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/bigquery-dataset-to-okf/scripts'))
import run
```

## Available Functions

The following functions are available in [run.py](file:///.agents/skills/bigquery-dataset-to-okf/scripts/run.py):

### 1. Export Dataset and Tables to OKF
- **Export to OKF**: `export_dataset_to_okf(project_id: str, dataset_id: str, okf_root_dir: str = "okf") -> dict`
  *Fetches dataset details and all table metadata from BigQuery, then generates the dataset and table OKF files.*

  **Arguments:**
  - `project_id`: GCP Project ID.
  - `dataset_id`: BigQuery Dataset ID.
  - `okf_root_dir`: The destination root path for OKF (defaults to `okf`).

## Example Usage

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/bigquery-dataset-to-okf/scripts'))
import run

project = "l400-agentic-da-966jz2x4id"
dataset = "l400_agentic_da"

result = run.export_dataset_to_okf(
    project_id=project,
    dataset_id=dataset
)
print(result)
```

## Output Location

- **Dataset OKF:** `okf/datasets/{dataset_id}.md`
- **Table OKFs:** `okf/tables/{table_id_lower}.md`
- **Indices:** `okf/index.md`, `okf/datasets/index.md`, `okf/tables/index.md`

All files are completely compliant with OKF spec 0.1 and exclude the `# Common query patterns` section.
