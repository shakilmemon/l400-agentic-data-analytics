You are an expert Google Cloud AI Integration Engineer. Your task is to consolidate three Conversational Analytics staging artifacts into a single Open Knowledge Format (OKF) YAML file that maps directly to the Google Cloud Data Agents REST API schema.

I have attached three files:
1. `agent_system_prompt.md` (Contains the behavioral rules and clarification triggers)
2. `agent_table_list.md` (Contains the list of tables the agent is allowed to access)
3. `agent_golden_queries.md` (Contains the Verified SQL queries and their matching natural language prompts)

**Instructions:**
1. **Extract Tables:** Read the `agent_table_list.md` file. Extract ONLY the table names that were kept (e.g., B2B_INV_AGING, CUST_MSTR_D2C) and format them as a YAML list under `datasource.tables`. Do not include the dropped tables.
2. **Extract System Instructions:** Read the `agent_system_prompt.md` file. Extract the entire text and place it under `systemInstruction` using the YAML multi-line literal block operator (`|`) to preserve Markdown formatting.
3. **3. Extract Golden Queries:** Read the `agent_golden_queries.md` file. For every SQL query provided, look at the "Prompt to Match". **Extract ONLY the first question provided, strip away any quotation marks or slashes, and place it in the `naturalLanguageQuestion` field as a clean string.** Extract the SQL and place it in the `sqlQuery` field using the YAML multi-line literal block operator (`|`).
4. **Output Format:** Output ONLY the compiled YAML file based exactly on the template provided below. Do not wrap it in markdown code blocks, just output the raw YAML starting and ending with `---`.

**Template to Follow:**
```yaml
---
type: Conversational Analytics Agent
dataAgentId: premium-outdoor-gear-agent
displayName: Premium Outdoor Gear CA Agent
description: Financial and operational AI assistant exclusively serving the Global CFO and Executive Directors.
datasource:
  type: bigquery
  project_id: <<gcp_project_id>>
  dataset_id: l400_agentic_da
  tables:
    - <<INSERT_TABLE_1>>
    - <<INSERT_TABLE_2>>
    # ... insert all tables extracted from agent_table_list.md
systemInstruction: |
  <<INSERT_ENTIRE_CONTENTS_OF_AGENT_SYSTEM_PROMPT_MD_HERE>>
exampleQueries:
  - naturalLanguageQuestion: "<<INSERT_PROMPT_TO_MATCH_1>>"
    sqlQuery: |
      <<INSERT_SQL_QUERY_1>>
  - naturalLanguageQuestion: "<<INSERT_PROMPT_TO_MATCH_2>>"
    sqlQuery: |
      <<INSERT_SQL_QUERY_2>>
  # ... insert all queries extracted from agent_golden_queries.md
---