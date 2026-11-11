import os
import json
import re
from datetime import datetime

def load_env_config(env_file_path: str = "agent-config.json") -> dict:
    """Loads environment configurations from the specified JSON file."""
    if os.path.exists(env_file_path):
        try:
            with open(env_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def regenerate_indices(okf_dir: str):
    """Regenerates the Markdown directory indexes for root, datasets, tables, and references."""
    datasets_dir = os.path.join(okf_dir, "datasets")
    tables_dir = os.path.join(okf_dir, "tables")
    references_dir = os.path.join(okf_dir, "references")
    glossary_dir = os.path.join(references_dir, "glossary")

    # Root index
    root_index = """# Open Knowledge Format (OKF) Bundle

This bundle contains the database and glossary schemas defined for the Premium Outdoor Gear legacy ERP database.

## Subdirectories

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
            with open(os.path.join(datasets_dir, f"{d}.md"), "r", encoding="utf-8") as f:
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
            with open(os.path.join(tables_dir, f"{t}.md"), "r", encoding="utf-8") as f:
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
        ref_index = """# References

Reference directories containing business glossary terms, metrics definitions, and mapping tables.

## Subdirectories

* [glossary](glossary/index.md) - Corporate business glossary terms and conceptual descriptions.
"""
        with open(os.path.join(references_dir, "index.md"), "w", encoding="utf-8") as f:
            f.write(ref_index)

    # Glossary index
    if os.path.exists(glossary_dir):
        terms = [f[:-3] for f in os.listdir(glossary_dir) if f.endswith(".md") and f != "index.md"]
        terms.sort()
        glossary_index_lines = ["# Glossary Terms", "", "Conceptual and business glossary terms mapped to ERP columns:", ""]
        for t in terms:
            with open(os.path.join(glossary_dir, f"{t}.md"), "r", encoding="utf-8") as f:
                content = f.read()
                desc_match = re.search(r'description:\s*(.*?)\n', content)
                desc = desc_match.group(1).strip() if desc_match else "No description available."
                if (desc.startswith("'") and desc.endswith("'")) or (desc.startswith('"') and desc.endswith('"')):
                    desc = desc[1:-1]
            glossary_index_lines.append(f"* [{t.upper()}]({t}.md) - {desc}")
        with open(os.path.join(glossary_dir, "index.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(glossary_index_lines) + "\n")


def export_dictionary_to_okf(
    input_file_path: str = "docs/requirements/Data-Dictionary/Data_Dictionary.md",
    okf_root_dir: str = "okf"
) -> dict:
    """
    Parses a data dictionary markdown file and writes/updates OKF table references under okf_root_dir/tables.
    """
    messages = []
    
    # Check absolute paths
    if not os.path.isabs(input_file_path):
        input_file_path = os.path.abspath(input_file_path)
    if not os.path.isabs(okf_root_dir):
        okf_root_dir = os.path.abspath(okf_root_dir)

    if not os.path.exists(input_file_path):
        messages.append(f"Error: Source data dictionary not found at: {input_file_path}")
        return {
            "status": "failed",
            "tool_name": "export_dictionary_to_okf",
            "messages": messages,
            "results": None
        }

    # Load environment variables for project id and dataset id
    env_config = load_env_config()
    project_id = env_config.get("gcp-project-id") or "l400-agentic-da-966jz2x4id"
    dataset_id = env_config.get("bigquery-dataset") or "l400_agentic_da"

    tables_dir = os.path.join(okf_root_dir, "tables")
    os.makedirs(tables_dir, exist_ok=True)

    try:
        with open(input_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        tables_data = {}
        current_table = None
        current_desc = ""
        columns = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            # Match table heading ### `TABLE_NAME` or ### TABLE_NAME
            table_match = re.match(r'^###\s+`?([A-Za-z0-9_]+)`?\s*$', line_str)
            if table_match:
                if current_table:
                    tables_data[current_table] = {"description": current_desc, "columns": columns}
                current_table = table_match.group(1).strip()
                current_desc = ""
                columns = []
                continue
                
            # Match table description
            desc_match = re.match(r'^\*\*Table Description:\*\*\s*(.*)$', line_str)
            if desc_match:
                current_desc = desc_match.group(1).strip()
                continue
                
            # Match schema table columns
            if line_str.startswith('|') and current_table:
                parts = [p.strip() for p in line_str.split('|')]
                if len(parts) >= 4:
                    col_name = parts[1].strip('`').strip()
                    col_desc = parts[2]
                    if col_name and col_name.lower() != 'column name' and not re.match(r'^[\s:-]+$', col_name):
                        columns.append((col_name, col_desc))

        if current_table:
            tables_data[current_table] = {"description": current_desc, "columns": columns}

        messages.append(f"Parsed {len(tables_data)} tables from '{input_file_path}'.")

        # Generate OKF files for each table
        current_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        for table_name, data in tables_data.items():
            filename_slug = table_name.lower()
            table_file_path = os.path.join(tables_dir, f"{table_name}.md")
            
            # Uncapitalize table description for the body prose (e.g. "The TABLE table is a key component... It holds the master chart...")
            raw_desc = data["description"]
            uncap_desc = raw_desc[0].lower() + raw_desc[1:] if raw_desc else ""

            # Build columns schema table markdown
            columns_lines = []
            for col_name, col_desc in data["columns"]:
                columns_lines.append(f"| `{col_name}` | {col_desc} |")
            schema_table_content = "\n".join(columns_lines)

            body_content = f"""---
type: BigQuery Table
resource: 'https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_name}'
title: {table_name}
description: {raw_desc}
tags:
  - {filename_slug}
  - erp
  - {dataset_id}
timestamp: '{current_time}'
---

The `{table_name}` table is a key component of the Premium Outdoor Gear legacy ERP database. It holds {uncap_desc}

# Schema

| Field Name | Description |
| :--- | :--- |
{schema_table_content}

# Citations

[1] BigQuery Table Resource: `https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_name}`
[2] Premium Outdoor Gear - Legacy ERP Database Catalog
"""
            messages.append(f"Writing table schema: {table_name} -> okf/tables/{table_name}.md")
            with open(table_file_path, "w", encoding="utf-8") as out_f:
                out_f.write(body_content)

        # Regenerate OKF indexes
        messages.append("Regenerating OKF directory indices...")
        regenerate_indices(okf_root_dir)

        messages.append(f"Successfully processed and updated {len(tables_data)} tables in OKF!")
        return {
            "status": "success",
            "tool_name": "export_dictionary_to_okf",
            "messages": messages,
            "results": {
                "tables_count": len(tables_data),
                "output_dir": tables_dir
            }
        }

    except Exception as e:
        messages.append(f"An unexpected error occurred during dictionary export: {e}")
        return {
            "status": "failed",
            "tool_name": "export_dictionary_to_okf",
            "messages": messages,
            "results": None
        }
