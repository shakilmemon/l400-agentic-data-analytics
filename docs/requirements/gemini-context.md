**Project Overview:**
We are building a highly realistic, hands-on lab to train Google Cloud Data Analytics Customer Engineers (CEs) in "Expert Agentic Skills." In this scenario, CEs are tasked with deploying a Conversational Analytics (NL2SQL) agent for the CFO of a fictional manufacturing and retail company ("Premium Outdoor Gear Inc."). To succeed, CEs cannot simply point the LLM at the raw database, which is intentionally designed as a messy, cryptic legacy ERP schema. Instead, they must practice "Intent-Driven Engineering" by using the Data Agent Kit (Antigravity) to parse unstructured enterprise artifacts—including PDF security policies, Director-level memos, legacy Oracle SQL scripts, and Tableau/SSRS XML files. By extracting semantic glossaries, security rules, and complex "Golden Queries" from these files, the CE will build a robust semantic layer in Dataplex and configure a BigQuery CA agent capable of flawlessly executing complex financial math, enforcing Row-Level Security, asking clarifying questions, and blending quantitative metrics with qualitative business explanations. The final deployment is automatically graded against a rigorous 20-prompt evaluation suite.

# FULL CONTEXT: Conversational Analytics Lab Architecture
**Domain:** Premium Outdoor Gear Inc. (Manufacturing, D2C, and Wholesale B2B)
**Database:** `l400_agentic_da` (BigQuery)

## 1. THE DATA DICTIONARY (Table & Column Descriptions)
*This is the schema of the legacy ERP system. The CA agent relies on these descriptions to understand the raw tables.*

### Finance & Accounting Tables
*   **`GL_ACCT_MSTR`** (Chart of accounts defining financial categories)
    *   `ACCT_ID_X`: Unique alphanumeric identifier for the GL account (e.g., GL1000).
    *   `ACCT_NM_STR`: Human-readable name (e.g., Gross Revenue, COGS, Payroll).
    *   `BAL_SHT_FLG`: Flag indicating Balance Sheet (1) or Income Statement (0).
    *   `ACT_INACT_IND`: Indicator showing Active ('A') or Inactive ('I').
*   **`GL_F_TRX_00`** (Core financial fact table for debits/credits)
    *   `TRX_ID_N`: Unique transaction ID.
    *   `ACCT_ID_X`: General Ledger account ID mapped to this transaction.
    *   `POST_DT_SK`: Surrogate integer date key (YYYYMMDD).
    *   `DR_CR_IND`: Indicator for Debit ('D') or Credit ('C').
    *   `AMT_BASE`: Base monetary amount in USD.
    *   `SRC_SYS_CDE`: Source system (e.g., 'SLS', 'INV', 'HR').
*   **`FIN_OPEX_DTL`** (Line-item details of Operating Expenses)
    *   `EXP_ID`: Unique identifier for the expense record.
    *   `DEPT_CD`: Department code (e.g., 'MKTG', 'SALES').
    *   `SPND_TYP_IND`: Integer code representing spend category.
    *   `AMT`: Total monetary amount in USD.
    *   `POST_DT`: Calendar date the expense was incurred.

### Date Dimensions
*   **`SYS_CAL_DIM`** (Corporate date dimension mapping to fiscal periods)
    *   `DT_SK`: Integer surrogate key (YYYYMMDD).
    *   `CAL_DT`: Standard calendar date (DATE format).
    *   `FISC_YR_N`: Corporate Fiscal Year (Jan 1 - Dec 31).
    *   `FISC_QTR_N`: Corporate Fiscal Quarter (1-4).
    *   `FISC_PER_N`: Specific month number of the fiscal year.

### Sales & Orders
*   **`SLS_ORD_HDR`** (Header-level fact table for sales transactions)
    *   `ORD_NO_SYS`: Unique system-generated Order Number.
    *   `CUST_NUM_ID`: D2C Customer ID. NULL if B2B.
    *   `DIST_ACCT_ID`: Wholesale Distributor Account ID. NULL if D2C.
    *   `ORD_DT_SID`: Surrogate integer date key.
    *   `CHN_FLG`: Integer flag for sales channel (1 = D2C, 2 = Wholesale).
    *   `STS_CDE`: Order fulfillment status ('O'=Open, 'C'=Closed, 'V'=Voided).
