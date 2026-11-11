---
name: unstructured-data-to-okf
description: Parse unstructured business requirements for qualitative analytics and generate standard OKF table schemas and CA business context guides.
---

# Skill: Unstructured Data to OKF

This skill parses unstructured business requirements documents (like `business_requirements.md` under `docs/requirements/Unstructured-Data/`) and generates/updates:
1. The official OKF Table Reference for BigQuery: `okf/tables/dim_business_events.md` (which includes both business columns and the 4 system columns).
2. The CA Business Context Training Document: `docs/requirements/Unstructured-Data/02-business-context.md` (which lists only the core business columns, omitting the 4 technical system fields, and incorporates the Golden Query SQL and trigger prompts).

## Quick Start & Usage

This skill provides a helper script `run.py` that handles markdown-to-markdown conversion, custom pattern mapping, Golden Query compilation, and automatic file generation.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/unstructured-data-to-okf/scripts'))
import run
```

## Available Functions

The following core functions are available in [run.py](file:///.agents/skills/unstructured-data-to-okf/scripts/run.py):

### 1. Compile Unstructured Requirements to OKF and CA
- **Function**: `compile_requirements_to_okf(req_file_path: str = "docs/requirements/Unstructured-Data/business_requirements.md", okf_root_dir: str = "okf") -> dict`
- **Description**: Parses the requirements file, compiles the SQL Golden Query according to specified financial and date range logic, formats the `dim_business_events` table (adding GCS system fields), and writes both output files perfectly.

## Example Usage

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/unstructured-data-to-okf/scripts'))
import run

# Run translation of unstructured requirements to OKF and CA
result = run.compile_requirements_to_okf()
print(result)
```

## Response Schema Format

```json
{
  "status": "success",
  "tool_name": "compile_requirements_to_okf",
  "messages": [
    "Successfully read business requirements from 'docs/requirements/Unstructured-Data/business_requirements.md'.",
    "Compiled Golden Query SQL successfully.",
    "Generated OKF table reference 'okf/tables/dim_business_events.md'.",
    "Generated CA business context 'docs/requirements/Unstructured-Data/02-business-context.md'.",
    "Process complete!"
  ],
  "results": {
    "okf_table_created": true,
    "ca_context_created": true
  }
}
```
