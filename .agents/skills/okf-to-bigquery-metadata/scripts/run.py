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


def get_bigquery_table(project_id: str, dataset_id: str, table_id: str, rest_api: str = None) -> dict: 
    """
    Gets a single BigQuery table details (schema, description, etc.).
    """
    messages = []
    if rest_api:
        url = f"{rest_api}{'&' if '?' in rest_api else '?'}view=BASIC"
    else:
        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}?view=BASIC"

    try:
        json_result = rest_api_helper(url, "GET", None) 
        messages.append(f"Successfully retrieved details for BigQuery table '{table_id}' in dataset '{dataset_id}' from the API.")
        return {
            "status": "success",
            "tool_name": "get_bigquery_table",
            "messages": messages,
            "exists": True,
            "results": json_result
        }
    except RuntimeError as e: 
        error_message = str(e)
        if "HTTP Status: 404" in error_message:
            messages.append(f"BigQuery table '{table_id}' not found in dataset '{dataset_id}'.")
            return {
                "status": "success",
                "tool_name": "get_bigquery_table",
                "messages": messages,
                "exists": False,
                "results": None
            }
        else:
            messages.append(f"An API error occurred while getting table '{table_id}': {error_message}")
            return {
                "status": "failed",
                "tool_name": "get_bigquery_table",
                "messages": messages,
                "exists": False,
                "results": None
            }
    except Exception as e:
        messages.append(f"An unexpected system error occurred: {e}")
        return {
            "status": "failed",
            "tool_name": "get_bigquery_table",
            "messages": messages,
            "exists": False,
            "results": None
        }


def patch_bigquery_table(project_id: str, dataset_id: str, table_id: str, table_description: str = None, column_descriptions: dict = None, rest_api: str = None) -> dict: 
    """
    Patches a BigQuery table with a table description and individual column descriptions.
    """
    messages = []
    
    # 1. Fetch current table to get current schema
    existence_check = get_bigquery_table(project_id, dataset_id, table_id, rest_api=rest_api)
    messages.extend(existence_check.get("messages", []))
    
    if existence_check["status"] != "success":
        messages.append(f"Failed to fetch table '{table_id}' during patch operation.")
        return {
            "status": "failed",
            "tool_name": "patch_bigquery_table",
            "messages": messages,
            "results": None
        }
        
    if not existence_check.get("exists", False):
        messages.append(f"BigQuery table '{table_id}' does not exist, cannot patch metadata.")
        return {
            "status": "failed",
            "tool_name": "patch_bigquery_table",
            "messages": messages,
            "results": None
        }
        
    current_table = existence_check["results"]
    
    # Extract current schema
    schema = current_table.get("schema", {})
    fields = schema.get("fields", [])
    
    # If no fields found, error out (or warn)
    if not fields:
        messages.append(f"Warning: BigQuery table '{table_id}' schema has no fields or is not a physical table.")
        
    # Build updated fields list
    updated_fields = []
    column_descriptions = column_descriptions or {}
    
    # Convert keys of column_descriptions to lowercase/uniform for matching
    col_desc_lower = {k.lower(): v for k, v in column_descriptions.items()}
    
    has_changes = False
    if table_description is not None and table_description != current_table.get("description", ""):
        has_changes = True

    for field in fields:
        field_name = field.get("name", "")
        existing_desc = field.get("description", "")
        
        # Determine updated description
        field_name_lower = field_name.lower()
        if field_name_lower in col_desc_lower:
            new_desc = col_desc_lower[field_name_lower]
        else:
            new_desc = existing_desc
            
        if new_desc != existing_desc:
            has_changes = True
            
        # Clone field dict to avoid side effects
        updated_field = dict(field)
        if new_desc is not None:
            updated_field["description"] = new_desc
        elif "description" in updated_field:
            # Keep description if not explicitly set to a different value
            pass
            
        updated_fields.append(updated_field)
        
    if not has_changes:
        messages.append(f"BigQuery table '{table_id}' descriptions are already up to date. Skipping PATCH.")
        return {
            "status": "success",
            "tool_name": "patch_bigquery_table",
            "messages": messages,
            "results": current_table
        }

    # Determine table description
    if table_description is not None:
        new_table_desc = table_description
    else:
        new_table_desc = current_table.get("description", "")
        
    # Build PATCH request body
    request_body = {}
    if table_description is not None:
        request_body["description"] = new_table_desc
        
    request_body["schema"] = {
        "fields": updated_fields
    }
    
    # Prepare URL
    url = rest_api if rest_api else f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}"
    
    messages.append(f"Attempting to patch BigQuery table '{table_id}' metadata...")
    try:
        json_result = rest_api_helper(url, "PATCH", request_body)
        messages.append(f"Successfully patched BigQuery table '{table_id}' metadata in dataset '{dataset_id}'.")
        return {
            "status": "success",
            "tool_name": "patch_bigquery_table",
            "messages": messages,
            "results": json_result
        }
    except Exception as e:
        messages.append(f"Failed to patch BigQuery table '{table_id}' metadata: {e}")
        return {
            "status": "failed",
            "tool_name": "patch_bigquery_table",
            "messages": messages,
            "results": None
        }


