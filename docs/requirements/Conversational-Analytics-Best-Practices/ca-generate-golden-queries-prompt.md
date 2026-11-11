You are an autonomous BigQuery Conversational Analytics (CA) Architect. Your task is to analyze the provided project documentation and generate the complete list of "Golden Queries" (Verified Queries) required to successfully deploy this CA agent.

You will be provided with:
1. The Completed Client Questionnaire.
2. The CA Best Practices document.
3. Open Knowledge Format (OKF) markdown files (Tables, Metrics, and Glossaries).

**Step 1: Metric Iteration (1-to-1 Mapping)**
Review the provided OKF Metric files. **You must generate exactly ONE Golden Query for EACH individual OKF Metric file provided.** Do not skip any metrics, and do not combine multiple metrics into a single query block. 

**Step 2: Golden Query Generation**
For each metric, translate the provided legacy SQL or Tableau logic into optimized, standard BigQuery SQL. Format your output as a Markdown document. For each query, you must provide:
- A categorization (Type 1: Metric Definition OR Type 2: Analytical Example) based on the Best Practices document.
- A "Prompt to Match" (a realistic natural language question a user would ask).
- The optimized BigQuery SQL statement.

**Step 3: Apply Mandatory Guardrails (Where Applicable)**
While generating the SQL for each metric, you must autonomously apply the following architectural constraints if the metric touches these specific data domains:
- **SCD Joins:** If the metric involves the `PRD_COGS_FCT` table, you must apply Slowly Changing Dimension (SCD) join logic using `CAL_DT >= EFF_DT` and `CAL_DT <= END_DT`.
- **String Concat:** If the metric involves invoices (`B2B_INV_AGING`), you must join it to the order header using `CONCAT('INV-', hdr.ORD_NO_SYS)`.
- **Security:** If the metric queries D2C customer data (`CUST_MSTR_D2C`), you must autonomously mask PII columns (like `EML_ADDR_TXT`) using SQL string manipulation, per the out-of-bounds security requirements.

**Step 4: The Qualitative Overlay (Standalone Query)**
In addition to the OKF metrics, you must generate ONE standalone Type 2 Analytical Example that teaches the agent how to answer "why" trends changed. This query must demonstrate how to `LEFT JOIN` the `dim_business_events` table using `CAL_DT BETWEEN Event_Start_Date AND Event_End_Date` to pull in the `Event_Description`.

Generate the final Golden Queries document now.