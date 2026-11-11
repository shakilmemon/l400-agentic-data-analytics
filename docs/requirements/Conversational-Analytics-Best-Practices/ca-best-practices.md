# Best Practices: Setting Up a Conversational Analytics (CA) Agent in BigQuery

**Overview:** 
Conversational Analytics (CA) enables users to ask natural language questions about data and receive answers without writing a single query. An agent acts as a scoped analytics contract between a data domain and an audience. It defines the data, business context, instructions, and behavioral rules.

## 1. Data Foundation
The quality of a CA agent is strictly bounded by the quality of its underlying data. No amount of instruction tuning compensates for a poorly modeled or ambiguously annotated dataset. 

* **Use Analytics-Ready, Gold Layer Tables:** Direct agents toward high-quality, clean tables that require no additional data transformation.
* **Pre-Join Complex Data:** Whenever feasible, consolidate related tables into views prior to agent integration. This removes the need for the agent to independently determine complicated JOIN paths and enhances SQL generation accuracy.
* **Scalable Metadata Management:**
  * Ensure table and column descriptions are centralized (e.g., via a data catalog). Automated metadata propagation seamlessly integrates this into the agent's context.
  * Conduct data profiling prior to agent configuration. Analyzing null rates, value distributions, and column cardinality helps identify which fields require detailed descriptions or data sampling.
  * *Note on Precedence:* Manual overrides applied during agent setup take priority over existing catalog metadata, but do not automatically update the source system.

## 2. Agent Scope
Attempting to create a single, all-encompassing agent is a common but costly error. Broad scope frequently results in instructional conflicts, ambiguous outputs, and inconsistent performance.

**Indicators of Excessive Agent Scope:**
* The configuration requires too many tables (aim to stay well under the maximum limit; ideally fewer than 20 core tables).
* Metrics lack unified definitions (e.g., "revenue" is calculated differently by Sales and Finance).
* Instructions become contradictory in an attempt to cover all scenarios.
* Accuracy for one business unit comes at the expense of another's requirements.

## 3. Instruction Authoring
Instructions embed your organization's analytical rules, specialized vocabulary, and business logic into the agent. 

**Fundamental Rule: Structured context is superior to prose context.**

### Context Priority 
1. **Verified Queries (1st Priority):** Deterministic SQL that executes when a user prompt matches. The most reliable way to encode metric calculations and analytical examples.
2. **Glossaries (2nd Priority):** Structured, column-linked semantic context used to define terms and interpret user prompts.
3. **Agent Instructions (3rd Priority):** Global behavioral rules, fiscal calendar definitions, formatting defaults, and clarification triggers (brief prose context with no SQL or Glossary equivalent).

### 3.1 Verified Queries
Verified queries provide deterministic SQL execution and are the ideal location for ensuring calculation consistency. 
* **Type 1: Metric Definition Queries:** Translates conceptual glossary terms into exact technical SQL logic based on your specific schema. 
* **Type 2: Analytical Example Queries:** Instructional templates for addressing complex business inquiries. They guide the agent on appropriate JOIN paths, aggregation methods, and filtering logic. 
  * *Requirements:* Must include a natural language prompt reflecting how users phrase questions, paired with thoroughly validated SQL.
  * *Ideal Candidates:* High-frequency questions, prompts requiring complex JOIN logic across several tables, inquiries with unique date filters, or cases where the agent previously provided inaccurate answers.

### 3.2 Glossaries
* **Only use for concepts:** Glossaries must *only* contain conceptual definitions and synonyms. They should **never** contain SQL.
* **Maintain single sources of truth:** Use enterprise-wide catalog glossaries for shared metrics to ensure cross-agent consistency. Use custom, agent-specific glossaries for strictly domain-specific needs.

### 3.3 Agent Instructions
**Appropriate use cases for text instructions:**
* Fiscal calendar definitions.
* Formatting rules (e.g., rounding precision, currency symbols, date display format, null handling).
* Clarification triggers (defining when the agent should ask for more information rather than assuming).

**Inappropriate use cases (Do NOT use instructions for):**
* Defining how to compute a metric in SQL.
* Describing JOIN logic between tables.
* Replicating a definition already living in a glossary.

**Rules for Writing Instructions:**
* **Keep it succinct and specific.** Vague instructions lead to inconsistent behavior.
  * *Instead of:* "Ask clarifying questions about the data."
  * *Write:* "When users ask about sales without specifying product line or region, ask: 'To calculate sales accurately, please specify the product line and region you are interested in.'"
  * *Instead of:* "Use the fiscal calendar."
  * *Write:* "Fiscal calendar begins Feb 1. FY 26 = Feb 1st, 2026 to Jan 31st, 2027. All date filters referencing 'this year' or 'current year' should use the fiscal year definition unless the user explicitly says calendar year."
* **Never let an instruction contradict a verified query’s behavior.**

## 4. Anti-Patterns to Avoid

* **The Omnibus Agent:** Building one agent to serve Finance, Sales, and Operations simultaneously. Metric definitions will conflict, instructions will become unwieldy, and maintenance will become impossible.
* **Text Instructions as SQL Substitutes:** Writing text instructions to describe query logic (e.g., *"When asked about revenue, always filter out internal accounts by excluding customer_type = 'internal'"*). The reliability of SQL applied this way degrades over conversation length. Use verified queries instead.
* **Ignoring Column Descriptions:** Relying on the model to infer meaning from column names alone. Names like ‘status’, ‘type’, ‘value’, and ‘id’ are ambiguous. The model will pick the wrong column, looking like an AI failure when it is actually a metadata gap.
* **Duplicating Glossary Definitions in Instructions:** Defining a term in both the Glossary and the Agent Instructions creates two sources of truth. When the business definition inevitably changes, the agent instructions will become stale and silently override the correct definition.