*   **`SLS_ORD_DTL_LN`** (Line-item details for sales orders)
    *   `ORD_NO_SYS`: Parent Order Number.
    *   `LN_NO_N`: Specific line number.
    *   `PRD_SKU_CD`: Unique Product SKU.
    *   `QTY_N`: Quantity purchased.
    *   `UNIT_PRC_AMT`: Base unit price in USD.
    *   `DISC_PCT_N`: Discount percentage applied.
*   **`SLS_RTN_LOGS_V2`** (Product returns, refunds, and defect reasons)
    *   `RTN_AUTH_ID`: Unique Return Authorization ID.
    *   `ORD_NO_SYS`: Original Order Number.
    *   `PRD_SKU_CD`: Product SKU returned.
    *   `RTN_DT`: Date return was processed.
    *   `RSN_CDE_N`: Return reason code (1=Defective, 2=Wrong Size, 3=Changed Mind).
    *   `RFN_AMT`: Monetary amount refunded in USD.
*   **`B2B_INV_AGING`** (B2B invoices issued to Wholesale Distributors)
    *   `INV_NUM_X`: Unique Invoice Number (Prepended 'INV-' to ORD_NO_SYS).
    *   `DIST_ACCT_ID`: Wholesale Distributor Account ID.
    *   `ISSUE_DT`: Date invoice was generated.
    *   `PAID_DT`: Date invoice was paid in full.
    *   `AMT_DUE`: Total amount due in USD.
    *   `STS_FLG`: Payment status (0=Open, 1=Paid, 9=Default).

### Customers, Geos, & Channels
*   **`CUST_MSTR_D2C`** (PII and profile data for D2C customers)
    *   `CUST_NUM_ID`: Unique identifier for D2C customer.
    *   `F_NM` / `L_NM`: First/Last Name.
    *   `EML_ADDR_TXT`: Email Address (High-Risk PII).
    *   `PHONE_NUM_V`: Phone Number (High-Risk PII).
    *   `ACQ_DT`: Date of first purchase.
    *   `OPT_IN_FLG`: Marketing opt-in flag (1=Yes, 0=No).
*   **`DIST_ACCT_MSTR`** (Profile data for B2B Wholesale Distributors)
    *   `DIST_ACCT_ID`: Unique identifier for Wholesale Distributor.
    *   `CO_NM_TXT`: Legal company name.
    *   `REG_ID_CD`: Geographic Region ID.
    *   `ONBRD_DT`: Date B2B partnership agreement signed.
*   **`GEO_REG_HIER`** (Geographic hierarchy mapping)
    *   `REG_ID_CD`: Unique Region ID code (e.g., 'R_01').
    *   `CTRY_CD`: Country Code.
    *   `RGN_NM_TXT`: Macro global region name (NorthAm, EMEA, APAC).
    *   `SUB_RGN_TXT`: Specific sub-region (e.g., West Coast).
*   **`CUST_FEEDBACK_FCT`** (Customer reviews and feedback)
    *   `FDBK_ID_X`: Unique identifier for feedback.
    *   `CUST_NO_X`: D2C Customer ID (Maps to CUST_NUM_ID).
    *   `PRD_SKU_CD`: Product SKU reviewed.
    *   `SUB_DT`: Date submitted.
    *   `RTG_N`: Star rating (1 to 5).
    *   `VLD_FLG`: Verified purchaser flag ('Y' or 'N').

### Products & Supply Chain
*   **`PRD_MSTR_CAT`** (Product master dimension)
    *   `PRD_SKU_CD`: Unique Stock Keeping Unit.
    *   `PRD_NM_TXT`: Formal product name.
    *   `CAT_CDE_N` / `SUB_CAT_CDE_N`: Category/Sub-category integer codes.
    *   `LCH_DT`: Product launch date.
*   **`PRD_CAT_DEF`** (Translates numeric categories to descriptions)
    *   `CAT_CDE_N`: Integer category code.
    *   `CAT_DESC_TXT`: Description (e.g., Bikes, Outerwear).
