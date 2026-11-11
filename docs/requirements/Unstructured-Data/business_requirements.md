# Business Requirements: Conversational Analytics with Qualitative Business Context

**Document Status:** Draft Spec (FP&A & IT Alignment)
**Date:** July 17, 2026
**Author:** FP&A Analytics Lead & Data Architecture Team

---

### 1. Executive Summary & Objective

The Conversational Analytics (CA) platform currently does an excellent job calculating financial run-rates and hard metrics from our BigQuery sales and inventory tables. However, it lacks "situational awareness." When executives ask qualitative questions such as:
* *"Why did wholesale revenue spike in April?"*
* *"Why did gross margins drop in Q3?"*

The agent cannot answer. It sees the mathematical drop in numbers, but doesn't know *why* (e.g., that we had a competitor safety recall that drove D2C sales, or a severe aluminum shortage that spike COGS). 

To bridge this gap, we are establishing a new qualitative dimension table called `dim_business_events`. This table will be loaded via AI extraction from our unstructured PDF resources (e.g., competitive intelligence memos, global supply chain bulletins). 

Our goal is to build an automated pipeline that registers this schema in the data dictionary and trains the CA agent using a **Type 2 Analytical Golden Query**. This teaches the agent how to overlay qualitative event timelines directly onto physical sales records.

---

### 2. Table Definition & Schema Specifications: `dim_business_events`

This dimension table holds qualitative context. To ensure the Business Intelligence layer and the LLM extraction models are aligned, the table must contain the following business-facing fields (note: do not worry about the technical GCS extraction metadata or raw model response logs here, as those are handled by the backend ingestion system):

* **Memo_Date**: The exact timestamp when the original alert/executive memo was officially distributed.
* **Sender**: The issuing office or business executive (e.g., *'Global Competitive Intelligence Desk'*, *'Supply Chain Logistics Org'*).
* **Event_Type**: High-level classification of the event (e.g., *'Market Anomaly'*, *'Supply Chain Disruption'*, *'Regulatory Alert'*).
* **Event_Start_Date**: The calendar date (YYYY-MM-DD format) when the financial or operational impact was first felt.
* **Event_End_Date**: The calendar date when the impact normalized or is projected to normalize.
* **Affected_Division**: The business division impacted by this event. Must be mapped to standard divisions like *'Wholesale'*, *'D2C'*, or *'All'*. 
  > **Business Note:** In our physical database, divisions are represented numerically inside `SLS_ORD_HDR.CHN_FLG` where `1` represents *'D2C'* and `2` represents *'Wholesale'*. The Golden Query must explicitly teach the CA agent this mapping since the unstructured memos only refer to "Wholesale" or "D2C" text!
* **Impacted_Products**: Comma-separated list of product categories or individual SKUs affected (e.g., *'Mountain Bikes'*, *'Tents'*, *'All'*).
* **Event_Description**: A detailed text description summarizing the event (e.g., competitor safety weld failures, shipping canal detours).
* **Root_Cause**: The root cause trigger of the anomaly (e.g., *'Safety weld failure'*, *'Geopolitical export restriction'*).
* **Financial_Impact_Category**: Description of the specific metric delta (e.g., *'Gross Margin Dip'*, *'Revenue Spike'*, *'Inventory Backlog'*).
* **FPA_Guidance**: Actionable instructions for the FP&A forecasting team on how to treat this anomaly during future planning and model-building (e.g., *'Exclude Q3 from standard run-rate calculation'*).
* **Expected_Duration**: Projected duration text (e.g., *'90 Days'*, *'1 Quarter'*).

---

### 3. Join Logic & Golden Query Requirements

To teach the CA agent how to merge qualitative and quantitative data, we must register a **Golden Query** in its training corpus. 

The query should join our sales order header (`SLS_ORD_HDR`), sales order detail lines (`SLS_ORD_DTL_LN`), calendar dimension (`SYS_CAL_DIM`), and the new `dim_business_events` table.

#### Golden Query Constraints:
1. **Natural Join Pattern:** Since business events are transient and cover date ranges, the events table must be `LEFT JOIN`ed on the calendar dimension using a date range constraint:
   `cal.CAL_DT BETWEEN biz.Event_Start_Date AND biz.Event_End_Date`
2. **Sales Status:** Standard order headers must be filtered for completed sales (`hdr.STS_CDE = 'C'`).
3. **Year Filter:** Filter the transaction data for fiscal year `2025`.
4. **Required Outputs:**
   - Fiscal Year and Fiscal Period.
   - Calculated **Net Revenue** (Formula: `SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N))`).
   - The qualitative explanation of the event (`MAX(biz.Event_Description)`).
   - The underlying root cause of the event (`MAX(biz.Root_Cause)`).
5. **Group and Order:** Group and order by Fiscal Year and Fiscal Period.

#### Trigger Prompt:
The golden query should match prompts like:
* *"Show me the Net Revenue trend for 2025 and include any qualitative business events or context."*

And help the agent dynamically answer ad-hoc questions like:
* *"Why did gross margins drop in Q3?"*