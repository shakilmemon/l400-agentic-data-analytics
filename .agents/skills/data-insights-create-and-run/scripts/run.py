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
    resp = e.response
    status_code = resp.status_code if resp is not None else 'N/A'
    resp_text = resp.text if resp is not None else 'N/A'
    req_url = e.request.url if e.request is not None else 'N/A'
    error_message = f"Error rest_api_helper -> HTTP Status: {status_code}, Text: {resp_text}, Request URL: {req_url}"
    raise RuntimeError(error_message)
  except requests.exceptions.RequestException as e:
    error_message = f"Error rest_api_helper -> Request Error Type: {type(e).__name__}, Message: {str(e)}, Request URL: {e.request.url if hasattr(e, 'request') and e.request else 'N/A'}"
    raise RuntimeError(error_message)
  except Exception as e:
    error_message = f"An unexpected error occurred in rest_api_helper: {e}"
    raise RuntimeError(error_message)


def get_data_insight_scan(project_id: str, dataplex_region: str, data_insight_scan_name: str) -> dict:
    """
    Retrieves a Dataplex data insight scan directly by scan ID.
    """
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/dataScans/{data_insight_scan_name}?view=BASIC"
    try:
        return rest_api_helper(url, "GET", None)
    except Exception:
        return None


def exists_data_insight_scan(project_id: str, dataplex_region: str, data_insight_scan_name: str) -> bool:
    """
    Checks if a Dataplex data insight scan already exists by directly probing the scan ID.
    """
    try:
        scan = get_data_insight_scan(project_id, dataplex_region, data_insight_scan_name)
        return scan is not None
    except Exception as e:
        raise RuntimeError(f"Error checking if data insight scan exists: {e}")


def create_data_insight_scan(project_id: str, dataplex_region: str, data_insight_scan_name: str, data_insight_display_name: str, bigquery_dataset_name: str, bigquery_table_name: str = None) -> dict:
    """
    Creates a new Dataplex data insight scan if it does not already exist. Can target a dataset or a table.
    """
    if exists_data_insight_scan(project_id, dataplex_region, data_insight_scan_name):
        full_scan_name = f"projects/{project_id}/locations/{dataplex_region}/dataScans/{data_insight_scan_name}"
        return {"name": full_scan_name, "created": False}

    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/dataScans?dataScanId={data_insight_scan_name}"
    
    if bigquery_table_name:
        bigquery_resource_path = f"//bigquery.googleapis.com/projects/{project_id}/datasets/{bigquery_dataset_name}/tables/{bigquery_table_name}"
    else:
        bigquery_resource_path = f"//bigquery.googleapis.com/projects/{project_id}/datasets/{bigquery_dataset_name}"

    request_body = {
        "displayName": data_insight_display_name,
        "type": "DATA_DOCUMENTATION",
        "dataDocumentationSpec": {},
        "data": {"resource": bigquery_resource_path}
    }

    try:
        json_result = rest_api_helper(url, "POST", request_body)
        return json_result
    except Exception as e:
        raise RuntimeError(f"Error creating data insight scan: {e}")


def start_data_insight_scan(project_id: str, dataplex_region: str, data_insight_scan_name: str) -> dict:
    """
    Triggers a run of an existing Dataplex data insight scan.
    """
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/dataScans/{data_insight_scan_name}:run"
    try:
        json_result = rest_api_helper(url, "POST", {})
        return json_result
    except Exception as e:
        raise RuntimeError(f"Error starting data insight scan: {e}")


def get_data_insight_scan_state(data_insight_scan_job_name: str) -> dict:
    """
    Gets the current state of a running data insight scan job.
    """
    url = f"https://dataplex.googleapis.com/v1/{data_insight_scan_job_name}"
    try:
        json_result = rest_api_helper(url, "GET", None)
        return json_result
    except Exception as e:
        raise RuntimeError(f"Error getting data insight scan job state: {e}")


def update_bigquery_resource_dataplex_labels(project_id: str, dataplex_region: str, dataplex_scan_name: str, bigquery_dataset_name: str, bigquery_table_name: str = None) -> dict:
    """
    Updates a BigQuery resource's (table or dataset) labels to link it to a Dataplex data insight scan.
    """
    if bigquery_table_name:
        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{bigquery_dataset_name}/tables/{bigquery_table_name}"
    else:
        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{bigquery_dataset_name}"

    request_body = {
        "labels": {
            "dataplex-data-documentation-published-project": project_id,
            "dataplex-data-documentation-published-location": dataplex_region,
            "dataplex-data-documentation-published-scan": dataplex_scan_name,
        }
    }
    try:
        json_result = rest_api_helper(url, "PATCH", request_body)
        return json_result
    except Exception as e:
        raise RuntimeError(f"Error updating BigQuery resource labels for insights: {e}")


