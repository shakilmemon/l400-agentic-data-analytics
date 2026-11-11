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

def get_bq_dataset(project_id: str, dataset_id: str) -> dict:
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}"
    return rest_api_helper(url, "GET")

def list_bq_tables(project_id: str, dataset_id: str) -> dict:
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables"
    return rest_api_helper(url, "GET")

def get_bq_table(project_id: str, dataset_id: str, table_id: str) -> dict:
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}?view=BASIC"
    return rest_api_helper(url, "GET")

def generate_indexes(okf_dir):
    """
    Generate index.md files for root, datasets, and tables.
    """
    datasets_dir = os.path.join(okf_dir, "datasets")
    tables_dir = os.path.join(okf_dir, "tables")
    references_dir = os.path.join(okf_dir, "references")
    glossary_dir = os.path.join(references_dir, "glossary")

    # Root index
    root_index = """---
okf_version: "0.1"
---

# Premium Outdoor Gear - Legacy ERP OKF Bundle

This bundle contains the Open Knowledge Format (OKF) metadata for the Premium Outdoor Gear legacy ERP database `l400_agentic_da`.

## Subdirectories

* [tables](tables/index.md) - The physical BigQuery tables containing ERP transaction facts and dimensions.
* [references](references/index.md) - Reference documents, business glossary terms, and metrics.
* [datasets](datasets/index.md) - Datasets defining the database schemas.
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

def export_dataset_to_okf(project_id: str, dataset_id: str, okf_root_dir: str = "okf") -> dict:
    """
    Synchronously fetches dataset and table details from the BigQuery REST API,
    and exports them as OKF dataset and table markdown files.
    """
    messages = []
    datasets_dir = os.path.join(okf_root_dir, "datasets")
    tables_dir = os.path.join(okf_root_dir, "tables")

    os.makedirs(datasets_dir, exist_ok=True)
    os.makedirs(tables_dir, exist_ok=True)

    try:
        # 1. Fetch Dataset Details
        messages.append(f"Fetching dataset details for '{dataset_id}' in project '{project_id}'...")
        dataset_meta = get_bq_dataset(project_id, dataset_id)
        
        friendly_name = dataset_meta.get("friendlyName", dataset_id)
        dataset_desc = dataset_meta.get("description", f"BigQuery Dataset {dataset_id}")
        location = dataset_meta.get("location", "US")

        # 2. Fetch Tables List
        messages.append(f"Fetching tables list for dataset '{dataset_id}'...")
        tables_response = list_bq_tables(project_id, dataset_id)
        bq_tables = tables_response.get("tables", [])
        messages.append(f"Found {len(bq_tables)} tables in BigQuery.")

        table_entities = []

        # 3. For each table, fetch details and write OKF Table file
        for table_summary in bq_tables:
            table_ref = table_summary.get("tableReference", {})
            table_id = table_ref.get("tableId", "")
            table_id_lower = table_id #.lower()
            
            messages.append(f"Fetching details for table '{table_id}'...")
            table_details = get_bq_table(project_id, dataset_id, table_id)
            
            table_desc = table_details.get("description", f"Physical table {table_id}")
            schema = table_details.get("schema", {})
            fields = schema.get("fields", [])

            # Register for dataset entity table
            table_entities.append((f"tables/{table_id_lower}", table_desc))

            # Generate OKF Table Markdown file
            table_frontmatter = {
                "type": "BigQuery Table",
                "resource": f"https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}",
                "rest_api": f"https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}",
                "title": table_id,
                "description": table_desc,
                "tags": [table_id_lower, "erp", dataset_id],
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            }

            schema_lines = ["# Schema", ""]
            schema_lines.append("| Field Name | Description |")
            schema_lines.append("| :--- | :--- |")
            for field in fields:
                field_name = field.get("name", "")
                field_desc = field.get("description", "")
                schema_lines.append(f"| `{field_name}` | {field_desc} |")
            
            schema_section = "\n".join(schema_lines)

            table_citations = f"""# Citations

[1] BigQuery Table Resource: `https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}`
[2] Premium Outdoor Gear - Legacy ERP Database Catalog"""

            table_yaml = dict_to_yaml_str(table_frontmatter)
            table_body = f"""---
{table_yaml}---

The `{table_id}` table is a key component of the Premium Outdoor Gear legacy ERP database. It holds {table_desc.lower()}

{schema_section}

{table_citations}
"""
            table_file_path = os.path.join(tables_dir, f"{table_id_lower}.md")
            with open(table_file_path, "w", encoding="utf-8") as f:
                f.write(table_body)

        # 4. Generate OKF Dataset Markdown file
        dataset_frontmatter = {
            "type": "BigQuery Dataset",
            "resource": f"https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/{dataset_id}",
            "rest_api": f"https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/{dataset_id}",
            "title": friendly_name,
            "description": dataset_desc,
            "tags": [dataset_id, "erp", project_id],
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        entity_lines = ["# Schema", ""]
        entity_lines.append("| Entity | Description |")
        entity_lines.append("| :--- | :--- |")
        for entity_path, entity_desc in table_entities:
            entity_lines.append(f"| `[{entity_path}]({entity_path}.md)` | {entity_desc} |")
        
        entity_section = "\n".join(entity_lines)

        dataset_citations = f"""# Citations

[1] BigQuery Resource: https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/{dataset_id}
[2] Premium Outdoor Gear - Database Catalog Documentation"""

        dataset_yaml = dict_to_yaml_str(dataset_frontmatter)
        dataset_body = f"""---
{dataset_yaml}---

This dataset, `{dataset_id}`, resides in the `{location}` region. {dataset_desc}

{entity_section}

{dataset_citations}
"""
        dataset_file_path = os.path.join(datasets_dir, f"{dataset_id}.md")
        with open(dataset_file_path, "w", encoding="utf-8") as f:
            f.write(dataset_body)

        # 5. Regenerate Index files
        messages.append("Regenerating progressive-disclosure index files...")
        generate_indexes(okf_root_dir)

        messages.append("OKF files export successfully completed!")
        return {
            "status": "success",
            "tool_name": "export_dataset_to_okf",
            "messages": messages,
            "results": {
                "dataset_path": dataset_file_path,
                "tables_count": len(bq_tables)
            }
        }

    except Exception as e:
        messages.append(f"Failed to export dataset to OKF: {e}")
        return {
            "status": "failed",
            "tool_name": "export_dataset_to_okf",
            "messages": messages,
            "results": None
        }
