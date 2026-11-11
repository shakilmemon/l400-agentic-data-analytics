import os
import re
import json
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

def build_glossary_map(glossary_dir: str) -> dict:
    """Reads glossary markdown files under glossary_dir and builds a map of term_name.lower() -> relative_path."""
    if not os.path.exists(glossary_dir):
        return {}
    
    glossary_map = {}
    for f in os.listdir(glossary_dir):
        if f.endswith(".md") and f != "index.md":
            file_path = os.path.join(glossary_dir, f)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    yaml_lines = parts[1].strip().splitlines()
                    title = None
                    synonyms = []
                    in_synonyms_list = False
                    
                    for line in yaml_lines:
                        line_str = line.strip()
                        if line_str.startswith("-") and in_synonyms_list:
                            syn_val = line_str.strip("-").strip().strip("'\"")
                            if syn_val:
                                synonyms.append(syn_val)
                            continue
                        else:
                            in_synonyms_list = False
                            
                        if ":" in line_str:
                            k, v = line_str.split(":", 1)
                            k = k.strip().lower()
                            v = v.strip().strip("'\"")
                            if k == "title":
                                title = v
                            elif k == "synonyms":
                                in_synonyms_list = True
                                if v and v != "None":
                                    syn_val = v.strip().strip("[]").strip()
                                    if syn_val:
                                        synonyms.append(syn_val)
                    
                    if title:
                        glossary_map[title.lower()] = f"../references/glossary/{f}"
                        # Also map filename slug (basename without extension)
                        filename_slug = f[:-3].replace("_", " ").lower()
                        glossary_map[filename_slug] = f"../references/glossary/{f}"
                        
                    for syn in synonyms:
                        glossary_map[syn.lower()] = f"../references/glossary/{f}"
            except Exception:
                pass
    return glossary_map

def find_glossary_link(term_name: str, glossary_map: dict, col_name: str = None) -> str:
    """Resolves a term name to its glossary relative path using exact, synonym, or partial matches."""
    term_lower = term_name.lower()
    
    # 1. Exact match
    if term_lower in glossary_map:
        return glossary_map[term_lower]
        
    # 2. Match part before parenthesis: e.g. "D2C (Direct-to-Consumer)" -> "d2c"
    parenthesis_match = re.match(r'^([^(]+)\s*\(', term_name)
    if parenthesis_match:
        part = parenthesis_match.group(1).strip().lower()
        if part in glossary_map:
            return glossary_map[part]
            
    # 3. Fuzzy search (substring)
    for title, link in glossary_map.items():
        if title in term_lower or term_lower in title:
            return link
            
    # 4. Fallback to column name match
    if col_name:
        col_lower = col_name.lower()
        if col_lower in glossary_map:
            return glossary_map[col_lower]
        col_slug = col_lower.replace("_", " ")
        if col_slug in glossary_map:
            return glossary_map[col_slug]
            
    return None