def create_and_run_data_insight_scan_workflow(project_id: str, dataplex_region: str, data_insight_scan_name: str, data_insight_display_name: str, bigquery_dataset_name: str, bigquery_table_name: str = None) -> dict:
    """
    Orchestrates the creation, execution, and linking of a Dataplex Data Insight scan synchronously.
    Works for datasets, tables, or both.
    """
    messages = []
    results = {
        "data_insight_scan_name": data_insight_scan_name,
        "data_insight_display_name": data_insight_display_name,
        "bigquery_dataset_name": bigquery_dataset_name,
        "bigquery_table_name": bigquery_table_name,
        "data_insight_scan_job_name": None,
        "data_insight_scan_job_state": None,
    }

    try:
        def log(msg):
            messages.append(msg)
            print(msg, flush=True)

        # Step 1: Create scan definition
        log(f"Step 1/5: Checking/creating scan definition '{data_insight_scan_name}'...")
        create_result = create_data_insight_scan(project_id, dataplex_region, data_insight_scan_name, data_insight_display_name, bigquery_dataset_name, bigquery_table_name)
        log("Successfully checked/created data insight scan definition.")

        # Step 2: Wait for Registration and ACTIVE status
        log("Step 2/5: Polling to verify scan registration and ACTIVE state...")
        is_active = False
        for attempt in range(60):
            scan_obj = get_data_insight_scan(project_id, dataplex_region, data_insight_scan_name)
            if scan_obj and scan_obj.get("state") == "ACTIVE":
                is_active = True
                break
            current_state = scan_obj.get("state") if scan_obj else "NOT_FOUND"
            log(f"Scan not active yet (state: {current_state}). Waiting 5 seconds (attempt {attempt+1}/60)...")
            time.sleep(5)
        if not is_active:
            raise RuntimeError(f"Data insight scan '{data_insight_scan_name}' did not become ACTIVE in time.")
        log(f"Data insight scan '{data_insight_scan_name}' is ACTIVE.")

        # Step 3: Run the Scan Job (with robust handling for registration propagation latency)
        log("Step 3/5: Starting or attaching to data insight scan job...")
        job_name = None
        try:
            jobs_url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{dataplex_region}/dataScans/{data_insight_scan_name}/jobs"
            jobs_res = rest_api_helper(jobs_url, "GET", None)
            for j in jobs_res.get("dataScanJobs", []):
                if j.get("state") in ["PENDING", "RUNNING"]:
                    job_name = j.get("name")
                    log(f"Found existing active/pending job: '{job_name}'")
                    break
        except Exception as e:
            log(f"Could not check existing jobs: {e}")

        if not job_name:
            start_result = None
            for attempt in range(10):
                try:
                    start_result = start_data_insight_scan(project_id, dataplex_region, data_insight_scan_name)
                    break
                except Exception as e:
                    if attempt == 9:
                        raise
                    log(f"Start scan job failed transiently: {e}. Retrying in 5 seconds (attempt {attempt+1}/10)...")
                    time.sleep(5)
            job_info = start_result.get("job", {})
            job_name = job_info.get("name")
            if not job_name:
                raise RuntimeError(f"Failed to retrieve job name from start result.")
            log(f"Started job: '{job_name}'")

        results["data_insight_scan_job_name"] = job_name

        # Step 4: Monitor completion
        log("Step 4/5: Monitoring job execution...")
        completed = False
        final_state = "UNKNOWN"
        for attempt in range(360):
            job_status = get_data_insight_scan_state(job_name)
            current_state = job_status.get("state", "UNKNOWN")
            log(f"Job state: {current_state} (attempt {attempt+1}/360)")
            if current_state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
                completed = True
                final_state = current_state
                break
            time.sleep(5)
        if not completed:
            raise RuntimeError(f"Job '{job_name}' did not complete in time.")
        if final_state != "SUCCEEDED":
            raise RuntimeError(f"Job '{job_name}' completed with non-success state: {final_state}")
        results["data_insight_scan_job_state"] = final_state

        # Step 5: Link the Scan to BigQuery labels
        log("Step 5/5: Linking data insight scan to BigQuery labels...")
        link_result = update_bigquery_resource_dataplex_labels(project_id, dataplex_region, data_insight_scan_name, bigquery_dataset_name, bigquery_table_name)
        log("Successfully linked data insight scan to BigQuery labels.")

        return {
            "status": "success",
            "messages": messages,
            "results": results
        }
    except Exception as e:
        log_err = f"Workflow failed: {e}"
        messages.append(log_err)
        print(log_err, flush=True)
        return {
            "status": "failed",
            "messages": messages,
            "results": results
        }
