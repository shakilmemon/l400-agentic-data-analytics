---
name: glossary-to-okf
description: Parse corporate operations/finance glossary markdown files and export them to OKF-compliant reference glossary documents with category tags, synonyms, and definitions.
---

# Skill: Glossary to OKF Export

Parse structured glossary files (such as `Outdoor_Gear_Industry_Glossary.md`) and translate them into standard Open Knowledge Format (OKF) glossary reference files with structured frontmatter (containing title, category, description, and synonyms) and clear, searchable markdown bodies.

## Quick Start & Usage

This skill provides a helper script `run.py` that parses glossary lists, groups terms into business categories, identifies synonyms, and exports each term to `okf/references/glossary/<term_slug>.md`.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/glossary-to-okf/scripts'))
import run
```

## Available Functions

The following functions are available in [run.py](file:///.agents/skills/glossary-to-okf/scripts/run.py):

### 1. Export Glossary to OKF
- **Export to OKF**: `export_glossary_to_okf(input_file_path: str = "docs/requirements/Glossary/Outdoor_Gear_Industry_Glossary.md", okf_root_dir: str = "okf") -> dict`
  *Parses the corporate glossary markdown file, groups terms by category, extracts synonyms, generates individual OKF reference files, and regenerates index directories.*

  **Arguments:**
  - `input_file_path`: Path to the source glossary markdown file (defaults to `docs/requirements/Glossary/Outdoor_Gear_Industry_Glossary.md`).
  - `okf_root_dir`: The destination root path for OKF (defaults to `okf`).

## Example Usage

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/glossary-to-okf/scripts'))
import run

result = run.export_glossary_to_okf()
print(result)
```

## Output Location

- **Glossary OKFs:** `okf/references/glossary/{term_slug}.md`
- **Indices:** `okf/references/glossary/index.md`, `okf/references/index.md`, `okf/index.md`

All files are completely compliant with OKF spec 0.1 and feature category mappings and synonyms in their YAML frontmatter.
