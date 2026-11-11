# Corporate Operations, Supply Chain, & Finance Glossary

---

**Domain:** Premium Outdoor Gear - Enterprise Operations &nbsp;&nbsp;&nbsp;&nbsp; **Last Updated:** Q1 2026

---

## 1. Channel Definitions

* **D2C (Direct-to-Consumer):** Sales originating from our owned retail website directly to the end-user. Flagged in systems as Channel 1.
* **Wholesale:** B2B sales made to external sporting goods retailers, local bike shops, and bulk distributors. Flagged in systems as Channel 2.
* **Distributor:** A registered B2B wholesale partner who purchases gear in bulk.

## 2. Customer & Product Terminology

* **Certified Field Tester:** An apex D2C customer who actively purchases across multiple product categories, retains their gear (low returns), and provides verified product feedback.
* **Tier 1 Distributor:** A wholesale partner with over $250,000 in annual volume, purchasing across 3+ categories, and maintaining an average invoice payment time of under 30 days.
* **SKU (Stock Keeping Unit):** The unique alphanumeric identifier for a specific gear item (e.g., SKU-101 for Pro Mountain Bike).
* **Product Category:** The highest level of product grouping (100=Bikes, 200=Outerwear, 300=Kayaks, 400=Tents).
* **MAP (Minimum Advertised Price):** The lowest price a wholesale distributor is legally allowed to publicly advertise our gear.
* **MSRP (Manufacturer’s Suggested Retail Price):** The standard list price for our gear in the D2C channel before discounts.

## 3. Supply Chain Terminology

* **On-Hand Inventory (QTY_ON_HND):** The physical count of a SKU currently sitting in our managed warehouses.
* **Lead Time:** The number of days between placing a purchase order with a raw material vendor and the material arriving at our manufacturing plant.
* **Backorder:** An order placed by a customer or distributor for a SKU that currently has zero On-Hand Inventory.
* **Defect Rate:** Calculated by dividing the total number of distinct Return Authorizations where the Reason Code is 1, by the total Quantity Sold.
* **Raw Materials:** The core supplies purchased from vendors to manufacture our products, primarily Aluminum, Carbon Fiber, Nylon, and Steel.
* **Drop-Ship:** When a wholesale partner sells our gear, but we ship it directly to their customer from our warehouse.

## 4. Financial & Revenue Metrics

* **Gross Revenue:** The total top-line sales amount before discounts or returns.
* **Net Revenue:** Gross Revenue minus applied discounts and refunds.
* **AOV (Average Order Value):** Calculated by dividing Total Net Revenue by the count of distinct order headers (ORD_NO_SYS).
* **EBIDA:** Earnings Before Interest, Depreciation, and Amortization.
* **Net Profit:** Gross Margin minus OPEX, taxes, and interest.
* **ARR (Annual Recurring Revenue):** The annualized value of recurring maintenance contracts.
* **Net-New ARR:** The total ARR gained from new contracts minus the ARR lost to churned or canceled contracts.
* **Churn Rate:** Metrics associated with the expansion or loss of recurring revenue contracts.
* **OPEX (Operating Expenses):** Indirect costs not tied to manufacturing (Marketing, Sales, IT, HR).
* **COGS (Cost of Goods Sold):** Direct production costs including Material, Labor, and Tariffs.
* **Gross Margin:** Net Revenue minus total COGS.
* **DSO (Days Sales Outstanding):** Calculated as the average number of days between the Invoice Issue Date and the Paid Date.
* **Aging Invoices:** B2B invoices that have been issued but remain unpaid.

## 5. Column Definitions & System Flags

* **CUST_NUM_ID (Customer Number ID):** The unique identifier for a D2C retail customer. This field is the primary key used to calculate CLV / LTV (Customer Lifetime Value), which is the total historical Net Revenue attributed to a single customer.
* **ACQ_DT (Acquisition Date):** The date a customer made their first purchase or created their account. Used to calculate CAC (Customer Acquisition Cost) (Marketing OPEX divided by net-new customers acquired).
* **CHN_FLG (Channel Flag):** Integer flag indicating the sales channel route (1 = D2C, 2 = Wholesale).
* **STS_CDE (Status Code):** The order fulfillment status flag ('O' = Open, 'C' = Closed/Fulfilled, 'V' = Voided). Open statuses are typically used to calculate active Pipeline.
* **UNIT_PRC_AMT (Unit Price Amount):** The base unit price of a product in USD, often reflecting the MSRP or MAP.
* **ISSUE_DT / PAID_DT:** The respective dates a B2B invoice was generated (Issue) and subsequently settled (Paid).
* **RSN_CDE_N (Reason Code):** Integer code representing the reason for a product return (1 = Defective, 2 = Wrong Size, 3 = Changed Mind).
* **PRD_SKU_CD (Product SKU Code):** The specific Stock Keeping Unit system code mapped to a physical product.
* **CAT_DESC_TXT (Category Description):** The text description of the product category.
* **MTL_CST_AMT (Material Cost Amount):** The raw material manufacturing cost component of Cost of Goods Sold (COGS).
* **DEPT_CD (Department Code):** The string code representing an internal business unit (e.g., 'MKTG', 'SALES').
* **QTA_AMT (Quota Amount):** The target sales revenue amount (Quota) assigned to a representative.
* **FISC_YR_N (Fiscal Year Number):** The corporate financial reporting year integer.