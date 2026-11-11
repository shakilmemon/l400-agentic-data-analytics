# Premium Outdoor Gear - Legacy ERP Data Dictionary

**Database:** l400_agentic_da  
**Last Updated:** Q1 2026

## 1. Finance & Accounting Tables

### GL_ACCT_MSTR

**Table Description:** The master chart of accounts defining all financial categories for General Ledger reporting.

| Column Name | Description |
| --- | --- |
| ACCT_ID_X | The unique alphanumeric identifier for the General Ledger account (e.g., GL1000). |
| ACCT_NM_STR | The human-readable name of the General Ledger account (e.g., Gross Revenue, COGS, Payroll). |
| BAL_SHT_FLG | Flag indicating if the account belongs on the Balance Sheet (1) or the Income Statement (0). |
| ACT_INACT_IND | Indicator showing if the account is currently Active ('A') or Inactive ('I'). |

---

### GL_F_TRX_00

**Table Description:** The core financial fact table containing every debit and credit transaction hitting the General Ledger.

| Column Name | Description |
| --- | --- |
| TRX_ID_N | The unique transaction identification number. |
| ACCT_ID_X | The General Ledger account ID mapped to this transaction. |
| POST_DT_SK | The surrogate integer date key (YYYYMMDD) indicating when the transaction was posted. |
| DR_CR_IND | Indicator identifying if the transaction is a Debit ('D') or a Credit ('C'). |
| AMT_BASE | The base monetary amount of the transaction in USD. |
| SRC_SYS_CDE | The internal source system that generated the transaction (e.g., 'SLS' for Sales, 'INV' for Inventory). |

---

### FIN_OPEX_DTL

**Table Description:** Granular line-item details of company Operating Expenses (OPEX), heavily used for calculating marketing and acquisition costs.

| Column Name | Description |
| --- | --- |
| EXP_ID | The unique identifier for the operating expense record. |
| DEPT_CD | The department code responsible for the expense (e.g., 'MKTG', 'SALES', 'IT'). |
| SPND_TYP_IND | Integer code representing the spend category (e.g., 10 for Digital Ads, 30 for Events). |
| AMT | The total monetary amount of the expense in USD. |
| POST_DT | The calendar date the operating expense was incurred and posted. |

---

## 2. Date Dimensions

### SYS_CAL_DIM

**Table Description:** The centralized corporate date dimension mapping calendar dates to corporate fiscal periods.

| Column Name | Description |
| --- | --- |
| DT_SK | The integer surrogate key for the date, formatted as YYYYMMDD. |
| CAL_DT | The standard calendar date (DATE format). |
| FISC_YR_N | The corporate Fiscal Year. The fiscal year runs from Jan 1 - Dec 31. |
| FISC_QTR_N | The corporate Fiscal Quarter (1 through 4). |
| FISC_PER_N | The specific month number of the fiscal year. |

---

## 3. Sales & Orders

### SLS_ORD_HDR

**Table Description:** The header-level fact table for all sales transactions containing order status, dates, and channel routing.

| Column Name | Description |
| --- | --- |
| ORD_NO_SYS | The unique system-generated Order Number. |
| CUST_NUM_ID | The Direct-to-Consumer (D2C) Customer ID. This is NULL if the order was a Wholesale B2B order. |
| DIST_ACCT_ID | The Wholesale Distributor Account ID. This is NULL if the order was a D2C retail order. |
| ORD_DT_SID | The surrogate integer date key indicating when the order was placed. |
| CHN_FLG | Integer flag indicating the sales channel. 1 = D2C (Direct-to-Consumer), 2 = Wholesale (B2B). |
| STS_CDE | The order fulfillment status. 'O' = Open, 'C' = Closed/Fulfilled, 'V' = Voided. |

---

### SLS_ORD_DTL_LN

**Table Description:** The line-item details for every sales order, detailing specific products, quantities, and applied discounts.

| Column Name | Description |
| --- | --- |
| ORD_NO_SYS | The parent Order Number linking back to the order header. |
| LN_NO_N | The specific line number within the order. |
| PRD_SKU_CD | The unique Product SKU code purchased on this line. |
| QTY_N | The quantity of the product purchased. |
| UNIT_PRC_AMT | The MSRP or base unit price of the product in USD. |
| DISC_PCT_N | The discount percentage applied to this line item (e.g., 0.15 = 15% discount). |

---

### SLS_RTN_LOGS_V2

**Table Description:** The fact table capturing all product returns, refunds, and associated defect reasons.

| Column Name | Description |
| --- | --- |
| RTN_AUTH_ID | The unique Return Authorization ID. |
| ORD_NO_SYS | The original Order Number the returned product belongs to. |
| PRD_SKU_CD | The specific Product SKU being returned. |
| RTN_DT | The date the return was processed and received. |
| RSN_CDE_N | Integer code for the return reason. 1 = Defective, 2 = Wrong Size, 3 = Changed Mind. |
| RFN_AMT | The total monetary amount refunded to the customer in USD. |

---

### B2B_INV_AGING

**Table Description:** Tracks the status and aging of B2B invoices issued to Wholesale Distributors.

| Column Name | Description |
| --- | --- |
| INV_NUM_X | The unique Invoice Number. Note: Invoices are created by prepending 'INV-' to the original ORD_NO_SYS. |
| DIST_ACCT_ID | The Wholesale Distributor Account ID responsible for payment. |
| ISSUE_DT | The date the invoice was generated and sent. |
| PAID_DT | The date the invoice was paid in full. Null if still unpaid. |
| AMT_DUE | The total monetary amount due for the invoice in USD. |
| STS_FLG | Integer flag indicating payment status. 0 = Open/Unpaid, 1 = Paid, 9 = Default/Collections. |