import os
import json
import re

def load_env_config(env_file_path: str = "agent-config.json") -> dict:
    """Loads environment configurations from the specified JSON file."""
    if os.path.exists(env_file_path):
        try:
            with open(env_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def update_frontmatter_resources(file_path: str, resource_val: str, rest_api_val: str = None) -> bool:
    """
    Updates or inserts the 'resource' and optionally 'rest_api' properties
    in the YAML frontmatter of an OKF markdown file while preserving all other contents.
    """
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            return False

        fm_lines = parts[1].splitlines()
        
        has_orig_resource = any(re.match(r'^\s*resource\s*:', l) for l in fm_lines)
        has_orig_rest_api = any(re.match(r'^\s*(rest_api|rest-api)\s*:', l) for l in fm_lines)

        new_fm_lines = []
        for line in fm_lines:
            if re.match(r'^\s*resource\s*:', line):
                new_fm_lines.append(f'resource: "{resource_val}"')
                if rest_api_val and not has_orig_rest_api:
                    new_fm_lines.append(f'rest_api: "{rest_api_val}"')
                    has_orig_rest_api = True
            elif rest_api_val and re.match(r'^\s*(rest_api|rest-api)\s*:', line):
                new_fm_lines.append(f'rest_api: "{rest_api_val}"')
            elif not has_orig_resource and re.match(r'^\s*type\s*:', line):
                new_fm_lines.append(line)
                new_fm_lines.append(f'resource: "{resource_val}"')
                has_orig_resource = True
                if rest_api_val and not has_orig_rest_api:
                    new_fm_lines.append(f'rest_api: "{rest_api_val}"')
                    has_orig_rest_api = True
            else:
                new_fm_lines.append(line)

        if not has_orig_resource and not any(re.match(r'^\s*resource\s*:', l) for l in new_fm_lines):
            new_fm_lines.insert(0, f'resource: "{resource_val}"')
            if rest_api_val and not any(re.match(r'^\s*rest_api\s*:', l) for l in new_fm_lines):
                new_fm_lines.insert(1, f'rest_api: "{rest_api_val}"')

        fm_content = "\n".join(new_fm_lines).strip()
        prefix = parts[0]
        new_content = f"{prefix}---\n{fm_content}\n---{parts[2]}"
        if new_content == content:
            return True
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception:
        return False

def parse_table_markdown(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Parse frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    yaml_lines = parts[1].strip().splitlines()
    fm = {}
    for line in yaml_lines:
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip("'\"")

    # 2. Extract column descriptions from the table schema
    body = parts[2]
    lines = body.splitlines()
    col_descs = {}
    
    in_schema_section = False
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        
        # Check for # Schema heading
        if line_str.startswith("# Schema"):
            in_schema_section = True
            continue
        
        # If in schema section, parse table rows
        if in_schema_section:
            if line_str.startswith("#"):
                # Hit next section (e.g. # Citations), stop parsing
                in_schema_section = False
                continue
                
            if line_str.startswith("|"):
                row_parts = [p.strip() for p in line_str.split("|")]
                if len(row_parts) >= 4:
                    col_name = row_parts[1].strip("`").strip()
                    col_desc = row_parts[2]
                    # Filter header separators and column headers
                    if col_name and col_name.lower() != "field name" and not re.match(r"^[\s:-]+$", col_name):
                        col_descs[col_name] = col_desc
                        
    return {
        "title": fm.get("title"),
        "description": fm.get("description"),
        "resource": fm.get("resource"),
        "rest_api": fm.get("rest_api") or fm.get("rest-api"),
        "column_descriptions": col_descs
    }

def sync_okf_to_bigquery(
    tables_dir: str = "okf/tables",
    project_id: str = None,
    dataset_id: str = None
) -> dict:
    """
    Synchronises descriptions and schemas from OKF table markdown files directly to BigQuery.
    """
    messages = []
    
    # 1. Load config fallback
    env_config = load_env_config()
    if not project_id:
        project_id = env_config.get("gcp-project-id") or env_config.get("project_id") or env_config.get("project")
    if not dataset_id:
        dataset_id = env_config.get("bigquery-dataset") or env_config.get("dataset_id") or env_config.get("dataset")

    # Normalize path
    if not os.path.isabs(tables_dir):
        tables_dir = os.path.abspath(tables_dir)

    if not os.path.exists(tables_dir):
        messages.append(f"Error: OKF tables directory does not exist: {tables_dir}")
        return {
            "status": "failed",
            "tool_name": "sync_okf_to_bigquery",
            "messages": messages,
            "results": None
        }

    # Find all table markdown files
    table_files = [f for f in os.listdir(tables_dir) if f.endswith(".md") and f != "index.md"]
    table_files.sort()
    messages.append(f"Found {len(table_files)} table schema files under '{tables_dir}' to synchronise.")

    success_count = 0
    total_count = len(table_files)

    for f in table_files:
        file_path = os.path.join(tables_dir, f)
        try:
            parsed = parse_table_markdown(file_path)
            if not parsed or not parsed.get("title"):
                messages.append(f"Warning: Skipping file '{f}' because it does not contain a valid OKF table structure.")
                continue

            table_id = parsed["title"]
            table_desc = parsed["description"]
            col_descs = parsed["column_descriptions"]

            # Parse project/dataset from the resource URL if not provided
            tgt_project = project_id
            tgt_dataset = dataset_id
            
            res_url = parsed.get("resource", "")
            if res_url and (not tgt_project or not tgt_dataset):
                url_match = re.search(r'/projects/([^/]+)/datasets/([^/]+)/tables/', res_url)
                if url_match:
                    if not tgt_project:
                        tgt_project = url_match.group(1)
                    if not tgt_dataset:
                        tgt_dataset = url_match.group(2)

            if not tgt_project or not tgt_dataset:
                messages.append(f"Error: Could not resolve GCP Project ID or Dataset ID for table '{table_id}'. Skipping.")
                continue

            messages.append(f"Syncing metadata for table '{table_id}' to BigQuery ({tgt_project}:{tgt_dataset})...")
            
            patch_res = patch_bigquery_table(
                project_id=tgt_project,
                dataset_id=tgt_dataset,
                table_id=table_id,
                table_description=table_desc,
                column_descriptions=col_descs,
                rest_api=parsed.get("rest_api")
            )
            messages.extend(patch_res.get("messages", []))
            if patch_res["status"] == "success":
                success_count += 1
                messages.append(f"Successfully synchronised '{table_id}' schema metadata.")
                # Save resource and rest_api to OKF table file
                resource_url = f"https://bigquery.googleapis.com/v2/projects/{tgt_project}/datasets/{tgt_dataset}/tables/{table_id}"
                rest_api_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{tgt_project}/datasets/{tgt_dataset}/tables/{table_id}"
                if update_frontmatter_resources(file_path, resource_url, rest_api_url):
                    messages.append(f"Persisted resource in '{f}': {resource_url}")
            else:
                messages.append(f"Failed to synchronise '{table_id}' metadata.")

        except Exception as e:
            messages.append(f"Error syncing table file '{f}': {e}")

    messages.append(f"BigQuery metadata sync completed: {success_count}/{total_count} tables synchronised successfully.")
    return {
        "status": "success" if success_count == total_count else "partial" if success_count > 0 else "failed",
        "tool_name": "sync_okf_to_bigquery",
        "messages": messages,
        "results": {
            "tables_count": success_count,
            "total_tables": total_count
        }
    }


def patch_bigquery_dataset(project_id: str, dataset_id: str, dataset_description: str = None, rest_api: str = None) -> dict:
    """
    Patches a BigQuery dataset with a dataset description.
    """
    messages = []
    request_body = {}
    if dataset_description is not None:
        request_body["description"] = dataset_description

    url = rest_api if rest_api else f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}"
    messages.append(f"Attempting to patch BigQuery dataset '{dataset_id}' in project '{project_id}'...")
    try:
        json_result = rest_api_helper(url, "PATCH", request_body)
        messages.append(f"Successfully patched BigQuery dataset '{dataset_id}' metadata.")
        return {
            "status": "success",
            "tool_name": "patch_bigquery_dataset",
            "messages": messages,
            "results": json_result
        }
    except Exception as e:
        messages.append(f"Failed to patch BigQuery dataset '{dataset_id}' metadata: {e}")
        return {
            "status": "failed",
            "tool_name": "patch_bigquery_dataset",
            "messages": messages,
            "results": None
        }


def parse_dataset_markdown(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    yaml_lines = parts[1].strip().splitlines()
    fm = {}
    for line in yaml_lines:
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip("'\"")

    return {
        "title": fm.get("title"),
        "description": fm.get("description"),
        "resource": fm.get("resource"),
        "rest_api": fm.get("rest_api") or fm.get("rest-api")
    }


def sync_okf_datasets_to_bigquery(
    datasets_dir: str = "okf/datasets",
    project_id: str = None,
    dataset_id: str = None
) -> dict:
    """
    Synchronises descriptions from OKF dataset markdown files directly to BigQuery.
    """
    messages = []
    
    env_config = load_env_config()
    if not project_id:
        project_id = env_config.get("gcp-project-id") or env_config.get("project_id") or env_config.get("project")
    if not dataset_id:
        dataset_id = env_config.get("bigquery-dataset") or env_config.get("dataset_id") or env_config.get("dataset")

    if not os.path.isabs(datasets_dir):
        datasets_dir = os.path.abspath(datasets_dir)

    if not os.path.exists(datasets_dir):
        messages.append(f"Error: OKF datasets directory does not exist: {datasets_dir}")
        return {
            "status": "failed",
            "tool_name": "sync_okf_datasets_to_bigquery",
            "messages": messages,
            "results": None
        }

    dataset_files = [f for f in os.listdir(datasets_dir) if f.endswith(".md") and f != "index.md"]
    dataset_files.sort()
    messages.append(f"Found {len(dataset_files)} dataset schema files under '{datasets_dir}' to synchronise.")

    success_count = 0
    total_count = len(dataset_files)

    for f in dataset_files:
        file_path = os.path.join(datasets_dir, f)
        try:
            parsed = parse_dataset_markdown(file_path)
            if not parsed or not parsed.get("title"):
                messages.append(f"Warning: Skipping file '{f}' because it does not contain a valid OKF dataset structure.")
                continue

            target_dataset_id = parsed["title"]
            dataset_desc = parsed["description"]

            tgt_project = project_id
            res_url = parsed.get("resource", "")
            if res_url and not tgt_project:
                url_match = re.search(r'/projects/([^/]+)/datasets/', res_url)
                if url_match:
                    tgt_project = url_match.group(1)

            if not tgt_project:
                messages.append(f"Error: Could not resolve GCP Project ID for dataset '{target_dataset_id}'. Skipping.")
                continue

            messages.append(f"Syncing metadata for dataset '{target_dataset_id}' to BigQuery ({tgt_project})...")
            
            patch_res = patch_bigquery_dataset(
                project_id=tgt_project,
                dataset_id=target_dataset_id,
                dataset_description=dataset_desc,
                rest_api=parsed.get("rest_api")
            )
            messages.extend(patch_res.get("messages", []))
            if patch_res["status"] == "success":
                success_count += 1
                messages.append(f"Successfully synchronised '{target_dataset_id}' dataset metadata.")
                # Save resource and rest_api to OKF dataset file
                resource_url = f"https://bigquery.googleapis.com/v2/projects/{tgt_project}/datasets/{target_dataset_id}"
                rest_api_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{tgt_project}/datasets/{target_dataset_id}"
                if update_frontmatter_resources(file_path, resource_url, rest_api_url):
                    messages.append(f"Persisted resource in '{f}': {resource_url}")
            else:
                messages.append(f"Failed to synchronise '{target_dataset_id}' dataset metadata.")

        except Exception as e:
            messages.append(f"Error syncing dataset file '{f}': {e}")

    messages.append(f"BigQuery dataset metadata sync completed: {success_count}/{total_count} datasets synchronised successfully.")
    return {
        "status": "success" if success_count == total_count else "partial" if success_count > 0 else "failed",
        "tool_name": "sync_okf_datasets_to_bigquery",
        "messages": messages,
        "results": {
            "datasets_count": success_count,
            "total_datasets": total_count
        }
    }


