---
name: okf-to-glossary
description: Load reference terms from OKF markdown files and synchronize them to Dataplex (Knowledge Engine) Business Glossaries.
---

# Skill: OKF to Dataplex Glossary Synchronisation

Load local Open Knowledge Format (OKF) glossary reference markdown files, parse their YAML frontmatter and definitions, and automatically synchronize them to Google Cloud Dataplex (Knowledge Engine) Business Glossaries. Handles category creation, term nesting, and bulk synchronization.

## Quick Start & Usage

This skill provides a helper script `run.py` that connects to the Dataplex REST API, auto-provisions categories, and uploads/updates terms.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/okf-to-glossary/scripts'))
import run
```

## Available Functions

The following functions are available in [run.py](file:///.agents/skills/okf-to-glossary/scripts/run.py):

### 1. Synchronise OKF to Dataplex
- **Sync OKF to Dataplex**: `sync_okf_to_dataplex(okf_references_dir: str = "okf/references/glossary", glossary_id: str = "premium_outdoor_gear", project_id: str = None, dataplex_region: str = "us") -> dict`
  *Reads all OKF markdown files in `okf_references_dir`, creates the target Dataplex business glossary if missing, provisions categories, and creates/updates terms accordingly.*

  **Arguments:**
  - `okf_references_dir`: Directory path containing the OKF markdown reference files (defaults to `okf/references/glossary`).
  - `glossary_id`: Target Dataplex Glossary ID (defaults to `premium_outdoor_gear`).
  - `project_id`: GCP Project ID. Automatically loaded from `agent-config.json` if omitted.
  - `dataplex_region`: Dataplex resource region (defaults to `us`).

  *Upon successful synchronization, updates each term and synonym file's YAML frontmatter with `resource` and `rest_api` endpoints.*

## Example Usage

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/okf-to-glossary/scripts'))
import run

result = run.sync_okf_to_dataplex(
    okf_references_dir="okf/references/glossary",
    glossary_id="premium_outdoor_gear"
)
print(result)
```

## Response Schema Format

All operations return a standard JSON dict structured like:
```json
{
  "status": "success",
  "tool_name": "sync_okf_to_dataplex",
  "messages": [
    "Starting Dataplex sync to glossary 'premium_outdoor_gear'...",
    "Ensuring glossary 'premium_outdoor_gear' exists...",
    "Ensuring 5 categories exist in Dataplex...",
    "Dataplex sync completed: 41/41 terms successfully synchronised."
  ],
  "results": {
    "glossary_id": "premium_outdoor_gear",
    "terms_count": 41,
    "categories_count": 5
  }
}
```
