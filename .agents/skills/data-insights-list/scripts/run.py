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
    error_message = f"Error rest_api_helper -> HTTP Status: {e.response.status_code if e.response else 'N/A'}, Text: {e.response.text if e.response else 'N/A'}, Request URL: {e.request.url if e.request else 'N/A'}"
    raise RuntimeError(error_message)
  except requests.exceptions.RequestException as e:
    error_message = f"Error rest_api_helper -> Request Error Type: {type(e).__name__}, Message: {str(e)}, Request URL: {e.request.url if hasattr(e, 'request') and e.request else 'N/A'}"
    raise RuntimeError(error_message)
  except Exception as e:
    error_message = f"An unexpected error occurred in rest_api_helper: {e}"
    raise RuntimeError(error_message)


def get_data_insight_scans(project_id: str, dataplex_region: str) -> dict: 
    """
    Lists all Dataplex data insight scans in the configured region.

    This function specifically filters the results to include only scans of
    type 'DATA_DOCUMENTATION'.
    """
    # The URL to list all data scans in the specified project and region.
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/dataScans"

    json_result = rest_api_helper(url, "GET", None)
    all_scans = json_result.get("dataScans", [])
    
    # Filter for Data Insights scans, which have the type 'DATA_DOCUMENTATION'
    insight_scans_only = [
        scan for scan in all_scans if scan.get("type") == "DATA_DOCUMENTATION"
    ]

    return {"dataScans": insight_scans_only}


def get_data_insight_scan(project_id: str, dataplex_region: str, data_insight_scan_name: str) -> dict: 
    """
    Directly retrieves a single Dataplex data insight scan by scan ID/name.
    """
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/dataScans/{data_insight_scan_name}?view=BASIC"
    try:
        return rest_api_helper(url, "GET", None)
    except Exception:
        return None


def get_data_insight_scans_for_table(project_id: str, dataplex_region: str, dataset_id: str, table_name: str) -> dict: 
    """
    Lists all Dataplex data insight scans attached to the table.

    This function specifically filters the results to include only scans of
    type 'DATA_DOCUMENTATION' and assigned to the dataset id/name and table name.
    """
    # 1. Direct probe optimization via BigQuery table labels
    try:
        bq_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_name}?view=BASIC"
        table_meta = rest_api_helper(bq_url, "GET", None)
        scan_id = table_meta.get("labels", {}).get("dataplex-data-documentation-published-scan")
        if scan_id:
            scan = get_data_insight_scan(project_id, dataplex_region, scan_id)
            if scan and scan.get("type") == "DATA_DOCUMENTATION":
                return {"dataScans": [scan]}
    except Exception:
        pass

    # 2. Fallback to listing all data scans in the specified project and region.
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/dataScans"

    json_result = rest_api_helper(url, "GET", None)
    all_scans = json_result.get("dataScans", [])

    # Filter for Data Insights scans of the given table
    insight_scans_only = []

    for item in all_scans:
        if item.get("type") == "DATA_DOCUMENTATION" and \
           item.get("data", {}).get("resource").lower() == f"//bigquery.googleapis.com/projects/{project_id}/datasets/{dataset_id}/tables/{table_name}".lower():
            insight_scans_only.append(item)
        
    return {"dataScans": insight_scans_only}


def get_data_insight_scans_for_dataset(project_id: str, dataplex_region: str, dataset_id: str) -> dict: 
    """
    Lists all Dataplex data insight scans attached directly to the dataset resource.

    This function specifically filters the results to include only scans of
    type 'DATA_DOCUMENTATION' and assigned directly to the dataset id/name (without a table).
    """
    # 1. Direct probe optimization via BigQuery dataset labels
    try:
        bq_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}"
        ds_meta = rest_api_helper(bq_url, "GET", None)
        scan_id = ds_meta.get("labels", {}).get("dataplex-data-documentation-published-scan")
        if scan_id:
            scan = get_data_insight_scan(project_id, dataplex_region, scan_id)
            if scan and scan.get("type") == "DATA_DOCUMENTATION":
                return {"dataScans": [scan]}
    except Exception:
        pass

    # 2. Fallback to listing all data scans in the specified project and region.
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/dataScans"

    json_result = rest_api_helper(url, "GET", None)
    all_scans = json_result.get("dataScans", [])

    # Filter for Data Insights scans of the given dataset
    insight_scans_only = []

    for item in all_scans:
        if item.get("type") == "DATA_DOCUMENTATION" and \
           item.get("data", {}).get("resource").lower() == f"//bigquery.googleapis.com/projects/{project_id}/datasets/{dataset_id}".lower():
            insight_scans_only.append(item)
        
    return {"dataScans": insight_scans_only}
