---
name: gemini-to-okf
description: Pass a system/task prompt and multiple source documents to Gemini Pro on Vertex AI and output the generated OKF markdown in a specified directory. Supports automatic and interactive GCP project ID discovery and placeholder resolution (<<gcp_project_id>>).
---

# Skill: Gemini to OKF

This skill allows you to orchestrate custom prompt execution and document assembly using Gemini Pro (`gemini-3.1-pro-preview` or any other model) on Vertex AI. It takes a primary template/prompt file and joins it with the content of one or more documents as context, executes the consolidated request, and outputs the resulting Open Knowledge Format (OKF) document into a specified target directory.

## Quick Start & Usage

This skill provides a helper script `run.py` that handles workspace path resolution, document text extraction and formatting, Vertex AI REST API requests, and output file writing.

### Import Pattern

Always import the helper functions by dynamically adding the scripts directory to the path (relative to the workspace root):

```python
import sys
import os
sys.path.append(os.path.abspath('.agents/skills/gemini-to-okf/scripts'))
import run
```

## Available Functions

The following core function is available in [run.py](scripts/run.py):

### 1. Generate OKF Document with Gemini
- **Function**: `generate_okf_with_gemini(prompt_file_path: str, document_paths: list, output_dir: str, output_filename: str, model_name: str = "gemini-3.1-pro-preview", location: str = "global") -> dict`
- **Description**: Compiles a prompt file and a list of target context documents, sends the combined instructions to the selected Gemini model, and writes the output as a Markdown file.
- **Parameters**:
  - `prompt_file_path` (str): Path to the primary prompt markdown or text file.
  - `document_paths` (list of str): A list of paths to files whose contents should be appended as document context. Can also contain grouped dictionaries `{"header": "GROUP NAME", "paths": [...]}` or tuples `("GROUP NAME", [...])`.
  - `output_dir` (str): Target directory to save the output (e.g. `okf/conversation-analytics`).
  - `output_filename` (str): File name for the output (e.g. `agent_instructions.md`).
  - `model_name` (str, optional): Gemini model ID. Defaults to `"gemini-3.1-pro-preview"`.
  - `location` (str, optional): Vertex AI API endpoint region. Defaults to `"global"`.

## Project ID Discovery & Placeholder Resolution (`<<gcp_project_id>>`)

When preparing to run this skill or generating OKF documents where templates contain project placeholders like `<<gcp_project_id>>` (such as Conversational Analytics agent configs), the agent MUST follow these steps without modifying `run.py`:

### Step 1: Discover or Prompt for GCP Project ID
1. **Auto-Discovery (`agent-config.json`)**:
   - Check if `agent-config.json` exists in the workspace root.
   - If present, read and extract `"gcp-project-id"`.
2. **Interactive Prompting (Real-World / Fallback)**:
   - If `agent-config.json` does NOT exist or does not contain `gcp-project-id`, **the agent MUST prompt the user**:
     > *"Please provide your GCP Project ID, or specify a file path that contains it (e.g., `agent-config.json`, `.env`, or `config.json`)."*
   - If the user provides a project ID, use it directly.
   - If the user provides a file path, parse the file and extract the project ID (e.g., JSON key `gcp-project-id` / `project_id`, or environment variable `PROJECT_ID` / `GCP_PROJECT_ID`).

### Step 2: Post-Processing Generated Files for `<<gcp_project_id>>`
Because `run.py` passes the prompt directly to Gemini and writes the resulting output, template placeholders such as `<<gcp_project_id>>` may be reproduced verbatim in the generated output file.
Therefore, immediately after executing `run.generate_okf_with_gemini(...)`:
1. The agent MUST inspect the generated file at `output_dir/output_filename`.
2. Check if it contains `<<gcp_project_id>>` (or variants like `<<gcp-project-id>>` or `<<Insert Project Id here>>`).
3. Replace any occurrences of `<<gcp_project_id>>` with the resolved GCP Project ID.
4. Verify that the final OKF file contains the actual GCP Project ID under `datasource.project_id`.

## Example Usage

### Standard Workflow with Project ID Resolution:
```python
import sys
import os
import json

# 1. Resolve Project ID (agent-config.json or user-prompted)
project_id = None
if os.path.exists("agent-config.json"):
    with open("agent-config.json", "r") as f:
        config = json.load(f)
        project_id = config.get("gcp-project-id")
# If project_id is still None, the agent prompts the user before proceeding!

# 2. Run generation via run.py
sys.path.append(os.path.abspath('.agents/skills/gemini-to-okf/scripts'))
import run

result = run.generate_okf_with_gemini(
    prompt_file_path="docs/requirements/Conversational-Analytics-Best-Practices/ca-generate-system-prompt.md",
    document_paths=[
        "docs/requirements/Business-Requirements/questionnaire-completed.md",
        "docs/requirements/Conversational-Analytics-Best-Practices/ca-best-practices.md"
    ],
    output_dir="okf/conversation-analytics",
    output_filename="agent_system_prompt.md",
    model_name="gemini-3.1-pro-preview"
)
print(result)

# 3. Post-process output to replace <<gcp_project_id>> if present
output_file = os.path.join("okf/conversation-analytics", "agent_system_prompt.md")
if os.path.exists(output_file) and project_id:
    with open(output_file, "r") as f:
        content = f.read()
    if "<<gcp_project_id>>" in content:
        content = content.replace("<<gcp_project_id>>", project_id)
        with open(output_file, "w") as f:
            f.write(content)
```

## Response Schema Format

```json
{
  "status": "success",
  "tool_name": "generate_okf_with_gemini",
  "messages": [
    "Starting compilation of prompt 'docs/requirements/Conversational-Analytics-Best-Practices/ca-generate-system-prompt.md' and 2 documents...",
    "Appended document: questionnaire-completed.md",
    "Appended document: ca-best-practices.md",
    "Calling model 'gemini-3.1-pro-preview' in location 'global'...",
    "Success! Response received from Gemini.",
    "Saved generated OKF successfully to: okf/conversation-analytics/agent_system_prompt.md"
  ],
  "results": {
    "output_file_path": "okf/conversation-analytics/agent_system_prompt.md",
    "model_used": "gemini-3.1-pro-preview"
  }
}
```