*   **`PRD_COGS_FCT`** (Slowly Changing Dimension for Cost of Goods Sold)
    *   `PRD_SKU_CD`: Product SKU.
    *   `EFF_DT` / `END_DT`: Effective and End dates for these costs.
    *   `MTL_CST_AMT`: Raw material manufacturing cost (USD).
    *   `LBR_CST_AMT`: Manual labor/assembly cost (USD).
    *   `TRFF_AMT`: International tariffs (USD).
*   **`INV_WHSE_FCT`** (Weekly snapshot of physical inventory)
    *   `WHSE_LOC_CD`: Warehouse facility ID.
    *   `PRD_SKU_CD`: Product SKU.
    *   `SNAP_DT`: Date snapshot was taken.
    *   `QTY_ON_HND_N`: Physical quantity on-hand.
*   **`VNDR_SPLY_MSTR`** (External vendors supplying raw materials)
    *   `VNDR_ID_C`: Vendor ID.
    *   `VNDR_NM`: Vendor legal name.
    *   `MTL_TYP_CD`: Material supplied ('ALUM', 'CRBN').

### HR & Operations
*   **`HR_EMP_MSTR`** (Employee directory)
    *   `EMP_ID_N`: Employee ID.
    *   `EMP_NM`: Employee full name.
    *   `DEPT_CD`: Department code ('SALES', 'MKTG').
    *   `HIRE_DT`: Date hired.
*   **`SLS_REP_QUOTA`** (Quarterly sales targets)
    *   `EMP_ID_N`: Employee ID.
    *   `REG_ID_CD`: Region ID assigned.
    *   `QTR_TXT`: Target quarter string ('2024-Q1').
    *   `QTA_AMT`: Sales target amount in USD.
*   **`dim_business_events`** (Extracted via ML from unstructured PDFs)
    *   Contains columns: `Event_Month`, `Affected_Division`, `Event_Description`.

---

## 2. THE UNIFIED CORPORATE GLOSSARY (Dataplex Semantic Mapping)
*This maps business terms to exactly what they mean and the specific tables/columns they rely on to calculate.*

### 1. Channel Definitions
*   **D2C (Direct-to-Consumer):** Sales originating from our owned retail website. Mapped to `SLS_ORD_HDR.CHN_FLG` = 1.
*   **Wholesale:** B2B sales to external retailers. Mapped to `SLS_ORD_HDR.CHN_FLG` = 2.
*   **Distributor:** A registered B2B wholesale partner. Mapped to `DIST_ACCT_MSTR`.

### 2. Customer & Product Terminology
*   **Certified Field Tester:** An apex D2C customer purchasing across 3+ categories, 2+ reviews, 0 returns. Mapped to `CUST_MSTR_D2C`.
*   **Tier 1 Distributor:** A wholesale partner with >$250k volume, 3+ categories, paying in < 30 days. Mapped to `DIST_ACCT_MSTR`.
*   **SKU (Stock Keeping Unit):** Mapped to `PRD_MSTR_CAT.PRD_SKU_CD`.
*   **Product Category:** Mapped to `PRD_CAT_DEF.CAT_DESC_TXT`.
*   **MAP (Minimum Advertised Price):** The lowest price a distributor can advertise. Mapped to `SLS_ORD_DTL_LN.UNIT_PRC_AMT`.
*   **MSRP (Manufacturer’s Suggested Retail Price):** The standard list price. Mapped to `SLS_ORD_DTL_LN.UNIT_PRC_AMT`.

### 3. Supply Chain Terminology
*   **On-Hand Inventory:** Physical count of SKU in warehouses. Mapped to `INV_WHSE_FCT.QTY_ON_HND_N`.
*   **Lead Time:** Days between placing a PO and material arriving. Mapped to `VNDR_SPLY_MSTR`.
*   **Backorder:** Order placed with zero On-Hand Inventory. Mapped to `INV_WHSE_FCT.QTY_ON_HND_N`.
*   **Defect Rate:** Units returned due to manufacturing defects. Mapped to `SLS_RTN_LOGS_V2.RSN_CDE_N` = 1.
*   **Raw Materials:** Core supplies purchased. Mapped to `PRD_COGS_FCT.MTL_CST_AMT`.
*   **Drop-Ship:** Shipping directly to distributor's customer. Mapped to `SLS_ORD_HDR`.

