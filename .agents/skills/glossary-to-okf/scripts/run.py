import os
import re
from datetime import datetime

def dict_to_yaml_str(d: dict) -> str:
    """
    Format a flat dictionary to YAML string representation.
    """
    lines = []
    for k, v in d.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        elif v is None:
            lines.append(f"{k}: null")
        else:
            v_str = str(v)
            if ":" in v_str or "#" in v_str or "'" in v_str or '"' in v_str or "{" in v_str or "}" in v_str or "\n" in v_str:
                lines.append(f"{k}: {repr(v_str)}")
            else:
                lines.append(f"{k}: {v_str}")
    return "\n".join(lines) + "\n"

def slugify(text: str) -> str:
    """
    Generate a safe file-system slug from text.
    """
    # Convert to lowercase
    text = text.lower()
    # Replace slashes, spaces, hyphens with underscores
    text = re.sub(r'[\s\-/]+', '_', text)
    # Remove non-alphanumeric/non-underscore characters
    text = re.sub(r'[^a-z0-9_]', '', text)
    # Clean redundant underscores
    text = re.sub(r'_+', '_', text)
    return text.strip('_')

def generate_indexes(okf_dir):
    """
    Regenerates progressive disclosure index.md files for root, datasets, tables, and references/glossary.
    """
    datasets_dir = os.path.join(okf_dir, "datasets")
    tables_dir = os.path.join(okf_dir, "tables")
    references_dir = os.path.join(okf_dir, "references")
    glossary_dir = os.path.join(references_dir, "glossary")

    # Root index
    root_index = """---
okf_version: "0.1"
---

# Premium Outdoor Gear - Legacy ERP OKF Bundle

This bundle contains the Open Knowledge Format (OKF) metadata for the Premium Outdoor Gear legacy ERP database `l400_agentic_da`.

## Subdirectories

* [tables](tables/index.md) - The physical BigQuery tables containing ERP transaction facts and dimensions.
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
            with open(os.path.join(datasets_dir, f"{d}.md"), "r") as f:
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
            with open(os.path.join(tables_dir, f"{t}.md"), "r") as f:
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

    # Glossary index (grouping by category!)
    if os.path.exists(glossary_dir):
        terms = [f[:-3] for f in os.listdir(glossary_dir) if f.endswith(".md") and f != "index.md"]
        terms.sort()
        
        glossary_index_lines = ["# Glossary Terms", "", "Conceptual and business glossary terms mapped to ERP columns:", ""]
        
        # We can group terms by category
        categories = {}
        for t in terms:
            with open(os.path.join(glossary_dir, f"{t}.md"), "r") as f:
                content = f.read()
                desc_match = re.search(r'description:\s*(.*?)\n', content)
                desc = desc_match.group(1).strip() if desc_match else "No description available."
                if (desc.startswith("'") and desc.endswith("'")) or (desc.startswith('"') and desc.endswith('"')):
                    desc = desc[1:-1]
                
                title_match = re.search(r'title:\s*(.*?)\n', content)
                title = title_match.group(1).strip() if title_match else t.replace("_", " ").title()
                if (title.startswith("'") and title.endswith("'")) or (title.startswith('"') and title.endswith('"')):
                    title = title[1:-1]
                
                cat_match = re.search(r'category:\s*(.*?)\n', content)
                cat = cat_match.group(1).strip() if cat_match else "General"
                if (cat.startswith("'") and cat.endswith("'")) or (cat.startswith('"') and cat.endswith('"')):
                    cat = cat[1:-1]
                
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append((title, t, desc))
        
        for category_name in sorted(categories.keys()):
            glossary_index_lines.append(f"## {category_name}")
            glossary_index_lines.append("")
            for title, t, desc in categories[category_name]:
                glossary_index_lines.append(f"* [{title}]({t}.md) - {desc}")
            glossary_index_lines.append("")

        with open(os.path.join(glossary_dir, "index.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(glossary_index_lines) + "\n")

def export_glossary_to_okf(
    input_file_path: str = "docs/requirements/Glossary/Outdoor_Gear_Industry_Glossary.md",
    okf_root_dir: str = "okf"
) -> dict:
    """
    Parses a glossary markdown file and outputs standard OKF reference glossary files
    grouped by categories and including synonyms in frontmatter.
    """
    messages = []
    
    # Standardize path references (relative to workspace root)
    if not os.path.isabs(input_file_path):
        input_file_path = os.path.abspath(input_file_path)
    if not os.path.isabs(okf_root_dir):
        okf_root_dir = os.path.abspath(okf_root_dir)

    glossary_dir = os.path.join(okf_root_dir, "references", "glossary")
    os.makedirs(glossary_dir, exist_ok=True)

    if not os.path.exists(input_file_path):
        messages.append(f"Source glossary file not found: {input_file_path}")
        return {
            "status": "failed",
            "tool_name": "export_glossary_to_okf",
            "messages": messages,
            "results": None
        }

    try:
        with open(input_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        current_category = "General"
        terms_count = 0

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Match category headers (## 1. Channel Definitions)
            if line_str.startswith("## ") or line_str.startswith("### "):
                category_match = re.match(r'^##+\s*(?:\d+\.\s*)?(.*)$', line_str)
                if category_match:
                    current_category = category_match.group(1).strip()
                    messages.append(f"Switching to Category: {current_category}")
                continue

            # Match list items (* **Term Name:** Definition)
            if line_str.startswith("*") and "**" in line_str:
                # Extract term and definition
                # Match * **Term (Synonym):** Definition
                term_match = re.match(r'^\s*\*\s+\*\*([^*:]+(?:\s*\([^)]+\))?)(?::\*\*|\*\*:\s*)\s*(.*)$', line_str)
                if term_match:
                    raw_term_label = term_match.group(1).strip()
                    definition = term_match.group(2).strip()

                    # Extract synonyms from term label, e.g. "D2C (Direct-to-Consumer)"
                    synonyms = []
                    term_name = raw_term_label
                    
                    paren_match = re.match(r'^([^(]+)\(([^)]+)\)$', raw_term_label)
                    if paren_match:
                        term_name = paren_match.group(1).strip()
                        syn_raw = paren_match.group(2).strip()
                        # Split synonyms if they have slashes or commas
                        synonyms = [s.strip() for s in re.split(r'[\/,]+', syn_raw) if s.strip()]

                    term_slug = slugify(term_name)
                    
                    # Create frontmatter
                    frontmatter = {
                        "type": "Reference",
                        "title": term_name,
                        "description": definition[:180] + ("..." if len(definition) > 180 else ""),
                        "category": current_category,
                        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                    }
                    if synonyms:
                        frontmatter["synonyms"] = synonyms

                    yaml_header = dict_to_yaml_str(frontmatter)

                    # Create body
                    synonyms_str = ", ".join(synonyms) if synonyms else "None"
                    body = f"""---
{yaml_header}---

