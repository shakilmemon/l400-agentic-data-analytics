---
name: pdf-to-markdown
description: Convert PDF documents directly into clean standard GitHub-flavored Markdown using Gemini REST API on Vertex AI.
---

# Skill: PDF to Markdown

This skill takes any local PDF file path, base64 encodes it, and uses Vertex AI with Gemini (with an automatic fallback from `gemini-3.8-flash` to `gemini-3.1-pro-preview`) to translate the PDF content directly into clean, structured GitHub-flavored Markdown. It saves the resulting markdown file in the same directory as the original PDF.

## Quick Start & Usage

This skill provides a helper script `run.py` that handles file base64 encoding, Vertex AI authorization, REST request dispatching, and output file writing.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/pdf-to-markdown/scripts'))
import run
```

## Available Functions

The following core function is available in [run.py](file:///.agents/skills/pdf-to-markdown/scripts/run.py):

### 1. Convert PDF to Markdown
- **Function**: `convert_pdf_to_md(pdf_path: str, location: str = "us-central1") -> dict`
- **Description**: Convers any specified PDF file into standard Markdown and saves it under the same folder.
- **Parameters**:
  - `pdf_path` (str): Absolute or relative path to the PDF file.
  - `location` (str, optional): Vertex AI region. Defaults to `"us-central1"`.

## Example Usage

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/pdf-to-markdown/scripts'))
import run

# Run conversion on a specific PDF
result = run.convert_pdf_to_md("docs/requirements/Unstructured-Data/adam.pdf")
print(result)
```

## Response Schema Format

```json
{
  "status": "success",
  "tool_name": "convert_pdf_to_md",
  "messages": [
    "Starting conversion of PDF: /Users/paternostro/l400-agentic-da/docs/requirements/Unstructured-Data/adam.pdf",
    "Trying to convert PDF using model 'gemini-3.8-flash'...",
    "Success! Content extracted using model 'gemini-3.8-flash'.",
    "Saved markdown successfully to: /Users/paternostro/l400-agentic-da/docs/requirements/Unstructured-Data/adam.md"
  ],
  "results": {
    "pdf_path": "/Users/paternostro/l400-agentic-da/docs/requirements/Unstructured-Data/adam.pdf",
    "markdown_path": "/Users/paternostro/l400-agentic-da/docs/requirements/Unstructured-Data/adam.md",
    "model_used": "gemini-3.8-flash"
  }
}
```