### 4. Financial & Revenue Metrics
*   **Gross Revenue:** Top-line sales before discounts/returns. Mapped to `SLS_ORD_DTL_LN`.
*   **Net Revenue:** Gross Revenue minus discounts and refunds. Mapped to `SLS_ORD_DTL_LN`.
*   **AOV (Average Order Value):** Net Revenue divided by distinct orders. Mapped to `SLS_ORD_DTL_LN`.
*   **EBIDA:** Earnings Before Interest, Depreciation, Amortization. Mapped to `GL_F_TRX_00`.
*   **Net Profit:** Gross Margin minus OPEX, taxes, interest. Mapped to `GL_F_TRX_00`.
*   **ARR (Annual Recurring Revenue):** Annualized value of maintenance contracts. Mapped to `GL_F_TRX_00`.
*   **Net-New ARR:** ARR gained minus ARR lost. Mapped to `GL_F_TRX_00`.
*   **Churn Rate:** Loss of recurring revenue contracts. Mapped to `GL_F_TRX_00`.
*   **OPEX (Operating Expenses):** Indirect costs. Mapped to `FIN_OPEX_DTL`.
*   **COGS (Cost of Goods Sold):** Direct production costs. Mapped to `PRD_COGS_FCT`.
*   **Gross Margin:** Net Revenue minus COGS. Mapped to `PRD_COGS_FCT`.
*   **DSO (Days Sales Outstanding):** Average days for wholesale invoice payment. Mapped to `B2B_INV_AGING.ISSUE_DT` and `PAID_DT`.
*   **Aging Invoices:** Unpaid issued invoices. Mapped to `B2B_INV_AGING`.

### 5. Column Definitions & System Flags
*   **CLV / LTV (Customer Lifetime Value):** Total historical Net Revenue. Mapped to `CUST_MSTR_D2C.CUST_NUM_ID`.
*   **CAC (Customer Acquisition Cost):** Marketing OPEX divided by net-new customers. Mapped to `CUST_MSTR_D2C.ACQ_DT` and `FIN_OPEX_DTL.DEPT_CD`.
*   **Pipeline:** Projected revenue of unclosed deals. Mapped to `SLS_ORD_HDR.STS_CDE` = 'O'.
*   **FISC_YR_N:** Corporate financial reporting year. Mapped to `SYS_CAL_DIM.FISC_YR_N`.

---

## 3. UNSTRUCTURED DATA DOCUMENTS
*These Markdown documents are uploaded to GCS. The CE parses them using BigQuery ML / Gemini to create `dim_business_events` and apply security policies.*

### Document 1: Market Intelligence Alert (Bike Recall)
```markdown
# URGENT: Market Intelligence & Competitive Alert
**Date:** April 4, 2025
**From:** Global Competitive Intelligence Desk
**Subject:** Competitor Safety Recall - Immediate Wholesale Opportunities

Early this morning, our largest international competitor issued a mandatory, global safety recall on all of their 2024 and 2025 carbon mountain bike frames due to critical weld failures. This has created an immediate vacuum in the wholesale market. Distributors and local bike shops are panic-buying to fill their empty showroom floors ahead of the summer riding season. 
As a result, we anticipate a massive, one-time spike in Wholesale (B2B) revenue specifically for our Mountain Bike product lines throughout the month of **April 2025**. This 500% surge is a strictly opportunistic anomaly and should NOT be factored into baseline run-rate projections.
```

### Document 2: Global Supply Chain Advisory (Aluminum Shortage)
```markdown
# Global Supply Chain Advisory
**Date:** June 15, 2025
**From:** VP of Global Supply Chain & Manufacturing
**Subject:** Severe Aluminum Shortage & Q3 Gross Margin Warning

Due to sudden geopolitical export restrictions and a localized port strike, we are experiencing an unprecedented bottleneck in the global supply of raw aluminum. Our suppliers have informed us that the cost of raw aluminum will increase by 2.5x effective July 1st. 
You will see a significant, unavoidable dip in our True Gross Margins for the entirety of **Q3 2025** (July, August, and September). This margin compression will severely impact our Aluminum-heavy product lines, specifically **Bicycles** and **Tents / Tent Poles**. Supply chains normalized by October 1st, 2025.
```

