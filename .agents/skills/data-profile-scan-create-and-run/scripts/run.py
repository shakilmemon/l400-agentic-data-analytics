import google.auth.transport.requests
import google.auth
import requests
import time


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
    error_message = f"Error rest_api_helper -> HTTP Status: {e.response.status_code if e.response is not None else 'N/A'}, Text: {e.response.text if e.response is not None else 'N/A'}, Request URL: {e.request.url if e.request else 'N/A'}"
    raise RuntimeError(error_message)
  except requests.exceptions.RequestException as e:
    error_message = f"Error rest_api_helper -> Request Error Type: {type(e).__name__}, Message: {str(e)}, Request URL: {e.request.url if hasattr(e, 'request') and e.request else 'N/A'}"
    raise RuntimeError(error_message)
  except Exception as e:
    error_message = f"An unexpected error occurred in rest_api_helper: {e}"
    raise RuntimeError(error_message)


def get_data_profile_scan(project_id: str, dataplex_region: str, data_profile_scan_name: str) -> dict:
    """
    Directly retrieves a Dataplex data profile scan by scan ID.
    Returns the scan dict if found, or None if not found (404).
    """
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/dataScans/{data_profile_scan_name}?view=BASIC"
    try:
        return rest_api_helper(url, "GET", None)
    except RuntimeError as e:
        if "HTTP Status: 404" in str(e):
            return None
        raise
    except Exception:
        return None


def exists_data_profile_scan(project_id: str, dataplex_region: str, data_profile_scan_name: str) -> bool:
    """
    Checks if a Dataplex data profile scan already exists by directly probing the scan ID.
    """
    try:
        scan = get_data_profile_scan(project_id, dataplex_region, data_profile_scan_name)
        return scan is not None
    except Exception as e:
        raise RuntimeError(f"Error checking if data profile scan exists: {e}")


def create_data_profile_scan(project_id: str, dataplex_region: str, data_profile_scan_name: str, data_profile_display_name: str, bigquery_dataset_name: str, bigquery_table_name: str) -> dict:
    """
    Creates a new Dataplex data profile scan if it does not already exist.
    """
    if exists_data_profile_scan(project_id, dataplex_region, data_profile_scan_name):
        full_scan_name = f"projects/{project_id}/locations/{dataplex_region}/dataScans/{data_profile_scan_name}"
        return {"name": full_scan_name, "created": False}

    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/dataScans?dataScanId={data_profile_scan_name}"
    bigquery_resource_path = f"//bigquery.googleapis.com/projects/{project_id}/datasets/{bigquery_dataset_name}/tables/{bigquery_table_name}"

    request_body = {
        "dataProfileSpec": {"samplingPercent": 25},
        "data": {"resource": bigquery_resource_path},
        "description": data_profile_display_name,
        "displayName": data_profile_display_name
    }

    try:
        json_result = rest_api_helper(url, "POST", request_body)
        return json_result
    except Exception as e:
        raise RuntimeError(f"Error creating data profile scan: {e}")


def start_data_profile_scan(project_id: str, dataplex_region: str, data_profile_scan_name: str) -> dict:
    """
    Triggers a run of an existing Dataplex data profile scan.
    """
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/dataScans/{data_profile_scan_name}:run"
    try:
        json_result = rest_api_helper(url, "POST", {})
        return json_result
    except Exception as e:
        raise RuntimeError(f"Error starting data profile scan: {e}")


def get_data_profile_scan_state(data_profile_scan_job_name: str) -> dict:
    """
    Gets the current state of a running data profile scan job.
    """
    url = f"https://dataplex.googleapis.com/v1/{data_profile_scan_job_name}"
    try:
        json_result = rest_api_helper(url, "GET", None)
        return json_result
    except Exception as e:
        raise RuntimeError(f"Error getting data profile scan job state: {e}")


