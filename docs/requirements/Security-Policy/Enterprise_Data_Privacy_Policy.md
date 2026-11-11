# Premium Outdoor Gear Inc. 
## Enterprise Data Privacy & Governance Policy
**Document ID:** SEC-POL-2026-v4
**Effective Date:** January 1, 2026
**Applies To:** Global Data Analytics, IT, and AI Engineering Teams

---

### Executive Summary
To comply with the General Data Protection Regulation (GDPR), the California Consumer Privacy Act (CCPA), and internal corporate governance, strict access controls must be applied to our cloud data warehouse. All analytics environments, including AI-driven Conversational Analytics (CA) agents, must enforce Column-Level Security (Data Masking) and Row-Level Security (Data Sovereignty) at the database execution layer.

---

### Section 1: Personally Identifiable Information (PII) Masking
Direct-to-Consumer (D2C) data contains highly sensitive customer information. To prevent unauthorized exposure, specific data elements must be protected using **BigQuery Policy Tags** and **Data Masking Rules**.

**Target Table:** `l400_agentic_da.CUST_MSTR_D2C`

**Classification & Masking Rules:**
The following columns are classified as **High-Risk PII** and require a masking policy under a unified "Customer_PII" taxonomy:
1. **Customer Email (`EML_ADDR_TXT`):** Must be masked using a Default Masking Value (e.g., replacing the output with `***@***.***` or `NULL`) for all standard business users.
2. **Customer Phone Number (`PHONE_NUM_V`):** Must be masked using a Default Masking Value for all standard business users.

**Access Exceptions:** 
Only users assigned to the IAM Role `roles/datacatalog.categoryFineGrainedReader` (Executive Leadership and Data Stewards) are permitted to view the unmasked, plaintext values of these columns. 

---

### Section 2: Regional Data Sovereignty (Row-Level Security)
Due to strict international trade and data processing laws, our wholesale financial data must be segregated by geographic territory. Analysts, reporting tools, and AI agents are strictly prohibited from querying or viewing wholesale sales data outside of their assigned territory.

**Target Tables:** 
Row-Level Security (RLS) must be applied to the following tables using the `REG_ID_CD` column:
*   `l400_agentic_da.SLS_ORD_HDR`
*   `l400_agentic_da.DIST_ACCT_MSTR`
*   `l400_agentic_da.SLS_REP_QUOTA`

**Sovereignty Mappings:**
Access policies must be strictly mapped to the following region codes:
*   **North America (NorthAm) Team:** Authorized to view ONLY `REG_ID_CD = 'R_01'`
*   **Europe, Middle East, & Africa (EMEA) Team:** Authorized to view ONLY `REG_ID_CD = 'R_02'` OR `REG_ID_CD = 'R_03'`
*   **Asia-Pacific (APAC) Team:** Authorized to view ONLY `REG_ID_CD = 'R_04'`

*Note: Global CFOs and Executive Leadership are exempt from these RLS policies and retain global read access.*

---

### Section 3: AI & Conversational Analytics Guardrails
To ensure AI deployments do not inadvertently bypass the security measures outlined in Sections 1 and 2, all Generative AI tools and Natural Language to SQL (NL2SQL) agents must adhere to the following architecture:

1. **No Service Account Escalation:** Conversational Analytics agents must **never** execute queries using a highly privileged, global service account.
2. **Pass-Through Authentication:** All agents deployed via Gemini Enterprise or custom web applications must utilize **OAuth Pass-Through Authentication**. The underlying BigQuery engine must execute the generated SQL using the identity of the end-user asking the question. 

Failure to configure pass-through authentication will result in the immediate suspension of the AI project by the Information Security team.