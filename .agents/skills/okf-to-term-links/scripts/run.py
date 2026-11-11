import os
import sys
import json
import re
import google.auth
import google.auth.transport.requests
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
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
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
        if response.status_code == 204 or not response.text:
            return {}
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

_CACHE_PROJECT_NUMBERS = {}
_CACHE_DATASET_LOCATIONS = {}

def get_project_number(project_id: str) -> str:
    """
    Retrieves the GCP project number for a given project ID using the Cloud Resource Manager API.
    """
    if project_id in _CACHE_PROJECT_NUMBERS:
        return _CACHE_PROJECT_NUMBERS[project_id]
    url = f"https://cloudresourcemanager.googleapis.com/v3/projects/{project_id}"
    try:
        res = rest_api_helper(url, "GET")
        if "projectNumber" in res:
            num = str(res["projectNumber"])
            _CACHE_PROJECT_NUMBERS[project_id] = num
            return num
        name = res.get("name", "")
        if name.startswith("projects/"):
            num = name.split("/")[-1]
            _CACHE_PROJECT_NUMBERS[project_id] = num
            return num
        raise ValueError(f"Could not find project number in response: {res}")
    except Exception as e:
        # Fallback: check if we can query an existing Dataplex entry or log search to see the project number
        raise RuntimeError(f"Failed to resolve project ID '{project_id}' to project number: {e}")

def get_dataset_location(project_id: str, dataset_id: str) -> str:
    """
    Retrieves the location (region) of a BigQuery dataset.
    """
    cache_key = (project_id, dataset_id)
    if cache_key in _CACHE_DATASET_LOCATIONS:
        return _CACHE_DATASET_LOCATIONS[cache_key]
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}"
    try:
        res = rest_api_helper(url, "GET")
        loc = res.get("location", "us")
        _CACHE_DATASET_LOCATIONS[cache_key] = loc
        return loc
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve location for dataset '{dataset_id}' in project '{project_id}': {e}")