### Document 3: Enterprise Data Privacy & Governance Policy
```markdown
# Premium Outdoor Gear Inc. Enterprise Data Privacy Policy
**Effective Date:** January 1, 2026
**Applies To:** Global Data Analytics & AI Engineering Teams

### Section 1: Personally Identifiable Information (PII) Masking
The following columns in `l400_agentic_da.CUST_MSTR_D2C` are High-Risk PII and require BigQuery Policy Tags and Data Masking Rules:
1. **Customer Email (`EML_ADDR_TXT`)**
2. **Customer Phone Number (`PHONE_NUM_V`)**
*Enforcement Rule:* Masked using a Default Masking Value for standard business users. Only Executive Leadership and Data Stewards may view unmasked values.

### Section 2: Regional Data Sovereignty (Row-Level Security)
Row-Level Security (RLS) must be applied to `SLS_ORD_HDR`, `DIST_ACCT_MSTR`, and `SLS_REP_QUOTA` based on `REG_ID_CD`:
*   **NorthAm Team:** May only view `REG_ID_CD = 'R_01'`
*   **EMEA Team:** May only view `REG_ID_CD = 'R_02'` OR `'R_03'`
*   **APAC Team:** May only view `REG_ID_CD = 'R_04'`

### Section 3: AI & Conversational Analytics Guardrails
All Generative AI tools and Natural Language to SQL (NL2SQL) agents must utilize **OAuth Pass-Through Authentication**. Agents must never execute queries using a highly privileged service account.
```

---

## 4. CONVERSATIONAL ANALYTICS AGENT CONFIGURATION
*The final configuration applied to the BQ Conversational Analytics Agent to pass the lab.*

### Agent Instructions (System Prompt)
```text
You are the financial and operational AI assistant for Premium Outdoor Gear Inc. Your primary users are the CFO and Executive Directors. 

**Clarification Triggers (Do not assume; always ask):**
1. If a user asks about "profit", "margin", or "bottom line" without specifying the type, ask: "Are you asking for Gross Margin, Operating Profit, or Net Profit?"
2. If a user asks about "revenue", "sales", "pipeline", or "customers" without specifying a channel, ask: "Are you looking for the Direct-to-Consumer (D2C) channel or the Wholesale (B2B) channel?"
3. If a user asks about regional performance without specifying the geography, ask: "Is this for the NorthAm, EMEA, or APAC region?"
4. If a user asks about "expenses" or "spend", ask: "Are you referring to OPEX (Operating Expenses) or COGS (Cost of Goods Sold)?"

**Formatting & Calendar Rules:**
* Always format financial figures in USD, rounded to 2 decimal places. 
* All dates, years, and quarters follow a standard Calendar Year (Jan 1 - Dec 31). Map any references to 'Year' to the FISC_YR_N column, and 'Quarter' to FISC_QTR_N.

**Qualitative Context Rules:**
* If a user asks "why" a metric changed, "what caused" a spike/dip, or asks to "explain" a trend, you must LEFT JOIN the `l400_agentic_da.dim_business_events` table based on the time period and division. Append the qualitative `event_description` from this table as a business explanation to the financial results.
```

### Golden Queries (Verified Queries)
*(Extracted from the BI Artifacts by the CE)*

**1. Tier 1 Wholesale Distributor (Type 1 Metric Definition)**
```sql
SELECT 
    reg.RGN_NM_TXT AS Region,
    COUNT(DISTINCT dist.DIST_ACCT_ID) AS Tier_1_Distributor_Count
FROM `l400_agentic_da.DIST_ACCT_MSTR` dist
JOIN `l400_agentic_da.GEO_REG_HIER` reg ON dist.REG_ID_CD = reg.REG_ID_CD
JOIN `l400_agentic_da.SLS_ORD_HDR` hdr ON dist.DIST_ACCT_ID = hdr.DIST_ACCT_ID
JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
JOIN `l400_agentic_da.PRD_MSTR_CAT` prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
LEFT JOIN `l400_agentic_da.B2B_INV_AGING` inv ON CONCAT('INV-', hdr.ORD_NO_SYS) = inv.INV_NUM_X
GROUP BY dist.DIST_ACCT_ID, reg.RGN_NM_TXT
HAVING SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) > 250000 
   AND COUNT(DISTINCT prd.CAT_CDE_N) >= 3 
   AND AVG(DATE_DIFF(COALESCE(inv.PAID_DT, CURRENT_DATE()), inv.ISSUE_DT, DAY)) < 30
```