---

## 4. Customers, Geos, & Channels

### CUST_MSTR_D2C

**Table Description:** The master dimension table containing PII and profile data for Direct-to-Consumer (retail) customers.

| Column Name | Description |
| --- | --- |
| CUST_NUM_ID | The unique identifier for the D2C retail customer. |
| F_NM | The customer's First Name. |
| L_NM | The customer's Last Name. |
| EML_ADDR_TXT | The customer's Email Address (Classified as High-Risk PII). |
| PHONE_NUM_V | The customer's Phone Number (Classified as High-Risk PII). |
| ACQ_DT | The date the customer made their first purchase or created their account. |
| OPT_IN_FLG | Flag indicating if the customer opted into marketing emails. 1 = Yes, 0 = No. |

---

### DIST_ACCT_MSTR

**Table Description:** The master dimension table containing profile data for our B2B Wholesale Distributor partners.

| Column Name | Description |
| --- | --- |
| DIST_ACCT_ID | The unique identifier for the Wholesale Distributor. |
| CO_NM_TXT | The legal company name of the Distributor. |
| REG_ID_CD | The geographic Region ID where the distributor is headquartered. |
| ONBRD_DT | The date the distributor signed their B2B partnership agreement. |

---

### GEO_REG_HIER

**Table Description:** The geographic hierarchy mapping specific territory codes to global regions.

| Column Name | Description |
| --- | --- |
| REG_ID_CD | The unique internal Region ID code (e.g., 'R_01'). |
| CTRY_CD | The two-letter Country Code. |
| RGN_NM_TXT | The macro global region name (e.g., NorthAm, EMEA, APAC). |
| SUB_RGN_TXT | The specific sub-region or territory name (e.g., West Coast, Nordics). |

---

### CUST_FEEDBACK_FCT

**Table Description:** The repository for customer reviews and product feedback ratings.

| Column Name | Description |
| --- | --- |
| FDBK_ID_X | The unique identifier for the feedback submission. |
| CUST_NO_X | The D2C Customer ID who submitted the feedback (Maps to CUST_NUM_ID). |
| PRD_SKU_CD | The Product SKU being reviewed. |
| SUB_DT | The date the feedback was submitted. |
| RTG_N | The star rating provided by the customer, on a scale of 1 to 5. |
| VLD_FLG | Flag indicating if the review is from a verified purchaser. 'Y' = Yes, 'N' = No. |

---

## 5. Products & Supply Chain

### PRD_MSTR_CAT

**Table Description:** The product master dimension detailing active SKU attributes and pricing.

| Column Name | Description |
| --- | --- |
| PRD_SKU_CD | The unique Stock Keeping Unit (SKU) identifier for the product. |
| PRD_NM_TXT | The formal, human-readable name of the product. |
| CAT_CDE_N | The integer code mapping the product to its macro category. |
| SUB_CAT_CDE_N | The integer code mapping the product to its specific sub-category. |
| LCH_DT | The date the product was officially launched into the market. |

---

### PRD_CAT_DEF

**Table Description:** Lookup table translating numeric product category codes into human-readable descriptions.

| Column Name | Description |
| --- | --- |
| CAT_CDE_N | The integer category code. |
| CAT_DESC_TXT | The description of the product category (e.g., Bikes, Outerwear, Kayaks, Tents). |

---

### PRD_COGS_FCT

**Table Description:** A Slowly Changing Dimension (SCD) tracking the Cost of Goods Sold (COGS) for products over specific time periods.

| Column Name | Description |
| --- | --- |
| PRD_SKU_CD | The Product SKU. |
| EFF_DT | The Effective Date when these costs began applying to the product. |
| END_DT | The End Date when these costs stopped applying to the product. |
| MTL_CST_AMT | The raw material manufacturing cost in USD. |
| LBR_CST_AMT | The manual labor and assembly cost in USD. |
| TRFF_AMT | Associated international import/export tariffs in USD. |

---

### INV_WHSE_FCT

**Table Description:** A weekly snapshot table logging the physical inventory levels across all global warehouses.

| Column Name | Description |
| --- | --- |
| WHSE_LOC_CD | The unique identifier for the warehouse facility. |
| PRD_SKU_CD | The Product SKU currently in stock. |
| SNAP_DT | The date the inventory snapshot was taken (typically every 7 days). |
| QTY_ON_HND_N | The physical quantity of the product currently on-hand in the warehouse. |

---

### VNDR_SPLY_MSTR

**Table Description:** The master dimension of external vendors who supply raw materials for manufacturing.

| Column Name | Description |
| --- | --- |
| VNDR_ID_C | The unique Vendor ID. |
| VNDR_NM | The legal name of the supply vendor. |
| MTL_TYP_CD | The code representing the primary material supplied (e.g., 'ALUM' for Aluminum, 'CRBN' for Carbon Fiber). |

---

## 6. HR & Operations

### HR_EMP_MSTR

**Table Description:** The master employee directory tracking internal personnel and department alignment.

| Column Name | Description |
| --- | --- |
| EMP_ID_N | The unique internal Employee ID number. |
| EMP_NM | The full name of the employee. |
| DEPT_CD | The department the employee reports to (e.g., 'SALES', 'MKTG'). |
| HIRE_DT | The date the employee was officially hired. |

---

### SLS_REP_QUOTA

**Table Description:** The financial target quotas assigned to regional sales representatives on a quarterly basis.

| Column Name | Description |
| --- | --- |
| EMP_ID_N | The Employee ID of the sales representative. |
| REG_ID_CD | The Region ID the representative is responsible for selling into. |
| QTR_TXT | A string representing the target quarter (e.g., '2024-Q1'). |
| QTA_AMT | The total sales target (quota) amount in USD the representative is expected to close. |