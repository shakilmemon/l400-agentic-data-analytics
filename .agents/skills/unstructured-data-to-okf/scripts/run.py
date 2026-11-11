import os
import re
from datetime import datetime

def parse_requirements_file(filepath: str) -> dict:
    """
    Parses business_requirements.md to extract core business column descriptions
    and other requirements.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find columns listed with bullet points: * **FieldName**: Description
    # We match both '*' and '-' as bullet prefixes
    pattern = r'[*-]\s+\*\*([a-zA-Z0-9_]+)\*\*:\s*(.*)'
    col_matches = re.findall(pattern, content)

    columns = []
    for col_name, desc in col_matches:
        # Strip potential markdown formatting from description
        desc_clean = desc.strip()
        columns.append({
            "name": col_name.strip(),
            "description": desc_clean
        })

    return {
        "columns": columns,
        "raw_content": content
    }

def compile_requirements_to_okf(
    req_file_path: str = "docs/requirements/Unstructured-Data/business_requirements.md",
    okf_root_dir: str = "okf"
) -> dict:
    """
    Compiles the unstructured requirements into an OKF table spec and CA business context guide.
    """
    messages = []
    workspace_root = os.getcwd()

    if not os.path.isabs(req_file_path):
        req_file_path = os.path.abspath(req_file_path)
    if not os.path.isabs(okf_root_dir):
        okf_root_dir = os.path.abspath(okf_root_dir)

    if not os.path.exists(req_file_path):
        messages.append(f"Error: Requirements file not found at: '{req_file_path}'")
        return {
            "status": "failed",
            "tool_name": "compile_requirements_to_okf",
            "messages": messages,
            "results": None
        }

    rel_req_path = os.path.relpath(req_file_path, workspace_root)
    messages.append(f"Successfully read business requirements from '{rel_req_path}'.")

    try:
        req_data = parse_requirements_file(req_file_path)
        business_cols = req_data["columns"]
        
        if not business_cols:
            messages.append("Warning: No column-level requirements parsed from the bullet points. Using defaults.")
            # Default columns in case parsing fails
            business_cols = [
                {"name": "Memo_Date", "description": "The timestamp when the original executive memo or alert was published."},
                {"name": "Sender", "description": "The department or executive who issued the memo (e.g., 'Global Competitive Intelligence Desk')."},
                {"name": "Event_Type", "description": "The categorization of the event (e.g., 'Market Anomaly', 'Supply Chain Disruption')."},
                {"name": "Event_Start_Date", "description": "The calendar date (YYYY-MM-DD) when the event's financial impact began."},
                {"name": "Event_End_Date", "description": "The calendar date (YYYY-MM-DD) when the event's financial impact concluded or is expected to conclude."},
                {"name": "Affected_Division", "description": "The business division impacted by the event (e.g., 'Wholesale', 'D2C', or 'All'). Used to map to CHN_FLG."},
                {"name": "Impacted_Products", "description": "The specific product categories or SKUs affected (e.g., 'Mountain Bikes', 'Tents')."},
                {"name": "Event_Description", "description": "A detailed text explanation of what happened (e.g., competitor recall, material shortage)."},
                {"name": "Root_Cause", "description": "The underlying trigger of the event (e.g., 'Geopolitical export restriction', 'Safety weld failure')."},
                {"name": "Financial_Impact_Category", "description": "The specific metric impacted (e.g., 'Gross Margin Dip', 'Revenue Spike')."},
                {"name": "FPA_Guidance", "description": "Instructions for the FP&A team on how to treat this anomaly in future run-rate forecasting."},
                {"name": "Expected_Duration", "description": "How long the anomaly is expected to last before normalizing."}
            ]

        # The 4 system fields required ONLY for BigQuery (and the OKF schema definition)
        system_cols = [
            {"name": "full_response", "description": "System field: The raw JSON output returned by the LLM extraction model."},
            {"name": "status", "description": "System field: The success/failure execution status of the LLM extraction."},
            {"name": "uri", "description": "System field: The Google Cloud Storage (GCS) path to the original source PDF document."},
            {"name": "prompt", "description": "System field: The exact prompt instructions passed to the LLM to generate the row."}
        ]

        timestamp_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        project_id = "l400-agentic-da-966jz2x4id"  # Standard project ID from env or config
        
        # ----------------------------------------------------------------------
        # 1. GENERATE okf/tables/dim_business_events.md (BigQuery Table Reference)
        # ----------------------------------------------------------------------
        table_output_dir = os.path.join(okf_root_dir, "tables")
        os.makedirs(table_output_dir, exist_ok=True)
        table_file_path = os.path.join(table_output_dir, "dim_business_events.md")

        table_lines = [
            "---",
            "type: BigQuery Table",
            f"resource: 'https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/l400_agentic_da/tables/dim_business_events'",
            "title: dim_business_events",
            "description: A qualitative dimension table generated via AI extraction from unstructured executive memos and market alerts. It provides crucial business context, root causes, and explanations for anomalies in financial and operational data.",
            "tags:",
            "  - dim_business_events",
            "  - erp",
            "  - l400_agentic_da",
            f"timestamp: '{timestamp_str}'",
            "---",
            "",
            "The `dim_business_events` table is a key component of the Premium Outdoor Gear legacy ERP database. It holds a qualitative dimension table generated via AI extraction from unstructured executive memos and market alerts. It provides crucial business context, root causes, and explanations for anomalies in financial and operational data.",
            "",
            "# Schema",
            "",
            "| Field Name | Description |",
            "| :--- | :--- |"
        ]

        # Add both business columns and system columns to the BQ OKF file!
        for col in business_cols:
            table_lines.append(f"| `{col['name']}` | {col['description']} |")
        for col in system_cols:
            table_lines.append(f"| `{col['name']}` | {col['description']} |")

        table_lines.extend([
            "",
            "# Citations",
            "",
            f"[1] BigQuery Table Resource: `https://bigquery.googleapis.com/v2/projects/{project_id}/datasets/l400_agentic_da/tables/dim_business_events`",
            "[2] Premium Outdoor Gear - Legacy ERP Database Catalog",
            ""
        ])

        with open(table_file_path, "w", encoding="utf-8") as f_tab:
            f_out_content = "\n".join(table_lines)
            f_tab.write(f_out_content)

        rel_table_path = os.path.relpath(table_file_path, workspace_root)
        messages.append(f"Generated OKF table reference '{rel_table_path}'.")

        # ----------------------------------------------------------------------
        # 2. GENERATE docs/requirements/Unstructured-Data/02-business-context.md
        # ----------------------------------------------------------------------
        ca_output_dir = os.path.dirname(req_file_path)
        ca_file_path = os.path.join(ca_output_dir, "02-business-context.md")

        # Compile the SQL Golden Query
        golden_sql = """SELECT 
    cal.FISC_YR_N AS FiscalYear,
    cal.FISC_PER_N AS FiscalPeriod,
    SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) AS Net_Revenue,
    MAX(biz.Event_Description) AS Qualitative_Explanation,
    MAX(biz.Root_Cause) AS Root_Cause
