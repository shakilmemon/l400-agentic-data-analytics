---
name: term-mappings-to-okf
description: Parse corporate Dataplex / Knowledge Engine Business Glossary term mapping files and update OKF table reference schemas and frontmatter with live hyperlinks.
---

# Skill: Term Mappings to OKF Tables

Load and parse corporate Dataplex Glossary mapping files (e.g. `Terms_by_Table_and_Column.md`), extract table-level and column-level business terms, and update OKF table reference documents under `okf/tables/` with terms frontmatter and live hyperlink mappings.

## Quick Start & Usage

This skill provides a helper script `run.py` that processes glossary mapping files and updates OKF table reference markdown schemas.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/term-mappings-to-okf/scripts'))
import run
```

## Available Functions

The following functions are available in [run.py](file:///.agents/skills/term-mappings-to-okf/scripts/run.py):

### 1. Parse Mappings and Update OKF Tables
- **Update Mappings**: `update_term_mappings_in_okf(mapping_file: str = "docs/requirements/Glossary/Terms_by_Table_and_Column.md", okf_root_dir: str = "okf") -> dict`
  *Parses the specified glossary mapping markdown file, resolves links against your local business glossary references, and enriches OKF table files in `okf/tables/` with frontmatter term lists and schema-embedded hyperlinks.*

  **Arguments:**
  - `mapping_file`: Path to the source glossary mapping markdown file (defaults to `docs/requirements/Glossary/Terms_by_Table_and_Column.md`).
  - `okf_root_dir`: The root directory for your OKF files (defaults to `okf`).

## Example Usage

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/term-mappings-to-okf/scripts'))
import run

result = run.update_term_mappings_in_okf()
print(result)
```

## Response Schema Format

All operations return a standard JSON dict structured like:
```json
{
  "status": "success",
  "tool_name": "update_term_mappings_in_okf",
  "messages": [
    "Discovered 42 glossary reference definitions in 'okf/references/glossary'.",
    "Parsed 15 tables with glossary mappings from 'docs/requirements/Glossary/Terms_by_Table_and_Column.md'.",
    "Enriching OKF table file: CUST_MSTR_D2C -> okf/tables/cust_mstr_d2c.md",
    "Regenerating OKF directory indices...",
    "Successfully updated OKF tables with term mappings!"
  ],
  "results": {
    "tables_enriched_count": 15,
    "output_dir": "okf/tables"
  }
}
```
