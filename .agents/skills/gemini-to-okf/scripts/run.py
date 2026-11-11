import os
import sys
import requests
import google.auth
import google.auth.transport.requests

def generate_okf_with_gemini(
    prompt_file_path: str,
    document_paths: list,
    output_dir: str,
    output_filename: str,
    model_name: str = "gemini-3.1-pro-preview",
    location: str = "global"
) -> dict:
    """
    Assembles a primary prompt file and a series of reference documents,
    calls the specified Gemini model on Vertex AI, and outputs the resulting
    Open Knowledge Format (OKF) markdown file into the specified directory.
    """
    messages = []
    workspace_root = os.getcwd()

    # 1. Resolve paths
    if not os.path.isabs(prompt_file_path):
        prompt_file_path = os.path.abspath(prompt_file_path)

    if not os.path.exists(prompt_file_path):
        err_msg = f"Primary prompt file not found at: '{prompt_file_path}'"
        messages.append(err_msg)
        return {
            "status": "failed",
            "tool_name": "generate_okf_with_gemini",
            "messages": messages,
            "results": None
        }

    rel_prompt_path = os.path.relpath(prompt_file_path, workspace_root)
    messages.append(f"Starting compilation of prompt '{rel_prompt_path}' and {len(document_paths)} documents...")

    # 2. Read primary prompt
    try:
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            prompt_content = f.read()
    except Exception as e:
        err_msg = f"Failed to read primary prompt file: {e}"
        messages.append(err_msg)
        return {
            "status": "failed",
            "tool_name": "generate_okf_with_gemini",
            "messages": messages,
            "results": None
        }

    # 3. Process and append documents
    combined_prompt = prompt_content

    def append_single_doc(doc_path: str) -> bool:
        nonlocal combined_prompt
        if not os.path.isabs(doc_path):
            full_doc_path = os.path.abspath(doc_path)
        else:
            full_doc_path = doc_path

        if not os.path.exists(full_doc_path):
            err_msg = f"Document context file not found at: '{doc_path}'"
            messages.append(err_msg)
            return False

        basename = os.path.basename(doc_path)
        try:
            with open(full_doc_path, "r", encoding="utf-8") as f_doc:
                doc_content = f_doc.read()
            combined_prompt += f"\n\n---\n## DOCUMENT: {basename}\n{doc_content}"
            messages.append(f"Appended document: {basename}")
            return True
        except Exception as e:
            err_msg = f"Failed to read document file '{basename}': {e}"
            messages.append(err_msg)
            return False

    for item in document_paths:
        if isinstance(item, dict) and "header" in item:
            header_title = item["header"]
            combined_prompt += f"\n\n\n# ========================================\n# CONTEXT GROUP: {header_title}\n# ========================================\n"
            messages.append(f"Added header above group: {header_title}")
            for p in item.get("paths", []):
                if not append_single_doc(p):
                    return {
                        "status": "failed",
                        "tool_name": "generate_okf_with_gemini",
                        "messages": messages,
                        "results": None
                    }
        elif isinstance(item, tuple) and len(item) == 2:
            header_title, paths = item
            combined_prompt += f"\n\n\n# ========================================\n# CONTEXT GROUP: {header_title}\n# ========================================\n"
            messages.append(f"Added header above group: {header_title}")
            for p in paths:
                if not append_single_doc(p):
                    return {
                        "status": "failed",
                        "tool_name": "generate_okf_with_gemini",
                        "messages": messages,
                        "results": None
                    }
        else:
            if not append_single_doc(item):
                return {
                    "status": "failed",
                    "tool_name": "generate_okf_with_gemini",
                    "messages": messages,
                    "results": None
                }

    # 4. Authenticate with Google Application Default Credentials
    try:
        creds, project_id = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        access_token = creds.token
    except Exception as e:
        err_msg = f"Authentication error: {e}"
        messages.append(err_msg)
        return {
            "status": "failed",
            "tool_name": "generate_okf_with_gemini",
            "messages": messages,
            "results": None
        }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    # 5. Call Vertex AI Endpoint
    if location == "global":
        url = f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/global/publishers/google/models/{model_name}:generateContent"
    else:
        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_name}:generateContent"

    generation_config = {
        "temperature": 1.0,
        "topP": 1.0,
        "maxOutputTokens": 65536,
        "candidateCount": 1,
        "responseMimeType": "text/plain",
    }

    payload = {
        "contents": {
            "role": "user",
            "parts": [
                { "text": combined_prompt }
            ]
        },
        "generation_config": generation_config,
        "safety_settings": {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_LOW_AND_ABOVE"
        }
    }

    messages.append(f"Calling model '{model_name}' in location '{location}' for project '{project_id}'...")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=300.0)
        
        if response.status_code == 200:
            json_response = response.json()
            if "candidates" in json_response and len(json_response["candidates"]) > 0:
                candidate = json_response["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                    generated_text = candidate["content"]["parts"][0].get("text", "")
                    messages.append("Success! Response received from Gemini.")
                else:
                    raise RuntimeError("Unexpected response structure (no parts found)")
            else:
                raise RuntimeError("Unexpected response structure (no candidates found)")
        else:
            # Handle the response boolean truthiness bug gracefully by outputting raw details
            err_details = f"API Error {response.status_code}: {response.text}"
            messages.append(err_details)
            return {
                "status": "failed",
                "tool_name": "generate_okf_with_gemini",
                "messages": messages,
                "results": None
            }
    except Exception as e:
        err_msg = f"Exception during Vertex API request: {e}"
        messages.append(err_msg)
        return {
            "status": "failed",
            "tool_name": "generate_okf_with_gemini",
            "messages": messages,
            "results": None
        }

    # 6. Save generated content to target directory
    if not os.path.isabs(output_dir):
        output_dir = os.path.abspath(output_dir)

    try:
        os.makedirs(output_dir, exist_ok=True)
        final_file_path = os.path.join(output_dir, output_filename)
        
        # If output was wrapped in ```yaml or ``` code blocks, strip the fences
        output_to_write = generated_text
        stripped = generated_text.strip()
        if stripped.startswith("```yaml") or stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            output_to_write = "\n".join(lines).strip() + "\n"

        with open(final_file_path, "w", encoding="utf-8") as f_out:
            f_out.write(output_to_write)
        
        rel_output_file_path = os.path.relpath(final_file_path, workspace_root)
        messages.append(f"Saved generated OKF successfully to: {rel_output_file_path}")
    except Exception as e:
        err_msg = f"Failed to save generated file: {e}"
        messages.append(err_msg)
        return {
            "status": "failed",
            "tool_name": "generate_okf_with_gemini",
            "messages": messages,
            "results": None
        }

    return {
        "status": "success",
        "tool_name": "generate_okf_with_gemini",
        "messages": messages,
        "results": {
            "output_file_path": rel_output_file_path,
            "model_used": model_name
        }
    }
