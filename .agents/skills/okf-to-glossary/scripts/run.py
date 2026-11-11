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


def get_business_glossaries(project_id: str, dataplex_region: str) -> dict: 
    """
    Lists all Dataplex business glossaries in the configured region.
    """
    messages = []
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries"

    try:
        json_result = rest_api_helper(url, "GET", None) 
        messages.append("Successfully retrieved list of all business glossaries from the API.")
        glossaries = json_result.get("glossaries", [])
        messages.append(f"Found {len(glossaries)} business glossaries.")
        return {
            "status": "success",
            "tool_name": "get_business_glossaries",
            "messages": messages,
            "results": {"glossaries": glossaries}
        }
    except Exception as e:
        messages.append(f"An error occurred while listing business glossaries: {e}")
        return {
            "status": "failed",
            "tool_name": "get_business_glossaries",
            "messages": messages,
            "results": None
        }


def exists_business_glossary(project_id: str, dataplex_region: str, glossary_id: str) -> dict: 
    """
    Checks if a Dataplex business glossary already exists by checking the full list.
    """
    list_result = get_business_glossaries(project_id, dataplex_region) 
    messages = list_result.get("messages", [])

    if list_result["status"] == "failed":
        return {
            "status": "failed",
            "tool_name": "exists_business_glossary", 
            "messages": messages,
            "results": None
        }

    try:
        glossary_exists = False
        json_payload = list_result.get("results", {})
        full_glossary_name_to_find = f"projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}"

        for item in json_payload.get("glossaries", []):
            if item.get("name") == full_glossary_name_to_find:
                glossary_exists = True
                messages.append(f"Found matching glossary: '{glossary_id}'.")
                break

        if not glossary_exists:
            messages.append(f"Glossary '{glossary_id}' does not exist.")

        return {
            "status": "success",
            "tool_name": "exists_business_glossary",
            "messages": messages,
            "results": {"exists": glossary_exists}
        }
    except Exception as e:
        messages.append(f"An unexpected error occurred while processing glossary list: {e}")
        return {
            "status": "failed",
            "tool_name": "exists_business_glossary",
            "messages": messages,
            "results": None
        }


import time

def wait_for_operation(operation_res: dict) -> dict:
    """
    Blocks and polls a Google Cloud Long-Running Operation (LRO) until completion.
    """
    if not isinstance(operation_res, dict) or "name" not in operation_res:
        return operation_res
    
    op_name = operation_res["name"]
    if "/operations/" not in op_name:
        return operation_res
        
    url = f"https://dataplex.googleapis.com/v1/{op_name}"
    done = operation_res.get("done", False)
    
    attempts = 0
    while not done and attempts < 60:
        time.sleep(2)
        try:
            op_res = rest_api_helper(url, "GET", None)
            done = op_res.get("done", False)
            if done:
                return op_res.get("response", op_res)
        except Exception:
            pass
        attempts += 1
        
    return operation_res

def create_business_glossary(project_id: str, dataplex_region: str, glossary_id: str, display_name: str, description: str = "") -> dict: 
    """
    Creates a new Dataplex business glossary if it does not already exist.
    """
    messages = []
    list_result = get_business_glossaries(project_id, dataplex_region) 
    messages.extend(list_result.get("messages", []))

    if list_result["status"] == "failed":
        return {
            "status": "failed",
            "tool_name": "create_business_glossary",
            "messages": messages,
            "exists" : False,
            "results": None
        }

    glossaries = list_result.get("results", {}).get("glossaries", [])
    glossary_exists = False
    full_glossary_name_to_find = f"projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}"

    for glossary in glossaries:
        if glossary.get("name") == full_glossary_name_to_find:
            glossary_exists = True
            break

    if glossary_exists:
        messages.append(f"Business glossary '{glossary_id}' already exists.")
        return {
            "status": "success",
            "tool_name": "create_business_glossary",
            "messages": messages,
            "exists" : True,
            "results": {"name": full_glossary_name_to_find }
        }

    messages.append(f"Creating business glossary '{glossary_id}'.")
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries?glossaryId={glossary_id}"

    request_body = {
        "displayName": display_name,
        "description": description
    }

    try:
        json_result = rest_api_helper(url, "POST", request_body) 
        messages.append(f"Initiated business glossary creation for '{glossary_id}'. Waiting for completion...")
        wait_for_operation(json_result)
        messages.append(f"Successfully created business glossary '{glossary_id}'.")
        return {
            "status": "success",
            "tool_name": "create_business_glossary",
            "messages": messages,
            "exists" : False,
            "results": json_result
        }
    except Exception as e:
        messages.append(f"An error occurred while creating the business glossary: {e}")
        return {
            "status": "failed",
            "tool_name": "create_business_glossary",
            "messages": messages,
            "exists" : False,
            "results": None
        }

    
    