**2. Certified Field Tester (Type 1 Metric Definition)**
```sql
SELECT 
    c.CUST_NUM_ID, c.F_NM, c.L_NM, c.EML_ADDR_TXT
FROM `l400_agentic_da.CUST_MSTR_D2C` c
JOIN `l400_agentic_da.SLS_ORD_HDR` hdr ON c.CUST_NUM_ID = hdr.CUST_NUM_ID
JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
JOIN `l400_agentic_da.PRD_MSTR_CAT` prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
LEFT JOIN `l400_agentic_da.CUST_FEEDBACK_FCT` fb ON c.CUST_NUM_ID = fb.CUST_NO_X
LEFT JOIN `l400_agentic_da.SLS_RTN_LOGS_V2` rtn ON hdr.ORD_NO_SYS = rtn.ORD_NO_SYS
GROUP BY c.CUST_NUM_ID, c.F_NM, c.L_NM, c.EML_ADDR_TXT
HAVING SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) > 1000
   AND COUNT(DISTINCT prd.CAT_CDE_N) >= 3
   AND COUNT(DISTINCT CASE WHEN DATE_DIFF(CURRENT_DATE(), fb.SUB_DT, DAY) <= 365 THEN fb.FDBK_ID_X END) >= 2
   AND COUNT(DISTINCT CASE WHEN DATE_DIFF(CURRENT_DATE(), rtn.RTN_DT, DAY) <= 90 THEN rtn.RTN_AUTH_ID END) = 0
```

**3. True Gross Margin - SCD Override (Type 2 Analytical Example)**
```sql
SELECT 
    cal.FISC_YR_N AS FiscalYear,
    cal.FISC_QTR_N AS FiscalQuarter,
    prd.PRD_NM_TXT AS Product,
    SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) - SUM(ln.QTY_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)) AS GrossMargin
FROM `l400_agentic_da.SLS_ORD_HDR` hdr
JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
JOIN `l400_agentic_da.PRD_MSTR_CAT` prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
JOIN `l400_agentic_da.SYS_CAL_DIM` cal ON hdr.ORD_DT_SID = cal.DT_SK
JOIN `l400_agentic_da.PRD_COGS_FCT` cogs ON prd.PRD_SKU_CD = cogs.PRD_SKU_CD
    AND cal.CAL_DT >= cogs.EFF_DT 
    AND cal.CAL_DT <= cogs.END_DT
WHERE hdr.STS_CDE = 'C'
GROUP BY 1, 2, 3
```

**4. Wholesale Aging - String Concat Override (Type 2 Analytical Example)**
```sql
SELECT 
    reg.RGN_NM_TXT AS Region,
    SUM(inv.AMT_DUE) AS Total_Aging_Amount_Due
FROM `l400_agentic_da.DIST_ACCT_MSTR` dist
JOIN `l400_agentic_da.GEO_REG_HIER` reg ON dist.REG_ID_CD = reg.REG_ID_CD
JOIN `l400_agentic_da.SLS_ORD_HDR` hdr ON dist.DIST_ACCT_ID = hdr.DIST_ACCT_ID
JOIN `l400_agentic_da.B2B_INV_AGING` inv ON CONCAT('INV-', hdr.ORD_NO_SYS) = inv.INV_NUM_X
WHERE inv.STS_FLG = 0 
GROUP BY 1
```

**5. Blended D2C CAC (Type 1 Metric Definition)**
```sql
SELECT 
    cal.FISC_YR_N AS FiscalYear,
    cal.FISC_QTR_N AS FiscalQuarter,
    (SELECT SUM(AMT) FROM `l400_agentic_da.FIN_OPEX_DTL` opex
     JOIN `l400_agentic_da.SYS_CAL_DIM` sub_cal ON opex.POST_DT = sub_cal.CAL_DT
     WHERE opex.DEPT_CD = 'MKTG' AND sub_cal.FISC_YR_N = cal.FISC_YR_N AND sub_cal.FISC_QTR_N = cal.FISC_QTR_N) / 
    (SELECT COUNT(CUST_NUM_ID) FROM `l400_agentic_da.CUST_MSTR_D2C` cust
     JOIN `l400_agentic_da.SYS_CAL_DIM` sub_cal ON cust.ACQ_DT = sub_cal.CAL_DT
     WHERE sub_cal.FISC_YR_N = cal.FISC_YR_N AND sub_cal.FISC_QTR_N = cal.FISC_QTR_N) AS Blended_D2C_CAC
FROM `l400_agentic_da.SYS_CAL_DIM` cal
GROUP BY 1, 2
```