def update_term_mappings_in_okf(
    mapping_file: str = "docs/requirements/Glossary/Terms_by_Table_and_Column.md",
    okf_root_dir: str = "okf"
) -> dict:
    """
    Parses a glossary mapping file and enriches local OKF tables with table-level and column-level term links.
    """
    messages = []
    
    # Check absolute paths
    if not os.path.isabs(mapping_file):
        mapping_file = os.path.abspath(mapping_file)
    if not os.path.isabs(okf_root_dir):
        okf_root_dir = os.path.abspath(okf_root_dir)

    if not os.path.exists(mapping_file):
        messages.append(f"Error: Source mapping file not found at: {mapping_file}")
        return {
            "status": "failed",
            "tool_name": "update_term_mappings_in_okf",
            "messages": messages,
            "results": None
        }

    glossary_dir = os.path.join(okf_root_dir, "references", "glossary")
    glossary_map = build_glossary_map(glossary_dir)
    messages.append(f"Discovered {len(glossary_map)} glossary reference definitions in '{glossary_dir}'.")

    # Parse mapping file
    try:
        with open(mapping_file, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        mappings = {}
        current_table = None
        current_section = None

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            # Match ### Table: `l400_agentic_da.TABLE_NAME`
            table_match = re.match(r'^###\s+Table:\s+`l400_agentic_da\.([A-Z0-9_]+)`\s*$', line_str)
            if table_match:
                current_table = table_match.group(1).strip()
                mappings[current_table] = {
                    'table_terms': [],
                    'column_terms': {}
                }
                current_section = None
                continue
                
            if current_table:
                if "Table-Level Terms:" in line_str:
                    current_section = "table_terms"
                    continue
                elif "Column-Level Terms:" in line_str:
                    current_section = "column_terms"
                    continue
                    
                if current_section == "table_terms":
                    # Match table terms
                    term_match = re.match(r'^\s*\*\s+\*\*([^*]+)\*\*:\s*(.*)$', line_str)
                    if not term_match:
                        term_match = re.match(r'^\s*\*\s+\*\*([^*]+)\*\*\s*(.*)$', line_str)
                    if term_match:
                        term_name = term_match.group(1).strip().rstrip(":").strip()
                        term_desc = term_match.group(2).strip()
                        mappings[current_table]['table_terms'].append((term_name, term_desc))
                        
                elif current_section == "column_terms":
                    # Match column terms
                    col_match = re.match(r'^\s*\*\s+`([A-Z0-9_&\s]+)`\s*(?:➔|->)\s*(.*)$', line_str)
                    if col_match:
                        cols_str = col_match.group(1).strip()
                        terms_body = col_match.group(2).strip()
                        
                        columns_list = [c.strip() for c in cols_str.split('&')]
                        bold_terms = re.findall(r'\*\*([^*]+)\*\*', terms_body)
                        
                        for col in columns_list:
                            if col not in mappings[current_table]['column_terms']:
                                mappings[current_table]['column_terms'][col] = []
                            for bt in bold_terms:
                                term_clean = bt.strip().rstrip(":").strip()
                                if term_clean and term_clean not in mappings[current_table]['column_terms'][col]:
                                    mappings[current_table]['column_terms'][col].append(term_clean)

        messages.append(f"Parsed {len(mappings)} tables with glossary mappings from '{mapping_file}'.")

        tables_dir = os.path.join(okf_root_dir, "tables")
        enriched_count = 0

        for table_name, data in mappings.items():
            table_file_path = os.path.join(tables_dir, f"{table_name}.md")
            if not os.path.exists(table_file_path):
                filename_slug = table_name.lower()
                table_file_path = os.path.join(tables_dir, f"{filename_slug}.md")
                if not os.path.exists(table_file_path):
                    messages.append(f"Warning: OKF Table file for '{table_name}' not found under '{tables_dir}'. Skipping.")
                    continue

            # Read existing file
            with open(table_file_path, "r", encoding="utf-8") as f_in:
                file_content = f_in.read()

            # Split into frontmatter and body
            parts = file_content.split("---", 2)
            if len(parts) < 3:
                messages.append(f"Error: Invalid OKF Table format in '{table_file_path}'. Skipping.")
                continue

            # 1. Update YAML Frontmatter
            yaml_block = parts[1].strip()
            body_block = parts[2]
            
            yaml_lines = yaml_block.splitlines()
            parsed_yaml = {}
            current_key = None
            for line in yaml_lines:
                line_str = line.strip()
                if not line_str:
                    continue
                if line_str.startswith("- ") and current_key:
                    if not isinstance(parsed_yaml.get(current_key), list):
                        parsed_yaml[current_key] = []
                    parsed_yaml[current_key].append(line_str[2:].strip().strip("'\""))
                elif ":" in line_str:
                    k, v = line_str.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    if v == "":
                        parsed_yaml[k] = []
                    else:
                        parsed_yaml[k] = v
                    current_key = k

            # Inject terms list (only term names)
            table_terms_list = [name for name, _ in data["table_terms"]]
            if table_terms_list:
                parsed_yaml["terms"] = table_terms_list
            elif "terms" in parsed_yaml:
                del parsed_yaml["terms"]

            # Rebuild YAML
            new_yaml_lines = []
            for k, v in parsed_yaml.items():
                if isinstance(v, list):
                    new_yaml_lines.append(f"{k}:")
                    for item in v:
                        new_yaml_lines.append(f"  - {item}")
                else:
                    new_yaml_lines.append(f"{k}: {v}")
            
            new_yaml_block = "\n".join(new_yaml_lines)

            # 2. Update Schema section in body_block
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
            
            # If we found the Schema table, rewrite it with a third column
            if schema_start_idx != -1 and schema_end_idx != -1:
                table_lines = body_lines[schema_start_idx+1:schema_end_idx]
                new_table_lines = []
                
                new_table_lines.append("| Field Name | Description | Business Terms |")
                new_table_lines.append("| :--- | :--- | :--- |")
                
                for line in table_lines:
                    line_str = line.strip()
                    if not line_str.startswith("|") or ":---" in line_str or "Field Name" in line_str:
                        continue
                    
                    row_parts = [p.strip() for p in line_str.split("|")]
                    if len(row_parts) >= 3:
                        col_name = row_parts[1].strip("`").strip()
                        col_desc = row_parts[2]
                        
                        # Fetch column terms mapped to this column
                        matched_terms = data["column_terms"].get(col_name, [])
                        formatted_terms_list = []
                        
                        for term in matched_terms:
                            link = find_glossary_link(term, glossary_map, col_name)
                            if link:
                                formatted_terms_list.append(f"[{term}]({link})")
                            else:
                                formatted_terms_list.append(term)
                                
                        terms_col_val = ", ".join(formatted_terms_list) if formatted_terms_list else "-"
                        new_table_lines.append(f"| `{col_name}` | {col_desc} | {terms_col_val} |")
                        
                # Replace the schema lines
                body_lines[schema_start_idx+1:schema_end_idx] = [""] + new_table_lines + [""]
                body_block = "\n".join(body_lines)

            # Strip any existing Table-Level Business Terms section
            body_block = re.sub(r'### Table-Level Business Terms\n.*?(?=\n#|\Z)', '', body_block, flags=re.DOTALL)

            # Insert Table-Level Business Terms right before "# Schema"
            table_terms_body_lines = []
            if data["table_terms"]:
                table_terms_body_lines.append("### Table-Level Business Terms")
                for term_name, term_desc in data["table_terms"]:
                    link = find_glossary_link(term_name, glossary_map)
                    if link:
                        table_terms_body_lines.append(f"*   **[{term_name}]({link})**: {term_desc}")
                    else:
                        table_terms_body_lines.append(f"*   **{term_name}**: {term_desc}")
                table_terms_body_lines.append("")

            if table_terms_body_lines:
                body_lines_with_terms = body_block.splitlines()
                schema_idx = -1
                for idx, line in enumerate(body_lines_with_terms):
                    if line.strip().startswith("# Schema"):
                        schema_idx = idx
                        break
                if schema_idx != -1:
                    body_lines_with_terms[schema_idx:schema_idx] = table_terms_body_lines + [""]
                else:
                    body_lines_with_terms.extend([""] + table_terms_body_lines)
                body_block = "\n".join(body_lines_with_terms)

            # Reconstruct the entire file
            new_file_content = f"---\n{new_yaml_block}\n---\n{body_block}"
            
            rel_table_path = os.path.relpath(table_file_path, okf_root_dir)
            messages.append(f"Enriching OKF table file: {table_name} -> okf/{rel_table_path}")
            with open(table_file_path, "w", encoding="utf-8") as f_out:
                f_out.write(new_file_content)
                
            enriched_count += 1

        messages.append("Successfully updated OKF tables with term mappings!")
        return {
            "status": "success",
            "tool_name": "update_term_mappings_in_okf",
            "messages": messages,
            "results": {
                "tables_enriched_count": enriched_count,
                "output_dir": tables_dir
            }
        }

    except Exception as e:
        messages.append(f"An unexpected error occurred during mappings processing: {e}")
        return {
            "status": "failed",
            "tool_name": "update_term_mappings_in_okf",
            "messages": messages,
            "results": None
        }