def get_business_glossary(project_id: str, dataplex_region: str, glossary_id: str) -> dict: 
    """
    Gets a single Dataplex business glossary in the configured region.
    """
    messages = []
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}"

    try:
        json_result = rest_api_helper(url, "GET", None) 
        messages.append(f"Successfully retrieved details for business glossary '{glossary_id}' from the API.")
        return {
            "status": "success",
            "tool_name": "get_business_glossary",
            "messages": messages,
            "exists": True,
            "results": json_result
        }
    except RuntimeError as e: 
        error_message = str(e)
        if "HTTP Status: 404" in error_message:
            messages.append(f"Business Glossary '{glossary_id}' not found.")
            return {
                "status": "success",
                "tool_name": "get_business_glossary",
                "messages": messages,
                "exists": False,
                "results": None
            }
        else:
            messages.append(f"An API error occurred while getting business glossary '{glossary_id}': {error_message}")
            return {
                "status": "failed",
                "tool_name": "get_business_glossary",
                "messages": messages,
                "exists": False,
                "results": None
            }


def delete_business_glossary(project_id: str, dataplex_region: str, glossary_id: str) -> dict: 
    """
    Deletes a specific Dataplex Business Glossary.
    Note: A glossary must be empty (contain no terms or categories) to be deleted.
    """
    messages = []
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}"

    try:
        messages.append(f"Attempting to delete business glossary '{glossary_id}'.")
        _ = rest_api_helper(url, "DELETE", None) 
        messages.append(f"Successfully deleted business glossary '{glossary_id}'.")
        return {
            "status": "success",
            "tool_name": "delete_business_glossary",
            "messages": messages,
            "results": {"deleted": True, "glossary_id": glossary_id}
        }
    except Exception as e:
        messages.append(f"Failed to delete business glossary '{glossary_id}': {e}")
        return {
            "status": "failed",
            "tool_name": "delete_business_glossary",
            "messages": messages,
            "results": {"deleted": False, "glossary_id": glossary_id, "error": str(e)}
        }


def get_business_glossary_categories(project_id: str, dataplex_region: str, glossary_id: str) -> dict: 
    """
    Lists all categories within a specified Dataplex business glossary.
    """
    messages = []
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/categories"

    try:
        json_result = rest_api_helper(url, "GET", None) 
        messages.append(f"Successfully retrieved list of categories for glossary '{glossary_id}' from the API.")
        categories = json_result.get("categories", [])
        messages.append(f"Found {len(categories)} categories in glossary '{glossary_id}'.")
        return {
            "status": "success",
            "tool_name": "get_business_glossary_categories",
            "messages": messages,
            "results": {"categories": categories}
        }
    except Exception as e:
        messages.append(f"An error occurred while listing categories for glossary '{glossary_id}': {e}")
        return {
            "status": "failed",
            "tool_name": "get_business_glossary_categories",
            "messages": messages,
            "results": None
        }