def update_bigquery_table_dataplex_labels(project_id: str, dataplex_region: str, dataplex_scan_name: str, bigquery_dataset_name: str, bigquery_table_name: str) -> dict:
    """
    Updates a BigQuery table's labels to link it to a Dataplex data profile scan.
    """
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{bigquery_dataset_name}/tables/{bigquery_table_name}"
    request_body = {
        "labels": {
            "dataplex-dp-published-project": project_id,
            "dataplex-dp-published-location": dataplex_region,
            "dataplex-dp-published-scan": dataplex_scan_name,
        }
    }
    try:
        json_result = rest_api_helper(url, "PATCH", request_body)
        return json_result
    except Exception as e:
        raise RuntimeError(f"Error updating BigQuery table labels: {e}")


def create_and_run_data_profile_scan_workflow(project_id: str, dataplex_region: str, data_profile_scan_name: str, data_profile_display_name: str, bigquery_dataset_name: str, bigquery_table_name: str) -> dict:
    """
    Orchestrates the creation, execution, and linking of a Dataplex Data Profile scan synchronously.
    """
    messages = []
    results = {
        "data_profile_scan_name": data_profile_scan_name,
        "data_profile_display_name": data_profile_display_name,
        "bigquery_dataset_name": bigquery_dataset_name,
        "bigquery_table_name": bigquery_table_name,
        "data_profile_scan_job_name": None,
        "data_profile_scan_job_state": None,
    }

    try:
        # Step 1: Create scan definition
        messages.append(f"Step 1/5: Checking/creating scan definition '{data_profile_scan_name}'...")
        create_result = create_data_profile_scan(project_id, dataplex_region, data_profile_scan_name, data_profile_display_name, bigquery_dataset_name, bigquery_table_name)
        messages.append(f"Successfully checked/created data profile scan definition.")

        # Step 2: Wait for Registration
        messages.append(f"Step 2/5: Polling to verify scan registration...")
        registered = False
        for attempt in range(10):
            if exists_data_profile_scan(project_id, dataplex_region, data_profile_scan_name):
                registered = True
                break
            messages.append(f"Scan not registered yet. Waiting 2 seconds (attempt {attempt+1}/10)...")
            time.sleep(2)
        if not registered:
            raise RuntimeError(f"Data profile scan '{data_profile_scan_name}' did not register in time.")
        messages.append(f"Data profile scan '{data_profile_scan_name}' is registered.")

        # Step 3: Run the Scan Job
        messages.append(f"Step 3/5: Starting the data profile scan job...")
        start_result = None
        for attempt in range(5):
            try:
                start_result = start_data_profile_scan(project_id, dataplex_region, data_profile_scan_name)
                break
            except Exception as e:
                if attempt == 4:
                    raise
                messages.append(f"Start scan job failed transiently: {e}. Retrying in 5 seconds (attempt {attempt+1}/5)...")
                time.sleep(5)
        job_info = start_result.get("job", {})
        job_name = job_info.get("name")
        if not job_name:
            raise RuntimeError(f"Failed to retrieve job name from start result.")
        results["data_profile_scan_job_name"] = job_name
        messages.append(f"Started job: '{job_name}'")

        # Step 4: Monitor completion
        messages.append(f"Step 4/5: Monitoring job execution...")
        completed = False
        final_state = "UNKNOWN"
        for attempt in range(50):
            job_status = get_data_profile_scan_state(job_name)
            current_state = job_status.get("state", "UNKNOWN")
            messages.append(f"Job state: {current_state} (attempt {attempt+1}/50)")
            if current_state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
                completed = True
                final_state = current_state
                break
            time.sleep(5)
        if not completed:
            raise RuntimeError(f"Job '{job_name}' did not complete in time.")
        if final_state != "SUCCEEDED":
            raise RuntimeError(f"Job '{job_name}' completed with non-success state: {final_state}")
        results["data_profile_scan_job_state"] = final_state

        # Step 5: Link the Scan to BigQuery labels
        messages.append(f"Step 5/5: Linking data profile scan to BigQuery labels...")
        link_result = update_bigquery_table_dataplex_labels(project_id, dataplex_region, data_profile_scan_name, bigquery_dataset_name, bigquery_table_name)
        messages.append("Successfully linked data profile scan to BigQuery labels.")

        return {
            "status": "success",
            "messages": messages,
            "results": results
        }
    except Exception as e:
        messages.append(f"Workflow failed: {e}")
        return {
            "status": "failed",
            "messages": messages,
            "results": results
        }
