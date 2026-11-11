
# Premium Outdoor Gear - Dataplex Glossary Mapping
**Purpose:** Use this mapping guide to associate enterprise glossary terms to their physical data assets in BigQuery. If a term applies broadly, link it at the Table level. If it maps directly to a specific field, link it at the Column level.

## 1. Customers, Channels, & Geography

### Table: `l400_agentic_da.CUST_MSTR_D2C`
*   **Table-Level Terms:**
    *   **D2C (Direct-to-Consumer):** Sales originating from our owned retail website directly to the end-user.
    *   **Certified Field Tester:** An apex D2C customer who actively purchases across multiple product categories, retains gear, and provides verified feedback.
*   **Column-Level Terms:**
    *   `CUST_NUM_ID` ➔ **CLV / LTV (Customer Lifetime Value):** The total historical Net Revenue attributed to a single D2C customer.
    *   `ACQ_DT` ➔ **CAC (Customer Acquisition Cost):** Marketing OPEX divided by net-new customers acquired. *(Also links to FIN_OPEX_DTL)*.

### Table: `l400_agentic_da.DIST_ACCT_MSTR`
*   **Table-Level Terms:**
    *   **Wholesale:** B2B sales made to external sporting goods retailers, local bike shops, and bulk distributors.
    *   **Distributor:** A registered B2B wholesale partner who purchases gear in bulk.
    *   **Tier 1 Distributor:** A wholesale partner with over $250k in volume, buying 3+ categories, paying in < 30 days.

## 2. Sales, Orders, & Invoicing

### Table: `l400_agentic_da.SLS_ORD_HDR`
*   **Table-Level Terms:**
    *   **Drop-Ship:** When a wholesale partner sells our gear, but we ship it directly to their customer from our warehouse.
*   **Column-Level Terms:**
    *   `CHN_FLG` ➔ **D2C (Channel 1)** and **Wholesale (Channel 2)**.
    *   `STS_CDE` ➔ **Pipeline:** The projected revenue value of open, unclosed deals (where status is 'O' for Open).

### Table: `l400_agentic_da.SLS_ORD_DTL_LN`
*   **Table-Level Terms:**
    *   **Gross Revenue:** The total top-line sales amount before discounts or returns.
    *   **Net Revenue:** Gross Revenue minus applied discounts and refunds.
    *   **AOV (Average Order Value):** Total Net Revenue divided by distinct order headers.
*   **Column-Level Terms:**
    *   `UNIT_PRC_AMT` ➔ **MSRP (Manufacturer’s Suggested Retail Price):** The standard list price for our gear in the D2C channel.
    *   `UNIT_PRC_AMT` ➔ **MAP (Minimum Advertised Price):** The lowest price a distributor can advertise.

### Table: `l400_agentic_da.B2B_INV_AGING`
*   **Table-Level Terms:**
    *   **Aging Invoices:** B2B invoices that have been issued but remain unpaid.
*   **Column-Level Terms:**
    *   `ISSUE_DT` & `PAID_DT` ➔ **DSO (Days Sales Outstanding):** The average number of days it takes for a Wholesale Distributor to pay their B2B invoices.

### Table: `l400_agentic_da.SLS_RTN_LOGS_V2`
*   **Column-Level Terms:**
    *   `RSN_CDE_N` ➔ **Defect Rate:** The percentage of units returned due to manufacturing defects (Reason Code = 1).

## 3. Products, COGS, & Supply Chain

### Table: `l400_agentic_da.PRD_MSTR_CAT`
*   **Column-Level Terms:**
    *   `PRD_SKU_CD` ➔ **SKU (Stock Keeping Unit):** The unique alphanumeric identifier for a specific gear item.

### Table: `l400_agentic_da.PRD_CAT_DEF`
*   **Column-Level Terms:**
    *   `CAT_DESC_TXT` ➔ **Product Category:** The highest level of product grouping (e.g., Bikes, Outerwear, Kayaks).

### Table: `l400_agentic_da.PRD_COGS_FCT`
*   **Table-Level Terms:**
    *   **COGS (Cost of Goods Sold):** Direct production costs including Material, Labor, and Tariffs.
    *   **Gross Margin:** Net Revenue minus total COGS.
*   **Column-Level Terms:**
    *   `MTL_CST_AMT` ➔ **Raw Materials:** Core supplies purchased for manufacturing (e.g., Aluminum, Carbon Fiber).

### Table: `l400_agentic_da.INV_WHSE_FCT`
*   **Column-Level Terms:**
    *   `QTY_ON_HND_N` ➔ **On-Hand Inventory:** The physical count of a SKU currently sitting in our warehouses.
    *   `QTY_ON_HND_N` ➔ **Backorder:** An order placed for a SKU that currently has zero On-Hand Inventory.

## 4. Finance, OPEX, & Dates

### Table: `l400_agentic_da.GL_F_TRX_00`
*   **Table-Level Terms:**
    *   **EBIDA:** Earnings Before Interest, Depreciation, and Amortization.
    *   **Net Profit:** Gross Margin minus OPEX, taxes, and interest.
    *   **ARR (Annual Recurring Revenue):** The annualized value of recurring maintenance contracts.
    *   **Net-New ARR & Churn Rate:** Metrics associated with the expansion or loss of recurring revenue contracts.

### Table: `l400_agentic_da.FIN_OPEX_DTL`
*   **Table-Level Terms:**
    *   **OPEX (Operating Expenses):** Indirect costs not tied to manufacturing (Marketing, Sales, IT, HR).
*   **Column-Level Terms:**
    *   `DEPT_CD` ➔ **CAC (Customer Acquisition Cost):** Linked specifically when the Department Code is 'MKTG'.

### Table: `l400_agentic_da.SLS_REP_QUOTA`
*   **Column-Level Terms:**
    *   `QTA_AMT` ➔ **Quota Amount:** The quarterly sales target assigned to a regional sales representative.

### Table: `l400_agentic_da.SYS_CAL_DIM`
*   **Column-Level Terms:**
    *   `FISC_YR_N` ➔ **Fiscal Year:** Our financial reporting year (Runs Jan 1 - Dec 31).

### Table: `l400_agentic_da.VNDR_SPLY_MSTR`
*   **Table-Level Terms:**
    *   **Lead Time:** The number of days between placing a purchase order with a raw material vendor and the material arriving at our manufacturing plant.