def get_business_glossary_category(project_id: str, dataplex_region: str, glossary_id: str, category_id: str) -> dict: 
    """
    Gets a single Dataplex business glossary category within a specified glossary.
    """
    messages = []
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/categories/{category_id}"

    try:
        json_result = rest_api_helper(url, "GET", None) 
        messages.append(f"Successfully retrieved details for category '{category_id}' in glossary '{glossary_id}' from the API.")
        return {
            "status": "success",
            "tool_name": "get_business_glossary_category",
            "messages": messages,
            "exists": True,
            "results": json_result
        }
    except RuntimeError as e: 
        error_message = str(e)
        if "HTTP Status: 404" in error_message:
            messages.append(f"Category '{category_id}' not found in glossary '{glossary_id}'.")
            return {
                "status": "success",
                "tool_name": "get_business_glossary_category",
                "messages": messages,
                "exists": False,
                "results": None
            }
        else:
            messages.append(f"An API error occurred while getting category '{category_id}' in glossary '{glossary_id}': {error_message}")
            return {
                "status": "failed",
                "tool_name": "get_business_glossary_category",
                "messages": messages,
                "exists": False,
                "results": None
            }
    except Exception as e:
        messages.append(f"An unexpected system error occurred: {e}")
        return {
            "status": "failed",
            "tool_name": "get_business_glossary_category",
            "messages": messages,
            "exists": False,
            "results": None
        }


def create_business_glossary_category(project_id: str, dataplex_region: str, glossary_id: str, category_id: str, display_name: str, description: str = "", skip_existence_check: bool = False) -> dict: 
    """
    Creates a new Dataplex business glossary category if it does not already exist.
    """
    messages = []
    if not skip_existence_check:
        existence_check = get_business_glossary_category(project_id, dataplex_region, glossary_id, category_id) 
        messages.extend(existence_check.get("messages", []))

        if existence_check["status"] == "success":
            if existence_check["exists"] == True:
                full_category_name = existence_check["results"].get("name")
                messages.append(f"Business glossary category '{category_id}' already exists in glossary '{glossary_id}'.")
                return {
                    "status": "success",
                    "tool_name": "create_business_glossary_category",
                    "messages": messages,
                    "exists" : True,
                    "results": { "name": full_category_name }
                }
        else:
            messages.append(f"An unexpected error occurred during the existence check for category '{category_id}'.")
            return {
                "status": "failed",
                "tool_name": "create_business_glossary_category",
                "messages": messages,
                "exists" : False,
                "results": None
            }

    messages.append(f"Attempting to create business glossary category '{category_id}' in glossary '{glossary_id}'.")
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/categories?categoryId={category_id}"
    parent_glossary_name = f"projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}"

    request_body = {
        "displayName": display_name,
        "description": description,
        "parent": parent_glossary_name
    }

    try:
        json_result = rest_api_helper(url, "POST", request_body) 
        messages.append(f"Successfully created business glossary category '{category_id}' in glossary '{glossary_id}'.")
        return {
            "status": "success",
            "tool_name": "create_business_glossary_category",
            "messages": messages,
            "exists" : False,
            "results": json_result
        }
    except Exception as e:
        messages.append(f"An error occurred while creating the business glossary category '{category_id}': {e}")
        return {
            "status": "failed",
            "tool_name": "create_business_glossary_category",
            "messages": messages,
            "exists" : False,
            "results": None
        }


def delete_business_glossary_category(project_id: str, dataplex_region: str, glossary_id: str, category_id: str) -> dict: 
    """
    Deletes a specific Dataplex Business Glossary category.
    Note: A category must be empty (contain no terms or nested categories) to be deleted.
    """
    messages = []
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/categories/{category_id}"

    try:
        messages.append(f"Attempting to delete category '{category_id}' from glossary '{glossary_id}'.")
        _ = rest_api_helper(url, "DELETE", None) 
        messages.append(f"Successfully deleted category '{category_id}' from glossary '{glossary_id}'.")
        return {
            "status": "success",
            "tool_name": "delete_business_glossary_category",
            "messages": messages,
            "results": {"deleted": True, "category_id": category_id, "glossary_id": glossary_id}
        }
    except Exception as e:
        messages.append(f"Failed to delete category '{category_id}' from glossary '{glossary_id}': {e}")
        return {
            "status": "failed",
            "tool_name": "delete_business_glossary_category",
            "messages": messages,
            "results": {"deleted": False, "category_id": category_id, "glossary_id": glossary_id, "error": str(e)}
        }


