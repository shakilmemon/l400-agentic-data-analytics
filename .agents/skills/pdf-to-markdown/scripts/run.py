import os
import sys
import json
import base64
import requests
import google.auth
import google.auth.transport.requests

def convert_pdf_to_md(
    pdf_path: str,
    location: str = "global",
    temperature: float = 1.0,
    top_p: float = 1.0,
    top_k: int = 32
) -> dict:
    """
    Parses a PDF file using Gemini REST API on Vertex AI with robust fallbacks.
    Uses the global endpoint if location is 'global' to maximize model availability.
    """
    messages = []
    
    workspace_root = os.getcwd()
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.abspath(pdf_path)

    if not os.path.exists(pdf_path):
        messages.append(f"Error: PDF file not found at: '{pdf_path}'")
        return {
            "status": "failed",
            "tool_name": "convert_pdf_to_md",
            "messages": messages,
            "results": None
        }

    rel_pdf_path = os.path.relpath(pdf_path, workspace_root)
    messages.append(f"Starting conversion of PDF: {rel_pdf_path}")

    try:
        # Read and Base64 encode the PDF file
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # Get credentials and project ID
        creds, project_id = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        access_token = creds.token

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        # Define prompt for PDF markdown extraction
        prompt = (
            "You are an expert document converter. Convert this PDF document to clean, "
            "standard GitHub-flavored Markdown. Retain all sections, headings, list formats, "
            "bullet points, and tables. Do not wrap the output in markdown code blocks like "
            "```markdown, return only the raw markdown content directly."
        )

        models_to_try = ["gemini-3.8-flash", "gemini-3.1-pro-preview"]
        last_error = None
        extracted_text = None
        model_used = None

        for model in models_to_try:
            # Build URL based on location setting (global endpoint vs regional endpoint)
            if location == "global":
                url = f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/global/publishers/google/models/{model}:generateContent"
            else:
                url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model}:generateContent"

            # Use standard text/plain response mime-type for raw markdown
            generation_config = {
                "temperature": temperature,
                "topP": top_p,
                "maxOutputTokens": 65536,
                "candidateCount": 1,
                "responseMimeType": "text/plain",
            }

            if "gemini-2.5" in model:
                generation_config["topK"] = top_k

            payload = {
                "contents": {
                    "role": "user",
                    "parts": [
                        { "text": prompt },
                        { "inlineData": { "mimeType": "application/pdf", "data": pdf_base64 } }
                    ]
                },
                "generation_config": generation_config,
                "safety_settings": {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_LOW_AND_ABOVE"
                }
            }

            messages.append(f"Trying to convert PDF using model '{model}' in location '{location}' for project '{project_id}'...")
            try:
                response = requests.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    json_response = response.json()
                    
                    # Parse output safely following the sample structure
                    if "candidates" in json_response and len(json_response["candidates"]) > 0:
                        candidate = json_response["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                            extracted_text = candidate["content"]["parts"][0].get("text", "")
                            model_used = model
                            messages.append(f"Success! Content extracted using model '{model_used}'.")
                            break
                        else:
                            raise RuntimeError("Unexpected response structure (no parts found)")
                    else:
                        raise RuntimeError("Unexpected response structure (no candidates found)")
                else:
                    last_error = f"API Error {response.status_code}: {response.text}"
                    messages.append(f"Model '{model}' returned error code {response.status_code}")
            except Exception as e:
                last_error = f"Exception calling {model}: {e}"
                messages.append(f"Model '{model}' raised exception: {e}")

        if extracted_text is None:
            messages.append(f"All attempted models failed. Last error: {last_error}")
            return {
                "status": "failed",
                "tool_name": "convert_pdf_to_md",
                "messages": messages,
                "results": None
            }

        # Save output in same directory with .md extension
        output_path = os.path.splitext(pdf_path)[0] + ".md"
        with open(output_path, "w", encoding="utf-8") as f_out:
            f_out.write(extracted_text)

        rel_output_path = os.path.relpath(output_path, workspace_root)
        messages.append(f"Saved markdown successfully to: {rel_output_path}")

        return {
            "status": "success",
            "tool_name": "convert_pdf_to_md",
            "messages": messages,
            "results": {
                "pdf_path": rel_pdf_path,
                "markdown_path": rel_output_path,
                "model_used": model_used
            }
        }

    except Exception as e:
        messages.append(f"Critical error during conversion execution: {e}")
        return {
            "status": "failed",
            "tool_name": "convert_pdf_to_md",
            "messages": messages,
            "results": None
        }

if __name__ == "__main__":
    # If run directly as a script
    if len(sys.argv) < 2:
        raise ValueError("Filename must be provided.")
    pdf_input = sys.argv[1]
    res = convert_pdf_to_md(pdf_input)
    print(json.dumps(res, indent=2))
