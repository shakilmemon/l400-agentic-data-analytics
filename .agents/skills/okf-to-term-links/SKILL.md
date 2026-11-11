---
name: okf-to-term-links
description: Read local OKF table references and link their table-level and column-level business terms to Dataplex / Knowledge Engine. Use this skill when you want to synchronize term associations defined in local OKF files with live GCP metadata.
---

# Skill: OKF to Term Links (Dataplex)

This skill reads OKF table markdown files under `okf/tables/`, extracts any table-level terms from the frontmatter and column-level terms from the schema tables, and synchronizes them directly as entry links inside Google Cloud Dataplex (Knowledge Engine).

## Quick Start & Usage

This skill provides a helper script `run.py` that parses your local OKF tables directory and executes synchronous REST API calls to Dataplex to create and verify entry links.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/okf-to-term-links/scripts'))
import run
```

## Available Functions

The following core functions are available in [run.py](file:///.agents/skills/okf-to-term-links/scripts/run.py):

### 1. Synchronize OKF Terms to Dataplex Entry Links
- **Function**: `sync_okf_to_term_links(okf_tables_dir: str = "okf/tables", project_id: str = None) -> dict`
- **Description**: Iterates through all OKF table reference markdown files inside `okf/tables/`, parses their table-level terms and column-level terms, and creates corresponding entry links inside Dataplex Knowledge Catalog. Automatically reads the `resource` field from frontmatter to deterministically resolve Dataplex entry paths, with fallback to Knowledge Catalog search if absent.

### 2. Link Term to Table or Column
- **Function**: `link_term_to_table_or_column(project_id: str = None, dataset_id: str = None, table_id: str = None, term_name_or_id: str = None, column_name: str = None, auto_create_term: bool = True, resource: str = None) -> dict`
- **Description**: Connects a business glossary term to a BigQuery table or a specific column within that table. Supports passing a `resource` URI for fast deterministic entry path resolution.

## Example Usage

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/okf-to-term-links/scripts'))
import run

# Run synchronization of all OKF terms to Dataplex
result = run.sync_okf_to_term_links()
print(result)
```

## Response Schema Format

All operations return a standard JSON dict structured like:

```json
{
  "status": "success",
  "tool_name": "sync_okf_to_term_links",
  "messages": [
    "Successfully discovered active glossary: 'l400-agentic-da' in region 'us'",
    "Processing OKF table 'cust_mstr_d2c.md'...",
    "Found table-level terms: ['D2C (Direct-to-Consumer)', 'Certified Field Tester']",
    "Found column-level terms: {'CUST_NUM_ID': ['CLV / LTV (Customer Lifetime Value)'], 'ACQ_DT': ['CAC (Customer Acquisition Cost)']}",
    "Successfully linked table-level terms.",
    "Successfully linked column-level terms."
  ],
  "results": {
    "tables_processed_count": 15,
    "entry_links_created_count": 18
  }
}
```