def load_env_config(env_file_path: str = "agent-config.json") -> dict:
    """
    Loads environment configurations from the specified JSON file.
    """
    if not os.path.exists(env_file_path):
        # Check relative path
        alt_path = os.path.join(os.getcwd(), "agent-config.json")
        if os.path.exists(alt_path):
            env_file_path = alt_path
        else:
            raise FileNotFoundError(f"Environment config file not found at '{env_file_path}'")
            
    with open(env_file_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    # Clean the region string (e.g. "global (or should we use US?)" -> "us")
    region = config.get("business-glossary-region", "us")
    if "(" in region:
        # Check if actual glossaries can be found in 'us' first
        region = "us"
    config["business-glossary-region-clean"] = region
    
    # Extract clean glossary ID
    glossary_id = config.get("business-glossary-id", "l400-agentic-da-business-glossary")
    config["business-glossary-id-clean"] = glossary_id
    
    return config

def find_active_glossary(project_id: str, default_region: str = "global") -> tuple:
    """
    Finds the active glossary ID and region in the project for the specified region.
    Returns (glossary_id, region) or (None, None).
    """
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{default_region}/glossaries"
    try:
        res = rest_api_helper(url, "GET")
        glossaries = res.get("glossaries", [])
        if glossaries:
            full_name = glossaries[0]["name"]
            glossary_id = full_name.split("/")[-1]
            return glossary_id, default_region
    except Exception:
        pass
    return None, None

def search_knowledge_catalog(project_id: str, query: str) -> list:
    """
    Searches for entries in the Knowledge Catalog.
    """
    # Use default locations/global or us-central1 as the search endpoint
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/global:searchEntries"
    request_body = {
        "name": f"projects/{project_id}/locations/global",
        "query": query,
        "pageSize": 100
    }
    try:
        res = rest_api_helper(url, "POST", request_body)
        return res.get("results", [])
    except Exception:
        # Fallback to a region-specific endpoint if global search is not allowed/configured
        url_reg = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/us-central1:searchEntries"
        request_body["name"] = f"projects/{project_id}/locations/us-central1"
        try:
            res = rest_api_helper(url_reg, "POST", request_body)
            return res.get("results", [])
        except Exception as e:
            raise RuntimeError(f"Knowledge Catalog search failed: {e}")

_CACHE_TABLE_ENTRIES = {}
_CACHE_GLOSSARY_TERMS = {}
_CACHE_OKF_GLOSSARY_TERMS = None

def load_okf_glossary_terms(okf_references_dir: str = "okf/references/glossary", project_id: str = None) -> dict:
    """
    Scans the local OKF glossary directory (okf/references/glossary) and builds an in-memory lookup map
    for terms based on their 'resource' frontmatter.
    Returns a dictionary mapping identifiers (slug, title, normalized title, synonyms) to entry metadata.
    """
    global _CACHE_OKF_GLOSSARY_TERMS
    if _CACHE_OKF_GLOSSARY_TERMS is not None:
        return _CACHE_OKF_GLOSSARY_TERMS

    if not os.path.isabs(okf_references_dir):
        alt = os.path.join(os.getcwd(), okf_references_dir)
        if os.path.exists(alt):
            okf_references_dir = alt

    term_map = {}
    if not os.path.exists(okf_references_dir):
        _CACHE_OKF_GLOSSARY_TERMS = term_map
        return term_map

    # Resolve project number for constructing target entries
    env = load_env_config()
    p_id = project_id or env.get("gcp-project-id")
    try:
        p_num = get_project_number(p_id) if p_id else None
    except Exception:
        p_num = None

    for fname in os.listdir(okf_references_dir):
        if not fname.endswith(".md") or fname == "index.md":
            continue
        file_path = os.path.join(okf_references_dir, fname)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            fm_lines = parts[1].strip().splitlines()
            fm = {}
            in_synonyms = False
            synonyms = []
            for line in fm_lines:
                ls = line.strip()
                if ls.startswith("-") and in_synonyms:
                    syn = ls.strip("-").strip().strip("'\"")
                    if syn:
                        synonyms.append(syn)
                    continue
                else:
                    in_synonyms = False
                if ":" in ls:
                    k, v = ls.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip().strip("'\"")
                    if k == "synonyms":
                        in_synonyms = True
                        if v and v != "None":
                            cleaned_v = v.strip("[]").strip()
                            if cleaned_v:
                                synonyms.append(cleaned_v)
                    else:
                        fm[k] = v

            resource = fm.get("resource")
            title = fm.get("title") or fname[:-3].replace("_", " ").title()
            slug = fname[:-3]

            if not resource:
                continue

            # Parse resource: projects/{p}/locations/{loc}/glossaries/{g}/terms/{t}
            m = re.search(r'projects/([^/]+)/locations/([^/]+)/glossaries/([^/]+)/terms/([^/]+)', resource)
            if not m:
                continue

            term_proj = m.group(1)
            term_loc = m.group(2)
            term_glossary = m.group(3)
            term_id = m.group(4)

            term_proj_num = p_num if (p_num and term_proj == p_id) else None
            if not term_proj_num:
                try:
                    term_proj_num = get_project_number(term_proj)
                except Exception:
                    term_proj_num = term_proj

            target_name = f"projects/{term_proj_num}/locations/{term_loc}/entryGroups/@dataplex/entries/projects/{term_proj_num}/locations/{term_loc}/glossaries/{term_glossary}/terms/{term_id}"

            entry_info = {
                "name": target_name,
                "term_id": term_id,
                "display_name": title,
                "glossary_id": term_glossary,
                "location": term_loc,
                "project_number": term_proj_num,
                "resource": resource
            }

            def norm(s):
                s_no_parens = re.sub(r'\(.*?\)', '', s)
                cleaned = "".join(c for c in s_no_parens if c.isalnum() or c.isspace())
                return " ".join(cleaned.split()).lower()

            def slugify(text):
                s = text.lower()
                s = re.sub(r'[^a-z0-9\-]', '-', s)
                s = re.sub(r'-+', '-', s)
                return s.strip('-')

            keys_to_index = [
                term_id.lower(),
                slug.lower(),
                slug.replace("_", "-").lower(),
                slug.replace("-", "_").lower(),
                title.lower().strip(),
                norm(title),
                slugify(title)
            ]
            for syn in synonyms:
                keys_to_index.append(syn.lower().strip())
                keys_to_index.append(norm(syn))
                keys_to_index.append(slugify(syn))

            for k in keys_to_index:
                if k and k not in term_map:
                    term_map[k] = entry_info

        except Exception:
            continue

    _CACHE_OKF_GLOSSARY_TERMS = term_map
    return term_map

def resolve_table_entry(project_id: str = None, dataset_id: str = None, table_id: str = None, location: str = "us", resource: str = None) -> dict:
    """
    Resolves the BigQuery table's full entry resource path in Knowledge Catalog.
    Uses deterministic resolution as the primary fast path, falling back to searchEntries
    only if deterministic resolution cannot be completed.
    """
    # If resource URL is provided, parse IDs if needed
    if resource:
        m = re.search(r'/projects/([^/]+)/datasets/([^/]+)/tables/([^/]+)', resource)
        if m:
            project_id = project_id or m.group(1)
            dataset_id = dataset_id or m.group(2)
            table_id = table_id or m.group(3)

    cache_key = (project_id, dataset_id, table_id)
    if cache_key in _CACHE_TABLE_ENTRIES:
        return _CACHE_TABLE_ENTRIES[cache_key]

    # Fast Primary Path: Deterministic resolution
    # When project_id, dataset_id, and table_id are available, construct the entry ID directly without search.
    if project_id and dataset_id and table_id:
        try:
            project_number = get_project_number(project_id)
            dataset_location = get_dataset_location(project_id, dataset_id).lower()
            entry_id = f"bigquery.googleapis.com/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}"
            full_name = f"projects/{project_number}/locations/{dataset_location}/entryGroups/@bigquery/entries/{entry_id}"
            entry_data = {
                "name": full_name,
                "project_number": project_number,
                "location": dataset_location,
                "entry_group": "@bigquery",
                "entry_id": entry_id
            }
            _CACHE_TABLE_ENTRIES[cache_key] = entry_data
            return entry_data
        except Exception:
            # Fall back to Knowledge Catalog search if deterministic resolution fails
            pass

    # Fallback Path: Search Knowledge Catalog via searchEntries
    if project_id and table_id:
        fqn = f"bigquery:{project_id}.{dataset_id}.{table_id}" if dataset_id else f"bigquery:{project_id}.*.{table_id}"
        query = f"system:bigquery AND type:table AND name:{table_id}"
        try:
            results = search_knowledge_catalog(project_id, query)
            for result in results:
                entry = result.get("dataplexEntry", {})
                entry_fqn = entry.get("fullyQualifiedName", "")
                if entry_fqn.lower() == fqn.lower():
                    entry_data = {
                        "name": entry.get("name"),
                        "project_number": entry.get("name", "").split("/")[1],
                        "location": entry.get("name", "").split("/")[3].lower(),
                        "entry_group": "@bigquery",
                        "entry_id": "/".join(entry.get("name", "").split("/")[6:])
                    }
                    _CACHE_TABLE_ENTRIES[cache_key] = entry_data
                    return entry_data
        except Exception:
            pass

    # Final attempt: Deterministic resolution if fallback search did not find it
    try:
        project_number = get_project_number(project_id)
        dataset_location = get_dataset_location(project_id, dataset_id).lower()
        entry_id = f"bigquery.googleapis.com/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}"
        full_name = f"projects/{project_number}/locations/{dataset_location}/entryGroups/@bigquery/entries/{entry_id}"
        entry_data = {
            "name": full_name,
            "project_number": project_number,
            "location": dataset_location,
            "entry_group": "@bigquery",
            "entry_id": entry_id
        }
        _CACHE_TABLE_ENTRIES[cache_key] = entry_data
        return entry_data
    except Exception as e:
        raise RuntimeError(f"Could not resolve BigQuery table entry for '{dataset_id}.{table_id}': {e}")

def list_glossary_terms_with_fallback(project_id: str, region: str, glossary_id: str) -> list:
    """
    Lists all glossary terms in the glossary using the Direct REST API.
    """
    cache_key = (project_id, region, glossary_id)
    if cache_key in _CACHE_GLOSSARY_TERMS:
        return _CACHE_GLOSSARY_TERMS[cache_key]

    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{region}/glossaries/{glossary_id}/terms?pageSize=1000"
    try:
        res = rest_api_helper(url, "GET")
        terms = res.get("terms", [])
        _CACHE_GLOSSARY_TERMS[cache_key] = terms
        return terms
    except Exception as e:
        raise RuntimeError(f"Failed to list business glossary terms: {e}")

def find_matching_term(query_term_name: str, terms: list) -> dict:
    """
    Finds a term from a list of terms by matching the display name or term ID.
    Supports flexible matching (case-insensitive, cleaning whitespace, parenthesis etc.).
    """
    # Clean the query term name
    clean_query = query_term_name.strip().lower()
    
    # 1. Try exact display name match (case-insensitive)
    for term in terms:
        display_name = term.get("displayName", "").strip().lower()
        if display_name == clean_query:
            return term
            
    # 2. Try match after removing anything in parentheses from both
    # e.g. "D2C (Direct-to-Consumer)" -> "d2c"
    def normalize_name(name):
        name_no_parens = re.sub(r'\(.*?\)', '', name)
        cleaned = "".join(c for c in name_no_parens if c.isalnum() or c.isspace())
        return " ".join(cleaned.split()).lower()
        
    normalized_query = normalize_name(clean_query)
    if normalized_query:
        for term in terms:
            display_name = term.get("displayName", "")
            if normalize_name(display_name) == normalized_query:
                return term
                
    # 3. Try match term ID (last part of name path)
    def slugify(text):
        slug = text.lower()
        slug = re.sub(r'[^a-z0-9\-]', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')
        
    query_slug = slugify(clean_query)
    for term in terms:
        term_path = term.get("name", "")
        term_id = term_path.split("/")[-1].lower()
        if term_id == query_slug:
            return term
            
    # 4. Try matching substring
    for term in terms:
        display_name = term.get("displayName", "").lower()
        if clean_query in display_name or display_name in clean_query:
            return term
            
    return None

def resolve_or_create_term_entry(
    project_id: str,
    glossary_region: str,
    glossary_id: str,
    term_name_or_id: str,
    auto_create: bool = True
) -> dict:
    """
    Resolves a business glossary term's full entry resource path in Knowledge Catalog.
    If it doesn't exist and auto_create is True, creates it under the glossary.
    """
    try:
        project_number = get_project_number(project_id)
    except Exception:
        project_number = None

    # 0. Check local OKF glossary terms index first (Fast path - 0 network calls)
    try:
        okf_terms = load_okf_glossary_terms(project_id=project_id)
        candidates = [
            term_name_or_id.lower().strip(),
            term_name_or_id.lower().replace("_", "-").strip(),
            term_name_or_id.lower().replace("-", "_").strip()
        ]
        s_no_parens = re.sub(r'\(.*?\)', '', term_name_or_id)
        norm_cand = " ".join("".join(c for c in s_no_parens if c.isalnum() or c.isspace()).split()).lower()
        if norm_cand:
            candidates.append(norm_cand)
        s_slug = re.sub(r'-+', '-', re.sub(r'[^a-z0-9\-]', '-', term_name_or_id.lower())).strip('-')
        if s_slug:
            candidates.append(s_slug)

        for c in candidates:
            if c in okf_terms:
                return dict(okf_terms[c])
    except Exception:
        pass

    # 1. Fetch terms to see if we can find a match
    try:
        terms = list_glossary_terms_with_fallback(project_id, glossary_region, glossary_id)
    except Exception as e:
        terms = []
        
    matched_term = find_matching_term(term_name_or_id, terms)
    
    if matched_term:
        term_path = matched_term.get("name")
        # Extract projects/{TERM_PROJECT_NUMBER}/locations/{TERM_LOCATION_ID}/glossaries/{TERM_GLOSSARY_ID}/terms/{TERM_ID}
        # Wait, the target name inside entryLinks needs to be the entry's Knowledge Catalog path:
        # "projects/{TERM_PROJECT_NUMBER}/locations/{TERM_LOCATION_ID}/entryGroups/@dataplex/entries/projects/{TERM_PROJECT_NUMBER}/locations/{TERM_LOCATION_ID}/glossaries/{TERM_GLOSSARY_ID}/terms/{TERM_ID}"
        parts = term_path.split("/")
        term_project_num = project_number if project_number else parts[1]
        term_loc = parts[3]
        term_glossary_id = parts[5]
        term_id = parts[7]
        
        target_name = f"projects/{term_project_num}/locations/{term_loc}/entryGroups/@dataplex/entries/projects/{term_project_num}/locations/{term_loc}/glossaries/{term_glossary_id}/terms/{term_id}"
        return {
            "name": target_name,
            "term_id": term_id,
            "display_name": matched_term.get("displayName"),
            "glossary_id": term_glossary_id,
            "location": term_loc,
            "project_number": term_project_num
        }
        
    if not auto_create:
        raise ValueError(f"Term '{term_name_or_id}' not found in business glossary '{glossary_id}' and auto_create is False.")
        
    # 2. Auto-create the term
    def slugify(text):
        slug = text.lower()
        slug = re.sub(r'[^a-z0-9\-]', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')
        
    term_id = slugify(term_name_or_id)
    display_name = term_name_or_id
    
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{glossary_region}/glossaries/{glossary_id}/terms?termId={term_id}"
    parent_resource = f"projects/{project_id}/locations/{glossary_region}/glossaries/{glossary_id}"
    
    request_body = {
        "displayName": display_name,
        "description": f"Automatically created during linkage of term '{display_name}'.",
        "parent": parent_resource
    }
    
    try:
        new_term = rest_api_helper(url, "POST", request_body)
        _CACHE_GLOSSARY_TERMS.clear()
        term_path = new_term.get("name")
        parts = term_path.split("/")
        term_project_num = project_number if project_number else parts[1]
        term_loc = parts[3]
        term_glossary_id = parts[5]
        term_id = parts[7]
        
        target_name = f"projects/{term_project_num}/locations/{term_loc}/entryGroups/@dataplex/entries/projects/{term_project_num}/locations/{term_loc}/glossaries/{term_glossary_id}/terms/{term_id}"
        return {
            "name": target_name,
            "term_id": term_id,
            "display_name": display_name,
            "glossary_id": term_glossary_id,
            "location": term_loc,
            "project_number": term_project_num
        }
    except Exception as e:
        raise RuntimeError(f"Failed to auto-create term '{term_name_or_id}': {e}")

def make_entry_link_id(table_id: str, term_id: str, column_name: str = None) -> str:
    """
    Generates a unique, sanitized entry link ID matching Dataplex constraints:
    - 1 to 63 characters
    - Only lowercase letters, numbers, and hyphens
    - Starts with a letter
    - Ends with a letter or number
    """
    parts = [table_id]
    if column_name:
        parts.append(column_name)
    parts.append(term_id)
    
    raw_id = "-".join(parts).lower()
    
    sanitized = ""
    for char in raw_id:
        if char.isalnum() or char == '-':
            sanitized += char
        else:
            sanitized += '-'
            
    sanitized = re.sub(r'-+', '-', sanitized).strip('-')
    
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'l-' + sanitized
        
    sanitized = sanitized[:63].rstrip('-')
    return sanitized

def link_term_to_table_or_column(
    project_id: str = None,
    dataset_id: str = None,
    table_id: str = None,
    term_name_or_id: str = None,
    column_name: str = None,
    auto_create_term: bool = True,
    resource: str = None
) -> dict:
    """
    Creates an entry link in Dataplex connecting a Business Glossary term to a BigQuery table or column.
    """
    messages = []
    
    try:
        # If resource URL is provided, parse IDs if needed
        if resource:
            m = re.search(r'/projects/([^/]+)/datasets/([^/]+)/tables/([^/]+)', resource)
            if m:
                project_id = project_id or m.group(1)
                dataset_id = dataset_id or m.group(2)
                table_id = table_id or m.group(3)

        # Load environment defaults if parameters not provided
        env = load_env_config()
        project_id = project_id or env.get("gcp-project-id")
        dataset_id = dataset_id or env.get("bigquery-dataset")
        
        # Discover glossary ID and location
        glossary_id, glossary_region = find_active_glossary(project_id, env.get("business-glossary-region-clean", "us"))
        if not glossary_id:
            glossary_id = env.get("business-glossary-id-clean", "l400-agentic-da")
            glossary_region = env.get("business-glossary-region-clean", "us")
            messages.append(f"No active glossary found, using defaults: glossary_id={glossary_id}, region={glossary_region}")
        else:
            messages.append(f"Successfully discovered active glossary: '{glossary_id}' in region '{glossary_region}'")
            
        # 1. Resolve table entry
        messages.append(f"Resolving Knowledge Catalog entry for table '{dataset_id}.{table_id}'...")
        table_entry = resolve_table_entry(project_id, dataset_id, table_id, resource=resource)
        messages.append(f"Resolved table entry path: {table_entry['name']}")
        
        # 2. Resolve term entry
        messages.append(f"Resolving Business Glossary term entry for '{term_name_or_id}'...")
        term_entry = resolve_or_create_term_entry(project_id, glossary_region, glossary_id, term_name_or_id, auto_create_term)
        messages.append(f"Resolved term entry path: {term_entry['name']}")
        
        # 3. Create entry link ID
        entry_link_id = make_entry_link_id(table_id, term_entry["term_id"], column_name)
        messages.append(f"Generated entry link ID: '{entry_link_id}'")
        
        # 4. Create entry link directly (fast path - avoids redundant GET check)
        messages.append(f"Creating entry link '{entry_link_id}'...")
        create_url = f"https://dataplex.googleapis.com/v1/projects/{table_entry['project_number']}/locations/{table_entry['location']}/entryGroups/{table_entry['entry_group']}/entryLinks?entryLinkId={entry_link_id}"
        
        source_ref = {
            "name": table_entry["name"],
            "type": "SOURCE"
        }
        if column_name:
            source_ref["path"] = f"Schema.{column_name}"
            
        target_ref = {
            "name": term_entry["name"],
            "type": "TARGET"
        }
        
        request_body = {
            "entryLinkType": "projects/dataplex-types/locations/global/entryLinkTypes/definition",
            "entryReferences": [source_ref, target_ref]
        }
        
        json_result = rest_api_helper(create_url, "POST", request_body)
        messages.append("Successfully linked term to resource in Dataplex Knowledge Catalog.")
        
        return {
            "status": "success",
            "tool_name": "link_term_to_table_or_column",
            "messages": messages,
            "results": {
                "entry_link_id": entry_link_id,
                "already_existed": False,
                "source": table_entry["name"],
                "target": term_entry["name"],
                "api_response": json_result
            }
        }
        
    except Exception as e:
        err_msg = str(e)
        if "ALREADY_EXISTS" in err_msg or "already exists" in err_msg or "409" in err_msg:
            messages.append("Entry link already exists between these resources. Skipping link creation.")
            return {
                "status": "success",
                "tool_name": "link_term_to_table_or_column",
                "messages": messages,
                "results": {
                    "entry_link_id": entry_link_id,
                    "already_existed": True,
                    "source": table_entry["name"],
                    "target": term_entry["name"]
                }
            }
        messages.append(f"Failed to link term: {e}")
        return {
            "status": "failed",
            "tool_name": "link_term_to_table_or_column",
            "messages": messages,
            "results": None
        }

def remove_term_link(
    project_id: str = None,
    dataset_id: str = None,
    table_id: str = None,
    term_name_or_id: str = None,
    column_name: str = None,
    resource: str = None
) -> dict:
    """
    Deletes an entry link connecting a Business Glossary term to a BigQuery table or column.
    """
    messages = []
    try:
        # If resource URL is provided, parse IDs if needed
        if resource:
            m = re.search(r'/projects/([^/]+)/datasets/([^/]+)/tables/([^/]+)', resource)
            if m:
                project_id = project_id or m.group(1)
                dataset_id = dataset_id or m.group(2)
                table_id = table_id or m.group(3)

        env = load_env_config()
        project_id = project_id or env.get("gcp-project-id")
        dataset_id = dataset_id or env.get("bigquery-dataset")
        
        glossary_id, glossary_region = find_active_glossary(project_id, env.get("business-glossary-region-clean", "us"))
        if not glossary_id:
            glossary_id = env.get("business-glossary-id-clean", "l400-agentic-da")
            glossary_region = env.get("business-glossary-region-clean", "us")
            
        table_entry = resolve_table_entry(project_id, dataset_id, table_id, resource=resource)
        term_entry = resolve_or_create_term_entry(project_id, glossary_region, glossary_id, term_name_or_id, auto_create=False)
        entry_link_id = make_entry_link_id(table_id, term_entry["term_id"], column_name)
        
        messages.append(f"Deleting entry link '{entry_link_id}'...")
        url = f"https://dataplex.googleapis.com/v1/projects/{table_entry['project_number']}/locations/{table_entry['location']}/entryGroups/{table_entry['entry_group']}/entryLinks/{entry_link_id}"
        
        rest_api_helper(url, "DELETE")
        messages.append("Successfully deleted entry link from Dataplex Knowledge Catalog.")
        return {
            "status": "success",
            "tool_name": "remove_term_link",
            "messages": messages,
            "results": {
                "entry_link_id": entry_link_id,
                "deleted": True
            }
        }
    except Exception as e:
        messages.append(f"Failed to delete entry link: {e}")
        return {
            "status": "failed",
            "tool_name": "remove_term_link",
            "messages": messages,
            "results": None
        }

def parse_markdown_mappings(file_path: str) -> list:
    """
    Parses table and column glossary term mappings from a markdown file.
    """
    mappings = []
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Markdown mapping file not found at: '{file_path}'")
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.split('\n')
    current_table_fq = None
    current_level = None # "table" or "column"
    
    for line_num, line in enumerate(lines, 1):
        line_strip = line.strip()
        if not line_strip:
            continue
            
        # Match table declaration
        table_match = re.search(r'###\s+Table:\s*`?([^`\s]+)`?', line)
        if table_match:
            current_table_fq = table_match.group(1).strip("` ")
            current_level = None
            continue
            
        if current_table_fq:
            # Check for level headers
            if "Table-Level Terms" in line:
                current_level = "table"
                continue
            elif "Column-Level Terms" in line:
                current_level = "column"
                continue
                
            # Parse bullet points under the active level
            if line_strip.startswith('*') or line_strip.startswith('-'):
                if current_level == "table":
                    term_match = re.search(r'\*\*(.*?)\*\*', line_strip)
                    if term_match:
                        term_name = term_match.group(1).strip().rstrip(':')
                        if term_name:
                            mappings.append({
                                "table_fq": current_table_fq,
                                "column_name": None,
                                "term_name": term_name,
                                "line_num": line_num
                            })
                elif current_level == "column":
                    col_match = re.search(r'`([^`]+)`', line_strip)
                    if col_match:
                        column_name = col_match.group(1).strip()
                        bold_terms = re.findall(r'\*\*(.*?)\*\*', line_strip)
                        for term in bold_terms:
                            term_name = term.strip().rstrip(':')
                            if term_name:
                                mappings.append({
                                    "table_fq": current_table_fq,
                                    "column_name": column_name,
                                    "term_name": term_name,
                                    "line_num": line_num
                                })
                                
    return mappings

def batch_link_from_markdown(markdown_file_path: str, project_id: str = None) -> dict:
    """
    Parses a markdown mapping file and links all terms in batch.
    """
    messages = []
    successes = []
    failures = []
    
    try:
        env = load_env_config()
        project_id = project_id or env.get("gcp-project-id")
        
        messages.append(f"Parsing markdown mappings from '{markdown_file_path}'...")
        mappings = parse_markdown_mappings(markdown_file_path)
        messages.append(f"Found {len(mappings)} mappings to process.")
        
        for item in mappings:
            table_fq = item["table_fq"]
            column_name = item["column_name"]
            term_name = item["term_name"]
            line_num = item["line_num"]
            
            # Split table FQ (e.g. l400_agentic_da.CUST_MSTR_D2C)
            parts = table_fq.split('.')
            if len(parts) == 2:
                dataset_id = parts[0]
                table_id = parts[1]
            elif len(parts) == 1:
                dataset_id = env.get("bigquery-dataset")
                table_id = parts[0]
            else:
                dataset_id = parts[-2]
                table_id = parts[-1]
                
            col_msg = f"column '{column_name}'" if column_name else "table level"
            messages.append(f"Processing mapping (line {line_num}): table={dataset_id}.{table_id}, target={col_msg}, term='{term_name}'")
            
            res = link_term_to_table_or_column(
                project_id=project_id,
                dataset_id=dataset_id,
                table_id=table_id,
                term_name_or_id=term_name,
                column_name=column_name,
                auto_create_term=True
            )
            
            if res["status"] == "success":
                successes.append({
                    "table": f"{dataset_id}.{table_id}",
                    "column": column_name,
                    "term": term_name,
                    "entry_link_id": res["results"]["entry_link_id"],
                    "already_existed": res["results"]["already_existed"]
                })
            else:
                failures.append({
                    "table": f"{dataset_id}.{table_id}",
                    "column": column_name,
                    "term": term_name,
                    "error": res["messages"][-1] if res["messages"] else "Unknown error"
                })
                
        messages.append(f"Batch execution complete: {len(successes)} succeeded, {len(failures)} failed.")
        return {
            "status": "success" if not failures else "partial_failure",
            "tool_name": "batch_link_from_markdown",
            "messages": messages,
            "results": {
                "success_count": len(successes),
                "failure_count": len(failures),
                "successes": successes,
                "failures": failures
            }
        }
    except Exception as e:
        messages.append(f"Batch execution failed with critical system error: {e}")
        return {
            "status": "failed",
            "tool_name": "batch_link_from_markdown",
            "messages": messages,
            "results": None
        }

def sync_okf_to_term_links(
    okf_tables_dir: str = "okf/tables",
    project_id: str = None
) -> dict:
    """
    Reads local OKF table references under okf_tables_dir, parses their table-level
    and column-level terms, and synchronizes them to Dataplex / Knowledge Engine.
    """
    messages = []
    successes = []
    failures = []
    
    try:
        # Load environment config
        env = load_env_config()
        project_id = project_id or env.get("gcp-project-id")
        dataset_id = env.get("bigquery-dataset")
        
        # Discover glossary ID and location
        glossary_id, glossary_region = find_active_glossary(project_id, env.get("business-glossary-region-clean", "us"))
        if not glossary_id:
            glossary_id = env.get("business-glossary-id-clean", "l400-agentic-da")
            glossary_region = env.get("business-glossary-region-clean", "us")
            messages.append(f"No active glossary found, using defaults: glossary_id={glossary_id}, region={glossary_region}")
        else:
            messages.append(f"Successfully discovered active glossary: '{glossary_id}' in region '{glossary_region}'")
            
        # Check absolute paths
        if not os.path.isabs(okf_tables_dir):
            okf_tables_dir = os.path.abspath(okf_tables_dir)
            
        if not os.path.exists(okf_tables_dir):
            messages.append(f"Error: OKF tables directory not found at '{okf_tables_dir}'.")
            return {
                "status": "failed",
                "tool_name": "sync_okf_to_term_links",
                "messages": messages,
                "results": None
            }
            
        okf_files = [f for f in os.listdir(okf_tables_dir) if f.endswith(".md") and f != "index.md"]
        messages.append(f"Found {len(okf_files)} OKF table files in '{okf_tables_dir}'.")
        
        for file_name in okf_files:
            file_path = os.path.join(okf_tables_dir, file_name)
            messages.append(f"Processing OKF file: {file_name}")
            
            with open(file_path, "r", encoding="utf-8") as f_in:
                file_content = f_in.read()
                
            parts = file_content.split("---", 2)
            if len(parts) < 3:
                messages.append(f"Warning: File {file_name} does not match standard OKF table reference format. Skipping.")
                continue
                
            # Parse YAML frontmatter
            yaml_block = parts[1].strip()
            body_block = parts[2]
            
            yaml_lines = yaml_block.splitlines()
            table_title = None
            table_terms = []
            table_resource = None
            in_terms_list = False
            
            for line in yaml_lines:
                line_str = line.strip()
                if line_str.startswith("-") and in_terms_list:
                    term_val = line_str.strip("-").strip().strip("'\"")
                    if term_val:
                        table_terms.append(term_val)
                    continue
                else:
                    in_terms_list = False
                    
                if ":" in line_str:
                    k, v = line_str.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip().strip("'\"")
                    if k == "title":
                        table_title = v
                    elif k == "resource":
                        table_resource = v
                    elif k == "terms":
                        in_terms_list = True
                        if v and v != "None":
                            term_val = v.strip().strip("[]").strip()
                            if term_val:
                                table_terms.append(term_val)

            file_project_id = project_id
            file_dataset_id = dataset_id
            file_table_id = None

            if table_resource:
                m = re.search(r'/projects/([^/]+)/datasets/([^/]+)/tables/([^/]+)', table_resource)
                if m:
                    file_project_id = m.group(1)
                    file_dataset_id = m.group(2)
                    file_table_id = m.group(3)

            if not file_table_id:
                if table_title:
                    file_table_id = table_title
                else:
                    file_table_id = os.path.splitext(file_name)[0].upper()

            display_table_name = table_title or file_table_id
            messages.append(f"Table title: {display_table_name} (resource: {table_resource or 'none'})")
            if table_terms:
                messages.append(f"Table-level terms found: {table_terms}")
                
            # Parse Schema column-level terms
            column_terms = {}
            body_lines = body_block.splitlines()
            schema_start_idx = -1
            schema_end_idx = -1
            
            for idx, line in enumerate(body_lines):
                if line.strip().startswith("# Schema"):
                    schema_start_idx = idx
                    break
                    
            if schema_start_idx != -1:
                for idx in range(schema_start_idx + 1, len(body_lines)):
                    line_str = body_lines[idx].strip()
                    if line_str.startswith("|"):
                        if schema_end_idx == -1:
                            schema_end_idx = idx
                    elif schema_end_idx != -1 and not line_str:
                        schema_end_idx = idx
                        break
                    elif schema_end_idx != -1 and line_str.startswith("#"):
                        schema_end_idx = idx
                        break
                if schema_end_idx == -1:
                    schema_end_idx = len(body_lines)
                    
            if schema_start_idx != -1 and schema_end_idx != -1:
                table_lines = body_lines[schema_start_idx+1:schema_end_idx]
                for line in table_lines:
                    line_str = line.strip()
                    if not line_str.startswith("|") or ":---" in line_str or "Field Name" in line_str:
                        continue
                        
                    row_parts = [p.strip() for p in line_str.split("|")]
                    if len(row_parts) >= 4:
                        col_name = row_parts[1].strip("`").strip()
                        terms_col_val = row_parts[3].strip()
                        
                        if terms_col_val and terms_col_val != "-":
                            # Extract term titles or slugs from links, e.g., [CLV / LTV (Customer Lifetime Value)](../references/glossary/customer_lifetime_value.md)
                            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', terms_col_val)
                            extracted_terms = []
                            if links:
                                for l_text, l_target in links:
                                    m_target = re.search(r'glossary/([^/]+)\.md', l_target)
                                    if m_target:
                                        extracted_terms.append(m_target.group(1))
                                    else:
                                        extracted_terms.append(l_text.strip())
                            else:
                                extracted_terms = [t.strip() for t in terms_col_val.split(",") if t.strip()]
                                
                            if extracted_terms:
                                column_terms[col_name] = extracted_terms
                                
            if column_terms:
                messages.append(f"Column-level terms found: {column_terms}")
                
            # Perform Linkage Update
            # 1. Link table-level terms
            for term in table_terms:
                messages.append(f"Linking table-level term '{term}' to table '{file_table_id}'...")
                res = link_term_to_table_or_column(
                    project_id=file_project_id,
                    dataset_id=file_dataset_id,
                    table_id=file_table_id,
                    term_name_or_id=term,
                    column_name=None,
                    auto_create_term=True,
                    resource=table_resource
                )
                if res["status"] == "success":
                    successes.append({
                        "table": file_table_id,
                        "column": None,
                        "term": term,
                        "entry_link_id": res["results"]["entry_link_id"]
                    })
                else:
                    failures.append({
                        "table": file_table_id,
                        "column": None,
                        "term": term,
                        "error": res["messages"][-1] if res["messages"] else "Unknown error"
                    })
                    
            # 2. Link column-level terms
            for col_name, terms_list in column_terms.items():
                for term in terms_list:
                    messages.append(f"Linking column term '{term}' to column '{col_name}' on table '{file_table_id}'...")
                    res = link_term_to_table_or_column(
                        project_id=file_project_id,
                        dataset_id=file_dataset_id,
                        table_id=file_table_id,
                        term_name_or_id=term,
                        column_name=col_name,
                        auto_create_term=True,
                        resource=table_resource
                    )
                    if res["status"] == "success":
                        successes.append({
                            "table": file_table_id,
                            "column": col_name,
                            "term": term,
                            "entry_link_id": res["results"]["entry_link_id"]
                        })
                    else:
                        failures.append({
                            "table": file_table_id,
                            "column": col_name,
                            "term": term,
                            "error": res["messages"][-1] if res["messages"] else "Unknown error"
                        })
                        
        messages.append(f"OKF direct synchronization complete: {len(successes)} entry links succeeded, {len(failures)} failed.")
        return {
            "status": "success" if not failures else "partial_failure",
            "tool_name": "sync_okf_to_term_links",
            "messages": messages,
            "results": {
                "success_count": len(successes),
                "failure_count": len(failures),
                "successes": successes,
                "failures": failures
            }
        }
        
    except Exception as e:
        messages.append(f"Critical error during direct OKF term synchronization: {e}")
        return {
            "status": "failed",
            "tool_name": "sync_okf_to_term_links",
            "messages": messages,
            "results": None
        }
