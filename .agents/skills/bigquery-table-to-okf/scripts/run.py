import os
import re
from datetime import datetime
import google.auth.transport.requests
import google.auth
import requests

def rest_api_helper(url: str, http_verb: str, request_body: dict = None, headers: dict = None) -> dict:
  """
  Calls the Google Cloud REST API passing in the current user's credentials.
  """
  try:
    creds, project = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    access_token = creds.token
  except Exception as e:
    raise RuntimeError(f"Authentication error: {e}")

  request_headers = {
    "Content-Type" : "application/json",
    "Authorization" : f"Bearer {access_token}"
  }

  if headers:
    request_headers.update(headers)

  try:
    response = None
    http_verb = http_verb.upper()
    if http_verb == "GET":
      response = requests.get(url, headers=request_headers, timeout=300.0)
    elif http_verb == "POST":
      response = requests.post(url, json=request_body, headers=request_headers, timeout=300.0)
    elif http_verb == "PUT":
      response = requests.put(url, json=request_body, headers=request_headers, timeout=300.0)
    elif http_verb == "PATCH":
      response = requests.patch(url, json=request_body, headers=request_headers, timeout=300.0)
    elif http_verb == "DELETE":
      response = requests.delete(url, headers=request_headers, timeout=300.0)
    else:
      raise ValueError(f"Unknown HTTP verb: {http_verb}")

    response.raise_for_status()
    return response.json()

  except requests.exceptions.HTTPError as e:
    error_message = f"Error rest_api_helper -> HTTP Status: {e.response.status_code if e.response is not None else 'N/A'}, Text: {e.response.text if e.response is not None else 'N/A'}, Request URL: {e.request.url if e.request is not None else 'N/A'}"
    raise RuntimeError(error_message)
  except requests.exceptions.RequestException as e:
    error_message = f"Error rest_api_helper -> Request Error Type: {type(e).__name__}, Message: {str(e)}, Request URL: {e.request.url if hasattr(e, 'request') and e.request is not None else 'N/A'}"
    raise RuntimeError(error_message)
  except Exception as e:
    error_message = f"An unexpected error occurred in rest_api_helper: {e}"
    raise RuntimeError(error_message)

def dict_to_yaml_str(d: dict) -> str:
    """
    Format a flat dictionary to YAML string representation.
    """
    lines = []
    for k, v in d.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        elif v is None:
            lines.append(f"{k}: null")
        else:
            v_str = str(v)
            if ":" in v_str or "#" in v_str or "'" in v_str or '"' in v_str or "{" in v_str or "}" in v_str or "\n" in v_str:
                lines.append(f"{k}: {repr(v_str)}")
            else:
                lines.append(f"{k}: {v_str}")
    return "\n".join(lines) + "\n"

def get_bq_table(project_id: str, dataset_id: str, table_id: str) -> dict:
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}?view=BASIC"
    return rest_api_helper(url, "GET")