def get_business_glossary_term(project_id: str, dataplex_region: str, glossary_id: str, term_id: str) -> dict: 
    """
    Gets a single Dataplex business glossary term.
    """
    messages = []
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/terms/{term_id}"

    try:
        json_result = rest_api_helper(url, "GET", None) 
        messages.append(f"Successfully retrieved details for term '{term_id}' in glossary '{glossary_id}' from the API.")
        return {
            "status": "success",
            "tool_name": "get_business_glossary_term",
            "messages": messages,
            "exists": True,
            "results": json_result
        }
    except RuntimeError as e: 
        error_message = str(e)
        if "HTTP Status: 404" in error_message:
            messages.append(f"Term '{term_id}' not found.")
            return {
                "status": "success",
                "tool_name": "get_business_glossary_term",
                "messages": messages,
                "exists": False,
                "results": None
            }
        else:
            messages.append(f"An API error occurred while getting term '{term_id}': {error_message}")
            return {
                "status": "failed",
                "tool_name": "get_business_glossary_term",
                "messages": messages,
                "exists": False,
                "results": None
            }


def list_business_glossary_terms(project_id: str, dataplex_region: str, glossary_id: str) -> dict: 
    """
    Lists all terms within a specified Dataplex business glossary.
    """
    messages = []
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/terms?pageSize=1000"

    try:
        json_result = rest_api_helper(url, "GET", None) 
        messages.append(f"Successfully retrieved list of terms for glossary '{glossary_id}' from the API.")
        terms = json_result.get("terms", [])
        messages.append(f"Found {len(terms)} terms in glossary '{glossary_id}'.")
        return {
            "status": "success",
            "tool_name": "list_business_glossary_terms",
            "messages": messages,
            "results": {"terms": terms}
        }
    except Exception as e:
        messages.append(f"An error occurred while listing terms for glossary '{glossary_id}': {e}")
        return {
            "status": "failed",
            "tool_name": "list_business_glossary_terms",
            "messages": messages,
            "results": None
        }


def create_business_glossary_term( 
    project_id: str,
    dataplex_region: str,
    glossary_id: str,
    term_id: str,
    display_name: str,
    description: str = "",
    parent_category_id: str = "",
    skip_existence_check: bool = False
) -> dict:
    """
    Creates a new Dataplex business glossary term if it does not already exist.
    """
    messages = []
    term_id = term_id.strip()
    if not skip_existence_check:
        existence_check = get_business_glossary_term(project_id, dataplex_region, glossary_id, term_id) 
        messages.extend(existence_check.get("messages", []))

        if existence_check["status"] == "success":
            if existence_check["exists"] == True:
                full_term_name = existence_check["results"].get("name")
                messages.append(f"Business glossary term '{term_id}' already exists in glossary '{glossary_id}'.")
                return {
                    "status": "success",
                    "tool_name": "create_business_glossary_term",
                    "messages": messages,
                    "exists" : True,
                    "results": {"name": full_term_name }
            }
        else:
            messages.append(f"An unexpected error occurred during the existence check for term '{term_id}'.")
            return {
                "status": "failed",
                "tool_name": "create_business_glossary_term",
                "messages": messages,
                "exists" : False,
                "results": None
            }

    messages.append(f"Attempting to create business glossary term '{term_id}' in glossary '{glossary_id}'.")
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/terms?termId={term_id}"

    if parent_category_id:
        parent_resource = f"projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/categories/{parent_category_id}"
        messages.append(f"Term will be nested under category: '{parent_category_id}'.")
    else:
        parent_resource = f"projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}"
        messages.append("Term will be created directly under the glossary.")

    request_body = {
        "displayName": display_name,
        "description": description,
        "parent": parent_resource
    }

    try:
        json_result = rest_api_helper(url, "POST", request_body) 
        messages.append(f"Successfully created business glossary term '{term_id}'.")
        return {
            "status": "success",
            "tool_name": "create_business_glossary_term",
            "messages": messages,
            "exists" : False,
            "results": json_result
        }
    except Exception as e:
        messages.append(f"An error occurred while creating the business glossary term '{term_id}': {e}")
        return {
            "status": "failed",
            "tool_name": "create_business_glossary_term",
            "messages": messages,
            "exists" : False,
            "results": None
        }


