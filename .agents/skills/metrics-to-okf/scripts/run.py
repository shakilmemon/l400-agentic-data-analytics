import os
import re
import json
import html
from datetime import datetime

def slugify(text: str) -> str:
    """Converts text into a clean snake_case filename slug."""
    slug = text.lower()
    # Replace non-alphanumeric with spaces, then spaces with underscores
    slug = re.sub(r'[^a-z0-9\s_]', ' ', slug)
    slug = "_".join(slug.split())
    return slug

def generate_metrics_index(metrics_dir: str) -> None:
    """Generates an index.md navigation file listing all metrics beautifully."""
    if not os.path.exists(metrics_dir):
        return
        
    md_files = [f for f in os.listdir(metrics_dir) if f.endswith(".md") and f != "index.md"]
    md_files.sort()
    
    index_lines = [
        "---",
        "type: Reference",
        "title: Metrics Index",
        "description: Golden queries and metrics for Conversational Analytics.",
        "timestamp: '" + datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ') + "'",
        "---",
        "",
        "# Golden Metrics Index",
        "",
        "Welcome to the Golden Metrics Index. These reference metrics act as standard golden queries for Conversational Analytics.",
        "",
        "## Available Metrics",
        ""
    ]
    
    for f in md_files:
        file_path = os.path.join(metrics_dir, f)
        title = os.path.splitext(f)[0].replace("_", " ").title()
        description = "No description provided."
        
        try:
            with open(file_path, "r", encoding="utf-8") as file_in:
                content = file_in.read()
            parts = content.split("---", 2)
            if len(parts) >= 3:
                yaml_lines = parts[1].strip().splitlines()
                for line in yaml_lines:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip().lower()
                        v = v.strip().strip("'\"")
                        if k == "title":
                            title = v
                        elif k == "description":
                            description = v
        except Exception:
            pass
            
        index_lines.append(f"* [{title}]({f}) - {description}")
        
    index_lines.append("")
    index_lines.append("# Citations")
    index_lines.append("- Premium Outdoor Gear Business Analytics Dictionary")
    
    index_path = os.path.join(metrics_dir, "index.md")
    with open(index_path, "w", encoding="utf-8") as f_out:
        f_out.write("\n".join(index_lines))

def parse_sql_file(content: str) -> list:
    """Parses standard SQL files with METRIC declarations."""
    blocks = re.split(r'--\s*-{10,}', content)
    metrics = []
    current_metric = None

    for b in blocks:
        b_str = b.strip()
        if not b_str:
            continue
        
        metric_match = re.search(r'METRIC(?:\s+\d+)?:?\s*(.*)', b_str, re.IGNORECASE)
        if metric_match:
            title = metric_match.group(1).strip()
            desc_match = re.search(r'DESCRIPTION:\s*(.*)', b_str, re.IGNORECASE)
            desc = desc_match.group(1).strip() if desc_match else f"Metric for {title}."
            
            current_metric = {
                "title": title,
                "description": desc,
                "sql": ""
            }
        elif current_metric:
            current_metric["sql"] = b_str
            metrics.append(current_metric)
            current_metric = None
            
    return metrics

def parse_rdl_file(content: str, filename: str) -> list:
    """Parses SSRS .rdl reports and extracts SQL query inside <CommandText>."""
    match = re.search(r'<CommandText>\s*(.*?)\s*</CommandText>', content, re.DOTALL)
    if not match:
        return []
        
    raw_query = html.unescape(match.group(1).strip())
    
    # Parse description/author from comments inside /* ... */
    comment_match = re.search(r'/\*(.*?)\*/', raw_query, re.DOTALL)
    desc = f"Calculates metrics based on {os.path.basename(filename)} dataset."
    if comment_match:
        comment_body = comment_match.group(1).strip()
        lines = comment_body.splitlines()
        for line in lines:
            line_str = line.strip().lstrip("*").strip()
            if line_str.lower().startswith("desc:") or line_str.lower().startswith("description:"):
                desc = line_str.split(":", 1)[1].strip()
                break
                
    title = os.path.splitext(os.path.basename(filename))[0].replace("_", " ").title()
    return [{
        "title": title,
        "description": desc,
        "sql": raw_query
    }]

def parse_twb_file(content: str, filename: str) -> list:
    """Parses Tableau .twb workbooks and extracts calculated fields with formula."""
    pattern = r"<column\s+[^>]*caption='([^']*)'[^>]*>.*?<calculation\s+[^>]*formula='([^']*)'"
    matches = re.findall(pattern, content, re.DOTALL)
    
    metrics = []
    for match in matches:
        caption = match[0].strip()
        formula = html.unescape(match[1].strip())
        
        # Heuristics based description
        desc = f"Tableau calculated field: {caption}."
        if "Certified Field Tester Status" in caption:
            desc = "Identifies apex D2C customers who actively purchase, write reviews, and maintain zero returns."
        elif "Tier 1 Wholesale Distributor Flag" in caption:
            desc = "Flags wholesale distributors with high annual volume, product category diversity, and low average days to pay."
            
        metrics.append({
            "title": caption,
            "description": desc,
            "sql": formula
        })
    return metrics