# {term_name}

**Category:** {current_category}
**Synonyms:** {synonyms_str}

### Definition
{definition}

### Business Context
This concept is central to Premium Outdoor Gear business operations. It maps directly to data structures maintained in our Dataplex / Knowledge Engine business glossary and legacy ERP dataset `l400_agentic_da`.

# Citations

[1] Premium Outdoor Gear Business Glossary
[2] Corporate Operations, Supply Chain, & Finance Glossary
"""
                    # Write out reference file
                    term_file_path = os.path.join(glossary_dir, f"{term_slug}.md")
                    with open(term_file_path, "w", encoding="utf-8") as out_f:
                        out_f.write(body)
                    
                    terms_count += 1

        # Regenerate progressive indices
        messages.append("Regenerating OKF directory indices...")
        generate_indexes(okf_root_dir)

        messages.append(f"Successfully processed and exported {terms_count} glossary terms to OKF references!")
        return {
            "status": "success",
            "tool_name": "export_glossary_to_okf",
            "messages": messages,
            "results": {
                "terms_count": terms_count,
                "output_dir": glossary_dir
            }
        }

    except Exception as e:
        messages.append(f"Failed to parse and export glossary terms: {e}")
        return {
            "status": "failed",
            "tool_name": "export_glossary_to_okf",
            "messages": messages,
            "results": None
        }