def update_business_glossary_term( 
    project_id: str,
    dataplex_region: str,
    glossary_id: str,
    term_id: str,
    display_name: str = None, 
    description: str = None
) -> dict:
    """
    Updates an existing Dataplex business glossary term.
    """
    messages = []
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/terms/{term_id}"

    update_mask_fields = []
    request_body = {}

    if display_name is not None:
        request_body["displayName"] = display_name
        update_mask_fields.append("displayName")
    if description is not None:
        request_body["description"] = description
        update_mask_fields.append("description")

    if not update_mask_fields:
        messages.append("No fields provided for update. Skipping update operation.")
        return {
            "status": "success",
            "tool_name": "update_business_glossary_term",
            "messages": messages,
            "results": {"updated": False, "reason": "No fields to update"}
        }

    update_mask = ",".join(update_mask_fields)
    url_with_mask = f"{url}?update_mask={update_mask}"

    messages.append(f"Attempting to update business glossary term '{term_id}' with fields: {update_mask_fields}.")

    try:
        json_result = rest_api_helper(url_with_mask, "PATCH", request_body) 
        messages.append(f"Successfully updated business glossary term '{term_id}'.")
        return {
            "status": "success",
            "tool_name": "update_business_glossary_term",
            "messages": messages,
            "results": json_result
        }
    except Exception as e:
        messages.append(f"An error occurred while updating the business glossary term '{term_id}': {e}")
        return {
            "status": "failed",
            "tool_name": "update_business_glossary_term",
            "messages": messages,
            "results": None
        }