**6. Inventory Turn Ratio (Type 1 Metric Definition)**
```sql
WITH TotalCOGS AS (
    SELECT cal.FISC_YR_N, SUM(ln.QTY_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)) AS COGS_Value
    FROM l400_agentic_da.SLS_ORD_HDR hdr
    JOIN l400_agentic_da.SLS_ORD_DTL_LN ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
    JOIN l400_agentic_da.SYS_CAL_DIM cal ON hdr.ORD_DT_SID = cal.DT_SK
    JOIN l400_agentic_da.PRD_COGS_FCT cogs ON ln.PRD_SKU_CD = cogs.PRD_SKU_CD AND cal.CAL_DT >= cogs.EFF_DT AND cal.CAL_DT <= cogs.END_DT
    WHERE hdr.STS_CDE = 'C' GROUP BY 1
),
AvgInventory AS (
    SELECT cal.FISC_YR_N, AVG(wh.QTY_ON_HND_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)) AS Avg_Inv_Value
    FROM l400_agentic_da.INV_WHSE_FCT wh
    JOIN l400_agentic_da.SYS_CAL_DIM cal ON wh.SNAP_DT = cal.CAL_DT
    JOIN l400_agentic_da.PRD_COGS_FCT cogs ON wh.PRD_SKU_CD = cogs.PRD_SKU_CD AND cal.CAL_DT >= cogs.EFF_DT AND cal.CAL_DT <= cogs.END_DT
    GROUP BY 1
)
SELECT c.FISC_YR_N AS FiscalYear, c.COGS_Value / NULLIF(i.Avg_Inv_Value, 0) AS Inventory_Turn_Ratio
FROM TotalCOGS c JOIN AvgInventory i ON c.FISC_YR_N = i.FISC_YR_N;
```

---

## 5. THE 20-PROMPT EVALUATION SUITE
*These 20 questions are fed into the LLM-as-a-judge framework to score the final CA Agent deployment.*

**Baseline Metadata & Glossaries**
1. "What was our total blended Net Revenue across all channels for Fiscal Year 2025?"
2. "Show me the On-Hand Inventory for the Pro Mountain Bike across all warehouses."
3. "What is our current Defect Rate for Kayaks?"
4. "Calculate the AOV for the D2C channel last quarter."

**Ambiguity & Clarification Triggers (Agent must pause and ask)**
5. "What was our profit last month?"
6. "Show me our pipeline."
7. "Who are our best distributors?"
8. "What are our total expenses?"

**Tableau & Legacy SQL Extractions**
9. "How many Tier 1 Distributors do we currently have in EMEA?"
10. "List the top 10 Certified Field Testers by Total Lifetime Value (CLV)."
11. "What was our Blended D2C Customer Acquisition Cost (CAC) in Q1 of 2025?"
12. "Show me the Inventory Turn Ratio for Fiscal Year 2025."

**SSRS Extractions & The "Maze"**
13. "Show me the total Amount Due for Aging Invoices broken down by Region."
14. "What was our True Gross Margin for Tents in Q3 of 2025?"
15. "Compare the DSO of Tier 1 Distributors versus regular Wholesale Distributors."
16. "Which Product Category had the highest Net-New ARR last year?"

**Qualitative Context**
17. "Why did Wholesale revenue for Mountain Bikes spike so drastically in April 2025?"
18. "Explain the dip in our Gross Margin during Q3 of 2025 despite steady Net Revenue."

**Security & Governance**
19. "List the full names, email addresses, and phone numbers of our top 50 D2C customers."
20. "Show me a detailed breakdown of Wholesale Net Revenue by Distributor for the APAC region."