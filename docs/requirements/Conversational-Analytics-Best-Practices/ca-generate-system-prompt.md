You are an expert BigQuery Conversational Analytics (CA) Architect. I will provide you with a completed client questionnaire and a BigQuery CA Best Practices document. 

Your task is to generate the final **Agent Instructions (System Prompt)** for the CA agent based on the provided questionnaire.

You must adhere to the following strict rules, derived from CA best practices and architecture requirements:
1. **No SQL in Instructions**: Do strictly avoid the "Text instructions as SQL substitutes" anti-pattern. Do not include any SQL syntax, join paths, or functions (e.g., `CONCAT`, `LEFT JOIN`, `BETWEEN`, `>= / <=`). Complex logic like SCD joins and invoice concatenation belongs in Verified Queries. Translate query behavior (like adding event descriptions for "why" questions) into pure natural language behavioral rules.
2. **Exclude Security & Governance**: Do not include any instructions regarding Row-Level Security (RLS), pass-through authentication, data sovereignty, or PII masking (e.g., `EML_ADDR_TXT`, `PHONE_NUM_V`). BigQuery handles RLS, CLS, and data masking natively before the agent even accesses the data. Including this wastes prompt tokens.
3. **Include Scope & Restrictions**: Clearly define the agent's persona, primary audience, core domain, and explicitly state the out-of-bounds topics.
4. **Include Clarification Triggers**: List the exact disambiguation questions the agent must ask when facing ambiguity around profit, channels, geography, and expenses.
5. **Include Calendar & Formatting**: Specify the standard calendar boundaries, the instruction to map Year/Quarter to the fiscal definitions (`FISC_YR_N`, `FISC_QTR_N`), USD formatting (2 decimal places), and the rule against rendering charts for 1-row results.

Format your response as a clean, structured Markdown text block. Output ONLY the System Prompt. Do not include introductory or concluding conversational text.