FROM `l400_agentic_da.SLS_ORD_HDR` hdr
JOIN `l400_agentic_da.SYS_CAL_DIM` cal 
    ON hdr.ORD_DT_SID = cal.DT_SK
JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln 
    ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
-- THE NATURAL JOIN PATTERN:
LEFT JOIN `l400_agentic_da.dim_business_events` biz 
    ON cal.CAL_DT BETWEEN biz.Event_Start_Date AND biz.Event_End_Date
WHERE hdr.STS_CDE = 'C' AND cal.FISC_YR_N = 2025
GROUP BY 1, 2
ORDER BY 1, 2;"""

        ca_lines = [
            "**Golden Query (Type 2 Analytical Example)**",
            "",
            "If a user asks *\"Why did wholesale revenue spike in April?\"*, the CA Agent will have no idea how to join a text string like `'Wholesale'` in `Affected_Division` to the integer `CHN_FLG = 2` in the Sales Header table, nor will it know how to correctly map `Event_Month` to `SYS_CAL_DIM`. The Golden Query teaches the agent exactly how to overlay this qualitative data onto the financial math.",
            "",
            "Here is exactly what you need to add to your Data Dictionary and the Golden Query to make this work flawlessly.",
            "",
            "***",
            "",
            "## Unstructured Business Context",
            "",
            "### `dim_business_events`",
            "**Table Description:** A qualitative dimension table generated via AI extraction from unstructured executive memos and market alerts. It provides crucial business context, root causes, and explanations for anomalies in financial and operational data.",
            "",
            "| Column Name | Description |",
            "| :--- | :--- |"
        ]

        # Add ONLY business columns to the business context document!
        for col in business_cols:
            ca_lines.append(f"| `{col['name']}` | {col['description']} |")

        ca_lines.extend([
            "```", # Closes the markdown code block boundary in the original structure
            "",
            "***",
            "",
            "### The Golden Query (Type 2 Analytical Example)",
            "*Register this in the CA Agent configuration. It explicitly teaches the agent how to do the complex date extraction and how to map the text string `'Wholesale'` to the integer `CHN_FLG = 2`.*",
            "",
            "**Prompt to Match:** Show me the Net Revenue trend for 2025 and include any qualitative business events or context.",
            "",
            "**The SQL:**",
            "```sql",
            golden_sql,
            "```",
            "",
            "### Prompt to trigger",
            "Why did gross margins drop in Q3?",
            ""
        ])

        with open(ca_file_path, "w", encoding="utf-8") as f_ca:
            f_ca.write("\n".join(ca_lines))

        rel_ca_path = os.path.relpath(ca_file_path, workspace_root)
        messages.append(f"Generated CA business context '{rel_ca_path}'.")
        messages.append("Successfully compiled unstructured requirements into OKF table spec and CA guide!")

        return {
            "status": "success",
            "tool_name": "compile_requirements_to_okf",
            "messages": messages,
            "results": {
                "okf_table_created": True,
                "ca_context_created": True,
                "okf_table_path": rel_table_path,
                "ca_context_path": rel_ca_path
            }
        }

    except Exception as e:
        messages.append(f"Critical error during requirements compilation: {e}")
        return {
            "status": "failed",
            "tool_name": "compile_requirements_to_okf",
            "messages": messages,
            "results": None
        }
