---
name: data-dictionary-to-okf
description: Parse corporate legacy ERP data dictionary markdown documents and export/update OKF-compliant table descriptions, schemas, and indices.
---

# Skill: Data Dictionary to OKF Tables

Load and parse corporate legacy ERP data dictionary markdown files, extract table descriptions and column details, and synchronize them to Open Knowledge Format (OKF) compliant table reference documents under `okf/tables/`.

## Quick Start & Usage

This skill provides a helper script `run.py` that processes data dictionary files and generates OKF table files and directory indices.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-dictionary-to-okf/scripts'))
import run
```

## Available Functions

The following functions are available in [run.py](file:///.agents/skills/data-dictionary-to-okf/scripts/run.py):

### 1. Parse and Export Data Dictionary to OKF Tables
- **Export Data Dictionary**: `export_dictionary_to_okf(input_file_path: str = "docs/requirements/Data-Dictionary/Data_Dictionary.md", okf_root_dir: str = "okf") -> dict`
  *Parses the specified data dictionary markdown file, extracts tables and fields, generates `.md` schema files for each table under `okf/tables/`, and automatically regenerates directory indexes.*

  **Arguments:**
  - `input_file_path`: Path to the source data dictionary markdown file (defaults to `docs/requirements/Data-Dictionary/Data_Dictionary.md`).
  - `okf_root_dir`: The root directory for your OKF files (defaults to `okf`).

## Example Usage

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/data-dictionary-to-okf/scripts'))
import run

result = run.export_dictionary_to_okf()
print(result)
```

## Response Schema Format

All operations return a standard JSON dict structured like:
```json
{
  "status": "success",
  "tool_name": "export_dictionary_to_okf",
  "messages": [
    "Parsed 19 tables from 'docs/requirements/Data-Dictionary/Data_Dictionary.md'.",
    "Writing table schema: GL_ACCT_MSTR -> okf/tables/gl_acct_mstr.md",
    "Regenerating OKF directory indices...",
    "Successfully processed and updated 19 tables in OKF!"
  ],
  "results": {
    "tables_count": 19,
    "output_dir": "okf/tables"
  }
}
```