def parse_md_file(content: str, filename: str) -> list:
    """Parses markdown files and extracts SQL query inside ```sql code blocks or Formula notations."""
    metrics = []
    
    # Try finding standard ```sql ... ``` blocks first
    matches = list(re.finditer(r'```sql\s*(.*?)\s*```', content, re.DOTALL))
    
    if matches:
        for match in matches:
            start_idx = match.start()
            raw_query = match.group(1).strip()
            
            # Backwards search for the nearest heading
            lines = content[:start_idx].splitlines()
            title = os.path.splitext(os.path.basename(filename))[0].replace("_", " ").title()
            desc = f"Metric extracted from {os.path.basename(filename)}."
            
            for line in reversed(lines):
                line_str = line.strip()
                if line_str.startswith("#"):
                    title = line_str.lstrip("#").strip()
                    break
                    
            # Look for description in preceding lines
            desc_lines = []
            for line in reversed(lines):
                line_str = line.strip()
                if line_str.startswith("#"):
                    break
                if line_str and not line_str.startswith("```"):
                    desc_lines.insert(0, line_str)
            if desc_lines:
                desc = " ".join(desc_lines).strip()
                if len(desc) > 200:
                    desc = desc[:197] + "..."
                    
            metrics.append({
                "title": title,
                "description": desc,
                "sql": raw_query
            })
    else:
        # Fallback: search for Formula: or (Formula: ...)
        # E.g. "- Calculated **Net Revenue** (Formula: `SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N))`)"
        for line in content.splitlines():
            if "(Formula:" in line:
                parts = line.split("(Formula:", 1)
                title_part = parts[0].strip()
                formula_part = parts[1].strip()
                
                # Clean title: strip *, - , backticks, spaces
                title_clean = title_part
                title_clean = re.sub(r'^[*-]\s*', '', title_clean)
                title_clean = title_clean.replace("**", "").replace("*", "").replace("`", "").strip()
                
                # Clean formula: strip trailing parenthesis and backticks
                formula_clean = formula_part
                if "`" in formula_clean:
                    bt_match = re.search(r'`([^`]+)`', formula_clean)
                    if bt_match:
                        formula_clean = bt_match.group(1).strip()
                else:
                    if formula_clean.endswith(")"):
                        formula_clean = formula_clean[:-1].strip()
                    formula_clean = formula_clean.replace("`", "").strip()
                
                if title_clean and formula_clean:
                    # Avoid duplicate "Calculated Calculated" in description
                    desc_title = title_clean
                    if desc_title.lower().startswith("calculated"):
                        desc = f"{desc_title} formula."
                    else:
                        desc = f"Calculated {desc_title} formula."
                        
                    metrics.append({
                        "title": title_clean,
                        "description": desc,
                        "sql": formula_clean
                    })
            
    return metrics

def export_metrics_to_okf(
    file_paths,  # Can be a string or a list of strings
    okf_root_dir: str = "okf"
) -> dict:
    """
    Parses legacy SQL, SSRS reports (.rdl), Tableau workbooks (.twb), and Markdown (.md),
    extracts Metric sections, and exports them to OKF metrics reference files.
    """
    messages = []
    
    # Handle single file path
    if isinstance(file_paths, str):
        file_paths = [file_paths]
        
    workspace_root = os.getcwd()
    if not os.path.isabs(okf_root_dir):
        okf_root_dir = os.path.abspath(okf_root_dir)

    metrics_output_dir = os.path.join(okf_root_dir, "references", "metrics")
    os.makedirs(metrics_output_dir, exist_ok=True)

    exported_count = 0
    timestamp_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    for raw_path in file_paths:
        file_path = raw_path
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
            
        if not os.path.exists(file_path):
            messages.append(f"Warning: File not found at: '{raw_path}'. Skipping.")
            continue
            
        rel_resource_path = os.path.relpath(file_path, workspace_root)
        messages.append(f"Processing file: {rel_resource_path}")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f_in:
                content = f_in.read()
                
            _, ext = os.path.splitext(file_path.lower())
            parsed_metrics = []
            
            if ext == ".sql":
                parsed_metrics = parse_sql_file(content)
            elif ext == ".rdl":
                parsed_metrics = parse_rdl_file(content, file_path)
            elif ext == ".twb":
                parsed_metrics = parse_twb_file(content, file_path)
            elif ext == ".md":
                parsed_metrics = parse_md_file(content, file_path)
            else:
                messages.append(f"Warning: Unsupported file extension '{ext}' for file '{rel_resource_path}'. Skipping.")
                continue
                
            messages.append(f"Extracted {len(parsed_metrics)} metrics from '{rel_resource_path}'.")
            
            for m in parsed_metrics:
                m_slug = slugify(m["title"])
                output_file_name = f"{m_slug}.md"
                output_file_path = os.path.join(metrics_output_dir, output_file_name)

                # Build markdown document
                lines = [
                    "---",
                    "type: Reference",
                    f"resource: {rel_resource_path}",
                    f"title: {m['title']}",
                    f"description: {m['description']}",
                    "tags:",
                    "- metric",
                    f"timestamp: '{timestamp_str}'",
                    "---",
                    "",
                    m["description"],
                    "",
                    "```sql",
                    m["sql"],
                    "```",
                    "",
                    "# Citations",
                    f"- {rel_resource_path}"
                ]

                with open(output_file_path, "w", encoding="utf-8") as out_f:
                    out_f.write("\n".join(lines))
                
                messages.append(f"Exported metric: '{m['title']}' -> '{os.path.relpath(output_file_path, workspace_root)}'")
                exported_count += 1
                
        except Exception as e:
            messages.append(f"Error processing file '{rel_resource_path}': {e}")

    # Re-generate Metrics Index
    generate_metrics_index(metrics_output_dir)
    messages.append("Regenerated metrics directory index 'index.md'.")
    messages.append("Successfully processed and exported all metrics!")

    return {
        "status": "success",
        "tool_name": "export_metrics_to_okf",
        "messages": messages,
        "results": {
            "metrics_exported_count": exported_count,
            "output_dir": os.path.relpath(metrics_output_dir, workspace_root)
        }
    }