def delete_business_glossary_term(project_id: str, dataplex_region: str, glossary_id: str, term_id: str) -> dict: 
    """
    Deletes a specific Dataplex Business Glossary term.
    """
    messages = []
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/terms/{term_id}"

    try:
        messages.append(f"Attempting to delete term '{term_id}' from glossary '{glossary_id}'.")
        _ = rest_api_helper(url, "DELETE", None) 
        messages.append(f"Successfully deleted term '{term_id}' from glossary '{glossary_id}'.")
        return {
            "status": "success",
            "tool_name": "delete_business_glossary_term",
            "messages": messages,
            "results": {"deleted": True, "term_id": term_id, "glossary_id": glossary_id}
        }
    except Exception as e:
        messages.append(f"Failed to delete term '{term_id}' from glossary '{glossary_id}': {e}")
        return {
            "status": "failed",
            "tool_name": "delete_business_glossary_term",
            "messages": messages,
            "results": {"deleted": False, "term_id": term_id, "glossary_id": glossary_id, "error": str(e)}
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

def slugify(text: str) -> str:
    """Generate a safe ID slug from text."""
    text = text.lower()
    text = re.sub(r'[\s\-/]+', '_', text)
    text = re.sub(r'[^a-z0-9_]', '', text)
    text = re.sub(r'_+', '_', text)
    return text.strip('_')

def parse_frontmatter(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    
    yaml_lines = parts[1].strip().splitlines()
    data = {}
    current_key = None
    
    for line in yaml_lines:
        line_str = line.strip()
        if not line_str:
            continue
        if line_str.startswith("-"):
            if current_key and isinstance(data.get(current_key), list):
                item = line_str[1:].strip().strip("'\"")
                data[current_key].append(item)
            continue
        
        if ":" in line_str:
            key, val = line_str.split(":", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if val == "":
                data[key] = []
                current_key = key
            else:
                data[key] = val
                current_key = key
    return data

def update_frontmatter_resources(file_path: str, resource_val: str, rest_api_val: str = None) -> bool:
    """
    Safely injects or updates 'resource' and 'rest_api' fields in the YAML frontmatter
    of a markdown file without modifying or reformatting any other content.
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

def get_project_number(project_id: str) -> str:
    """
    Retrieves the numeric project number for a given project ID from the Resource Manager API.
    """
    url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}"
    try:
        res = rest_api_helper(url, "GET", None)
        num = res.get("projectNumber")
        if num:
            return str(num)
    except Exception:
        pass
    return project_id

def create_synonym_relationship(
    project_id: str,
    project_number: str,
    dataplex_region: str,
    glossary_id: str,
    term_id_1: str,
    term_id_2: str
) -> dict:
    """
    Establishes a bi-directional synonym relationship between two terms using entryLinks.
    """
    messages = []
    
    # Construct a safe entry_link_id containing only lowercase letters, numbers, and hyphens.
    entry_link_id = f"{term_id_1}-{term_id_2}".lower().replace("_", "-")
    
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/entryGroups/@dataplex/entryLinks?entryLinkId={entry_link_id}"
    
    entry_1_name = f"projects/{project_number}/locations/{dataplex_region}/entryGroups/@dataplex/entries/projects/{project_number}/locations/{dataplex_region}/glossaries/{glossary_id}/terms/{term_id_1}"
    entry_2_name = f"projects/{project_number}/locations/{dataplex_region}/entryGroups/@dataplex/entries/projects/{project_number}/locations/{dataplex_region}/glossaries/{glossary_id}/terms/{term_id_2}"
    
    request_body = {
        "entryLinkType": "projects/dataplex-types/locations/global/entryLinkTypes/synonym",
        "entryReferences": [
            { "name": entry_1_name },
            { "name": entry_2_name }
        ]
    }
    
    messages.append(f"Creating synonym link between '{term_id_1}' and '{term_id_2}' (entryLinkId: '{entry_link_id}')...")
    try:
        json_result = rest_api_helper(url, "POST", request_body)
        messages.append(f"Successfully created synonym link between '{term_id_1}' and '{term_id_2}' (entryLinkId: '{entry_link_id}').")
        return {
            "status": "success",
            "tool_name": "create_synonym_relationship",
            "messages": messages,
            "results": json_result
        }
    except Exception as e:
        err_msg = str(e)
        if "ALREADY_EXISTS" in err_msg or "409" in err_msg:
            messages.append(f"Synonym link between '{term_id_1}' and '{term_id_2}' already exists.")
            return {
                "status": "success",
                "tool_name": "create_synonym_relationship",
                "messages": messages,
                "results": None
            }
        messages.append(f"Failed to create synonym link between '{term_id_1}' and '{term_id_2}' (entryLinkId: '{entry_link_id}'): {e}")
        return {
            "status": "failed",
            "tool_name": "create_synonym_relationship",
            "messages": messages,
            "results": None
        }

def sync_okf_to_dataplex(
    okf_references_dir: str = "okf/references/glossary",
    glossary_id: str = None,
    project_id: str = None,
    dataplex_region: str = "global"
) -> dict:
    """
    Synchronises OKF glossary reference files to Dataplex Business Glossary.
    """
    messages = []
    
    # 1. Load config if defaults are omitted
    env_config = load_env_config()
    if not project_id:
        project_id = env_config.get("gcp-project-id") or env_config.get("project_id") or env_config.get("project")
    if not project_id:
        try:
            creds, project_id = google.auth.default()
        except Exception:
            pass

    if not glossary_id:
        glossary_id = env_config.get("business-glossary-id") or env_config.get("glossary_id") or "premium_outdoor_gear"

    if not dataplex_region or dataplex_region == "global":
        dataplex_region = env_config.get("business-glossary-region") or env_config.get("dataplex_region") or dataplex_region or "global"

    
    if not project_id:
        messages.append("Error: GCP Project ID is required but was not found or provided.")
        return {
            "status": "failed",
            "tool_name": "sync_okf_to_dataplex",
            "messages": messages,
            "results": None
        }

    project_number = get_project_number(project_id)
    messages.append(f"Resolved GCP project '{project_id}' to project number '{project_number}'.")

    # Normalize paths
    if not os.path.isabs(okf_references_dir):
        okf_references_dir = os.path.abspath(okf_references_dir)

    if not os.path.exists(okf_references_dir):
        messages.append(f"Error: OKF reference directory does not exist: {okf_references_dir}")
        return {
            "status": "failed",
            "tool_name": "sync_okf_to_dataplex",
            "messages": messages,
            "results": None
        }

    messages.append(f"Starting Dataplex sync to glossary '{glossary_id}' in project '{project_id}', region '{dataplex_region}'...")

    try:
        # 2. Ensure target glossary exists
        messages.append(f"Ensuring glossary '{glossary_id}' exists...")
        glossary_res = create_business_glossary(
            project_id=project_id,
            dataplex_region=dataplex_region,
            glossary_id=glossary_id,
            display_name=glossary_id.replace("_", " ").title(),
            description="Central business glossary synchronised from OKF references."
        )
        messages.extend(glossary_res.get("messages", []))
        if glossary_res["status"] == "failed":
            return glossary_res

        # 3. Read OKF references
        term_files = [f for f in os.listdir(okf_references_dir) if f.endswith(".md") and f != "index.md"]
        term_files.sort()
        messages.append(f"Found {len(term_files)} OKF glossary files to process.")

        # 4. First pass: Collect all unique categories
        categories = set()
        terms_data = []
        for f in term_files:
            file_path = os.path.join(okf_references_dir, f)
            term_slug = f[:-3]
            try:
                fm = parse_frontmatter(file_path)
                title = fm.get("title") or term_slug.replace("_", " ").title()
                category = fm.get("category") or "General"
                description = fm.get("description") or ""
                synonyms = fm.get("synonyms") or []
                if isinstance(synonyms, str):
                    synonyms = [synonyms]
                
                categories.add(category)
                terms_data.append({
                    "term_id": term_slug,
                    "title": title,
                    "category": category,
                    "category_id": slugify(category),
                    "description": description,
                    "synonyms": synonyms,
                    "file_path": file_path
                })
            except Exception as e:
                messages.append(f"Warning: Skipping file '{f}' due to frontmatter parse error: {e}")

        # 5. Ensure all categories exist in Dataplex (Single API call to list all categories)
        messages.append(f"Ensuring {len(categories)} categories exist in Dataplex...")
        existing_categories_res = get_business_glossary_categories(project_id, dataplex_region, glossary_id)
        existing_cat_ids = set()
        if existing_categories_res["status"] == "success":
            for cat_item in existing_categories_res.get("results", {}).get("categories", []):
                cat_name = cat_item.get("name", "")
                existing_cat_ids.add(cat_name.split("/")[-1])
        
        for cat in sorted(categories):
            cat_id = slugify(cat)
            if cat_id in existing_cat_ids:
                messages.append(f"Business glossary category '{cat_id}' already exists in glossary '{glossary_id}'.")
            else:
                cat_res = create_business_glossary_category(
                    project_id=project_id,
                    dataplex_region=dataplex_region,
                    glossary_id=glossary_id,
                    category_id=cat_id,
                    display_name=cat,
                    description=f"Glossary category for {cat} sync.",
                    skip_existence_check=True
                )
                messages.extend(cat_res.get("messages", []))
                if cat_res["status"] == "success":
                    existing_cat_ids.add(cat_id)

        # 6. Fetch existing terms in glossary in single request (pageSize=1000)
        messages.append(f"Fetching existing terms in glossary '{glossary_id}' in single request...")
        existing_terms_res = list_business_glossary_terms(project_id, dataplex_region, glossary_id)
        existing_terms_map = {}
        if existing_terms_res["status"] == "success":
            for term_item in existing_terms_res.get("results", {}).get("terms", []):
                t_id = term_item.get("name", "").split("/")[-1]
                existing_terms_map[t_id] = term_item

        # 7. Create or update terms and establish synonym links
        success_count = 0
        for t in terms_data:
            term_id = t["term_id"]
            display_name = t["title"]
            description = t["description"]
            category_id = t["category_id"]
            synonyms = t.get("synonyms", [])

            term_synced_successfully = False
            
            if term_id in existing_terms_map:
                existing_term = existing_terms_map[term_id]
                cur_disp = existing_term.get("displayName", "")
                cur_desc = existing_term.get("description", "")
                if cur_disp != display_name or cur_desc != description:
                    update_res = update_business_glossary_term(
                        project_id=project_id,
                        dataplex_region=dataplex_region,
                        glossary_id=glossary_id,
                        term_id=term_id,
                        display_name=display_name,
                        description=description
                    )
                    messages.extend(update_res.get("messages", []))
                    if update_res["status"] == "success":
                        success_count += 1
                        term_synced_successfully = True
                        existing_terms_map[term_id]["displayName"] = display_name
                        existing_terms_map[term_id]["description"] = description
                else:
                    messages.append(f"Term '{term_id}' is already up to date in glossary. Skipping update.")
                    success_count += 1
                    term_synced_successfully = True
            else:
                # Term does not exist -> Create it nested under its category
                create_res = create_business_glossary_term(
                    project_id=project_id,
                    dataplex_region=dataplex_region,
                    glossary_id=glossary_id,
                    term_id=term_id,
                    display_name=display_name,
                    description=description,
                    parent_category_id=category_id,
                    skip_existence_check=True
                )
                messages.extend(create_res.get("messages", []))
                if create_res["status"] == "success":
                    success_count += 1
                    term_synced_successfully = True
                    existing_terms_map[term_id] = {
                        "name": f"projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/terms/{term_id}",
                        "displayName": display_name,
                        "description": description
                    }

            if term_synced_successfully:
                resource_val = f"projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/terms/{term_id}"
                rest_api_val = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/terms/{term_id}"
                if t.get("file_path"):
                    update_frontmatter_resources(t["file_path"], resource_val, rest_api_val)

            # Synchronize synonym relationships if the term itself exists/updated successfully
            if term_synced_successfully and synonyms:
                messages.append(f"Processing synonyms for '{display_name}': {synonyms}")
                for syn in synonyms:
                    syn_slug = slugify(syn)
                    syn_desc = f"Synonym of {display_name}."
                    
                    syn_exists = False
                    if syn_slug in existing_terms_map:
                        existing_syn = existing_terms_map[syn_slug]
                        cur_syn_disp = existing_syn.get("displayName", "")
                        cur_syn_desc = existing_syn.get("description", "")
                        if cur_syn_disp != syn or cur_syn_desc != syn_desc:
                            update_syn_res = update_business_glossary_term(
                                project_id=project_id,
                                dataplex_region=dataplex_region,
                                glossary_id=glossary_id,
                                term_id=syn_slug,
                                display_name=syn,
                                description=syn_desc
                            )
                            messages.extend(update_syn_res.get("messages", []))
                            if update_syn_res["status"] == "success":
                                syn_exists = True
                                existing_terms_map[syn_slug]["displayName"] = syn
                                existing_terms_map[syn_slug]["description"] = syn_desc
                        else:
                            syn_exists = True
                    else:
                        create_syn_res = create_business_glossary_term(
                            project_id=project_id,
                            dataplex_region=dataplex_region,
                            glossary_id=glossary_id,
                            term_id=syn_slug,
                            display_name=syn,
                            description=syn_desc,
                            parent_category_id=category_id,
                            skip_existence_check=True
                        )
                        messages.extend(create_syn_res.get("messages", []))
                        if create_syn_res["status"] == "success":
                            syn_exists = True
                            existing_terms_map[syn_slug] = {
                                "name": f"projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/terms/{syn_slug}",
                                "displayName": syn,
                                "description": syn_desc
                            }
                    
                    if syn_exists:
                        syn_file_path = os.path.join(okf_references_dir, f"{syn_slug}.md")
                        if os.path.exists(syn_file_path):
                            syn_resource = f"projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/terms/{syn_slug}"
                            syn_rest_api = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/glossaries/{glossary_id}/terms/{syn_slug}"
                            update_frontmatter_resources(syn_file_path, syn_resource, syn_rest_api)

                    # 2. Establish bi-directional entryLink between main term and synonym term
                    if syn_exists:
                        link_res = create_synonym_relationship(
                            project_id=project_id,
                            project_number=project_number,
                            dataplex_region=dataplex_region,
                            glossary_id=glossary_id,
                            term_id_1=term_id,
                            term_id_2=syn_slug
                        )
                        messages.extend(link_res.get("messages", []))

        messages.append(f"Dataplex sync completed: {success_count}/{len(terms_data)} terms successfully synchronised.")
        return {
            "status": "success",
            "tool_name": "sync_okf_to_dataplex",
            "messages": messages,
            "results": {
                "glossary_id": glossary_id,
                "terms_count": success_count,
                "categories_count": len(categories)
            }
        }

    except Exception as e:
        messages.append(f"An unexpected error occurred during sync: {e}")
        return {
            "status": "failed",
            "tool_name": "sync_okf_to_dataplex",
            "messages": messages,
            "results": None
        }