def generate_indexes(okf_dir):
    """
    Generate index.md files for root, datasets, and tables, discovering all subdirectories.
    """
    datasets_dir = os.path.join(okf_dir, "datasets")
    tables_dir = os.path.join(okf_dir, "tables")
    references_dir = os.path.join(okf_dir, "references")
    glossary_dir = os.path.join(references_dir, "glossary")

    # Discover all subdirectories with index.md for root index
    known_subdir_descs = {
        "conversational-analytics": "Production Conversational Analytics (CA) agent definitions mapped directly to the Google Cloud Data Agents schema.",
        "datasets": "Datasets defining the database schemas.",
        "references": "Reference documents, business glossary terms, and metrics.",
        "tables": "The physical BigQuery tables containing ERP transaction facts and dimensions."
    }

    subdirs = []
    for item in sorted(os.listdir(okf_dir)):
        subpath = os.path.join(okf_dir, item)
        if os.path.isdir(subpath) and os.path.exists(os.path.join(subpath, "index.md")):
            desc = known_subdir_descs.get(item, f"{item.replace('_', ' ').title()} definitions and documentation.")
            subdirs.append(f"* [{item}]({item}/index.md) - {desc}")

    root_subdirs_text = "\n".join(subdirs)
    root_index = f"""---
okf_version: "0.1"
---

# Premium Outdoor Gear - Legacy ERP OKF Bundle

This bundle contains the Open Knowledge Format (OKF) metadata for the Premium Outdoor Gear legacy ERP database `l400_agentic_da`.

## Subdirectories

{root_subdirs_text}
"""
    with open(os.path.join(okf_dir, "index.md"), "w", encoding="utf-8") as f:
        f.write(root_index)

    # Datasets index
    if os.path.exists(datasets_dir):
        datasets = [f[:-3] for f in os.listdir(datasets_dir) if f.endswith(".md") and f != "index.md"]
        datasets.sort()
        datasets_index_lines = ["# Datasets", "", "BigQuery datasets defined in this OKF bundle:", ""]
        for d in datasets:
            with open(os.path.join(datasets_dir, f"{d}.md"), "r") as f:
                content = f.read()
                desc_match = re.search(r'description:\s*(.*?)\n', content)
                desc = desc_match.group(1).strip() if desc_match else "No description available."
                if (desc.startswith("'") and desc.endswith("'")) or (desc.startswith('"') and desc.endswith('"')):
                    desc = desc[1:-1]
            datasets_index_lines.append(f"* [{d}]({d}.md) - {desc}")
        with open(os.path.join(datasets_dir, "index.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(datasets_index_lines) + "\n")

    # Tables index
    if os.path.exists(tables_dir):
        tables = [f[:-3] for f in os.listdir(tables_dir) if f.endswith(".md") and f != "index.md"]
        tables.sort()
        tables_index_lines = ["# Tables", "", "Physical BigQuery tables mapped from the legacy ERP database:", ""]
        for t in tables:
            with open(os.path.join(tables_dir, f"{t}.md"), "r") as f:
                content = f.read()
                desc_match = re.search(r'description:\s*(.*?)\n', content)
                desc = desc_match.group(1).strip() if desc_match else "No description available."
                if (desc.startswith("'") and desc.endswith("'")) or (desc.startswith('"') and desc.endswith('"')):
                    desc = desc[1:-1]
            tables_index_lines.append(f"* [{t.upper()}]({t}.md) - {desc}")
        with open(os.path.join(tables_dir, "index.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(tables_index_lines) + "\n")

    # References index
    if os.path.exists(references_dir):
        subdirs_list = []
        if os.path.exists(os.path.join(references_dir, "glossary")):
            subdirs_list.append("* [glossary](glossary/index.md) - Corporate business glossary terms and conceptual descriptions.")
        if os.path.exists(os.path.join(references_dir, "metrics")):
            subdirs_list.append("* [metrics](metrics/index.md) - Golden metrics and SQL query templates for Conversational Analytics.")
        
        subdirs_text = "\n".join(subdirs_list)
        ref_index = f"""# References

Reference directories containing business glossary terms, metrics definitions, and mapping tables.

## Subdirectories

{subdirs_text}
"""
        with open(os.path.join(references_dir, "index.md"), "w", encoding="utf-8") as f:
            f.write(ref_index)

    # Glossary index
    if os.path.exists(glossary_dir):
        terms = [f[:-3] for f in os.listdir(glossary_dir) if f.endswith(".md") and f != "index.md"]
        terms.sort()
        glossary_index_lines = ["# Glossary Terms", "", "Conceptual and business glossary terms mapped to ERP columns:", ""]
        for t in terms:
            with open(os.path.join(glossary_dir, f"{t}.md"), "r") as f:
                content = f.read()
                desc_match = re.search(r'description:\s*(.*?)\n', content)
                desc = desc_match.group(1).strip() if desc_match else "No description available."
                if (desc.startswith("'") and desc.endswith("'")) or (desc.startswith('"') and desc.endswith('"')):
                    desc = desc[1:-1]
                title_match = re.search(r'title:\s*(.*?)\n', content)
                title = title_match.group(1).strip() if title_match else t.replace("_", " ").title()
                if (title.startswith("'") and title.endswith("'")) or (title.startswith('"') and title.endswith('"')):
                    title = title[1:-1]
            glossary_index_lines.append(f"* [{title}]({t}.md) - {desc}")
        with open(os.path.join(glossary_dir, "index.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(glossary_index_lines) + "\n")

def export_table_to_okf(project_id: str, dataset_id: str, table_id: str, tables_dir: str) -> dict:
    """
    Synchronously fetches metadata for a single table from BigQuery via REST API
    and outputs it as an OKF table markdown file.
    """
    messages = []
    
    # Ensure tables_dir is absolute
    tables_dir = os.path.abspath(tables_dir)
    os.makedirs(tables_dir, exist_ok=True)

    table_id_lower = table_id #.lower()
    table_file_path = os.path.join(tables_dir, f"{table_id_lower}.md")
    
    try:
        messages.append(f"Fetching details for table '{table_id}' from dataset '{dataset_id}'...")
        table_details = get_bq_table(project_id, dataset_id, table_id)
        
        table_desc = table_details.get("description") or f"Physical table {table_id}"
        schema = table_details.get("schema", {})
        fields = schema.get("fields", [])

        # Parse existing markdown file if it exists to preserve terms and citations
        existing_terms = []
        existing_table_level_terms = ""
        existing_col_terms = {}
        existing_citations = []
        if os.path.exists(table_file_path):
            with open(table_file_path, "r", encoding="utf-8") as f:
                old_content = f.read()

            # Extract terms from frontmatter
            terms_match = re.search(r'terms:\n((?:\s+-\s+.*\n)+)', old_content)
            if terms_match:
                for line in terms_match.group(1).splitlines():
                    t = line.strip().lstrip("- ").strip()
                    if t:
                        existing_terms.append(t)

            # Extract Table-Level Business Terms section
            tbl_terms_match = re.search(r'(### Table-Level Business Terms\n(?:[^\n#]+\n*)+)', old_content)
            if tbl_terms_match:
                existing_table_level_terms = tbl_terms_match.group(1).strip() + "\n\n"

            # Extract schema column business terms
            for line in old_content.splitlines():
                if line.startswith("| `") and "|" in line:
                    parts = [p.strip() for p in line.strip().split("|")[1:-1]]
                    if len(parts) >= 3:
                        col_name = parts[0].strip("`")
                        col_term = parts[2]
                        if col_term and col_term != "-":
                            existing_col_terms[col_name] = col_term

            # Extract extra citations
            citations_match = re.search(r'# Citations\n+(.*)', old_content, re.DOTALL)
            if citations_match:
                existing_citations = [c.strip() for c in citations_match.group(1).strip().splitlines() if c.strip()]

        # Generate OKF Table Markdown file
        table_frontmatter = {
            "type": "BigQuery Table",
            "resource": f"https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}",
            "rest_api": f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}",
            "title": table_id,
            "description": table_desc,
            "tags": [table_id_lower, "erp", dataset_id],
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        if existing_terms:
            table_frontmatter["terms"] = existing_terms

        schema_lines = ["# Schema", ""]
        schema_lines.append("| Field Name | Description | Business Terms |")
        schema_lines.append("| :--- | :--- | :--- |")
        for field in fields:
            field_name = field.get("name", "")
            field_desc = field.get("description", "") or ""
            col_term = existing_col_terms.get(field_name, "-")
            schema_lines.append(f"| `{field_name}` | {field_desc} | {col_term} |")
        
        schema_section = "\n".join(schema_lines)

        if existing_citations:
            citations_text = "\n".join(existing_citations)
            table_citations = f"""# Citations\n\n{citations_text}"""
        else:
            table_citations = f"""# Citations

[1] BigQuery Table Resource: `https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}`
[2] Premium Outdoor Gear - Legacy ERP Database Catalog"""

        table_yaml = dict_to_yaml_str(table_frontmatter)
        
        desc_sentence = table_desc
        if not (desc_sentence.startswith("It ") or desc_sentence.startswith("The ")):
            desc_sentence = f"It holds {desc_sentence[0].lower() + desc_sentence[1:]}"

        table_body = f"""---
{table_yaml}---

The `{table_id}` table is a key component of the Premium Outdoor Gear legacy ERP database. {desc_sentence}

{existing_table_level_terms}# Schema

{schema_section[9:]}

{table_citations}
"""
        with open(table_file_path, "w", encoding="utf-8") as f:
            f.write(table_body)

        messages.append(f"Successfully generated table OKF reference at: '{table_file_path}'")

        # Regenerate Index files if tables_dir is part of a standard OKF structure
        okf_root_dir = os.path.dirname(tables_dir)
        if os.path.exists(os.path.join(okf_root_dir, "index.md")):
            messages.append("Regenerating progressive-disclosure index files...")
            generate_indexes(okf_root_dir)

        return {
            "status": "success",
            "tool_name": "export_table_to_okf",
            "messages": messages,
            "results": {
                "table_path": table_file_path
            }
        }

    except Exception as e:
        messages.append(f"Failed to export table to OKF: {e}")
        return {
            "status": "failed",
            "tool_name": "export_table_to_okf",
            "messages": messages,
            "results": None
        }
