
# PART 1: The General Interview Guide & Questionnaire
*Use this framework to interview business stakeholders. The goal is to extract the exact boundaries, behaviors, and math required to build a highly accurate, scoped CA Agent, avoiding the "Omnibus" (one-agent-for-everything) anti-pattern.*

### Section 1: Agent Scoping & Audience (Defeating the Omnibus)
*Tip: CA Agents are limited to 50 tables, but the real limit is semantic conflict. Sales and Finance often calculate "Revenue" differently. Force the customer to pick ONE domain per agent.*
*   **1.1 Target Audience:** Who is the primary end-user of this specific agent? (e.g., Regional Sales Managers, the CFO, Supply Chain Analysts).
*   **1.2 Core Domain:** What is the single business domain this agent is responsible for? (e.g., Q3 Financial Reporting, B2B Sales Pipeline).
*   **1.3 Out-of-Bounds:** What questions should this agent explicitly *refuse* to answer or redirect? (e.g., "Do not answer HR or payroll questions.")

### Section 2: Data Foundation & Artifacts (Tables)
*Tip: We need to know where the truth lives. Do not let them point the agent at 50 raw, unjoined landing tables if a clean "Gold View" exists.*
*   **2.1 Table Sources:** Which specific BigQuery datasets/tables contain the "Gold Layer" data for this domain? 
*   **2.2 Artifact Harvesting:** Do you have existing Data Dictionaries, Glossaries, or Executive Memos (PDFs) that explain this data? 
*   **2.3 Semantic Conflicts:** Are there columns in these tables with ambiguous names (e.g., `status`, `type`, `value`) that we need to explicitly define in our Dataplex mapping?

### Section 3: The "Hard Math" & Golden Queries
*Tip: LLMs cannot guess complex corporate math. If a calculation requires >2 tables or specific IF/THEN logic, we must extract it into a Type 1 or Type 2 Verified Query.*
*   **3.1 Top 5 KPIs:** What are the 5 most common metrics your users will ask about? (e.g., Net-New ARR, Inventory Turn Ratio).
*   **3.2 Legacy Logic Extraction:** Are these metrics currently calculated in a Tableau dashboard, Looker, or legacy SQL scripts (SSRS/Oracle)? *(Action: Request export of these files to extract the SQL).*
*   **3.3 Reporting Nuances:** Are there any Slowly Changing Dimensions (SCDs) or specific string manipulations (like concatenating 'INV-' to order numbers) required to join your tables?

### Section 4: Ambiguity & Clarification Triggers (System Prompt)
*Tip: Users ask lazy questions. We must program the agent to pause and ask for missing parameters instead of hallucinating a filter.*
*   **4.1 The "Lazy" Prompt:** When your users ask, *"How did we do last month?"*, what missing details do you usually have to ask them for? 
*   **4.2 Categorical Triggers:** 
    *   *Geography:* If they ask for "Sales", do we assume Global, or should the agent ask: *"Which Region?"*
    *   *Divisions/Channels:* If they ask for "Revenue", should the agent ask: *"Are you asking for Wholesale or Retail?"*
    *   *Financials:* If they ask for "Profit", should the agent ask: *"Gross, Operating, or Net?"*
*   **4.3 Default Assumptions:** Are there any safe defaults? (e.g., "If they don't specify currency, assume USD.")

### Section 5: Calendar, Formatting, & Context (System Prompt)
*   **5.1 Time Boundaries:** How does your Fiscal Year run? (e.g., "Jan 1 to Dec 31").
*   **5.2 Date Language:** When a user says "This Year," do they mean Calendar Year or Fiscal Year?
*   **5.3 Formatting Rules:** How should numbers be displayed? (e.g., "Round to 2 decimals, display as currency").
*   **5.4 Qualitative Overlays:** Do you have business memos or market alerts that explain *why* numbers spiked/dipped? How should the agent weave these into answers?

### Section 6: Security & Governance (Light Touch)
*   **6.1 PII Masking:** Are there columns (like Email or SSN) that standard users shouldn't see? *(Action: Apply BQ Policy Tags).*
*   **6.2 Data Sovereignty (RLS):** Should EMEA analysts be blocked from seeing NorthAm revenue? *(Action: Apply Row-Level Security).*
