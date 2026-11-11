**Golden Query (Type 2 Analytical Example)**

If a user asks *"Why did wholesale revenue spike in April?"*, the CA Agent will have no idea how to join a text string like `'Wholesale'` in `Affected_Division` to the integer `CHN_FLG = 2` in the Sales Header table, nor will it know how to correctly map `Event_Month` to `SYS_CAL_DIM`. The Golden Query teaches the agent exactly how to overlay this qualitative data onto the financial math.

Here is exactly what you need to add to your Data Dictionary and the Golden Query to make this work flawlessly.

***

## Unstructured Business Context

### `dim_business_events`
**Table Description:** A qualitative dimension table generated via AI extraction from unstructured executive memos and market alerts. It provides crucial business context, root causes, and explanations for anomalies in financial and operational data.

| Column Name | Description |
| :--- | :--- |
| `Memo_Date` | The exact timestamp when the original alert/executive memo was officially distributed. |
| `Sender` | The issuing office or business executive (e.g., *'Global Competitive Intelligence Desk'*, *'Supply Chain Logistics Org'*). |
| `Event_Type` | High-level classification of the event (e.g., *'Market Anomaly'*, *'Supply Chain Disruption'*, *'Regulatory Alert'*). |
| `Event_Start_Date` | The calendar date (YYYY-MM-DD format) when the financial or operational impact was first felt. |
| `Event_End_Date` | The calendar date when the impact normalized or is projected to normalize. |
| `Affected_Division` | The business division impacted by this event. Must be mapped to standard divisions like *'Wholesale'*, *'D2C'*, or *'All'*. |
| `Impacted_Products` | Comma-separated list of product categories or individual SKUs affected (e.g., *'Mountain Bikes'*, *'Tents'*, *'All'*). |
| `Event_Description` | A detailed text description summarizing the event (e.g., competitor safety weld failures, shipping canal detours). |
| `Root_Cause` | The root cause trigger of the anomaly (e.g., *'Safety weld failure'*, *'Geopolitical export restriction'*). |
| `Financial_Impact_Category` | Description of the specific metric delta (e.g., *'Gross Margin Dip'*, *'Revenue Spike'*, *'Inventory Backlog'*). |
| `FPA_Guidance` | Actionable instructions for the FP&A forecasting team on how to treat this anomaly during future planning and model-building (e.g., *'Exclude Q3 from standard run-rate calculation'*). |
| `Expected_Duration` | Projected duration text (e.g., *'90 Days'*, *'1 Quarter'*). |
```

***

### The Golden Query (Type 2 Analytical Example)
*Register this in the CA Agent configuration. It explicitly teaches the agent how to do the complex date extraction and how to map the text string `'Wholesale'` to the integer `CHN_FLG = 2`.*

**Prompt to Match:** Show me the Net Revenue trend for 2025 and include any qualitative business events or context.

**The SQL:**
```sql
SELECT 
    cal.FISC_YR_N AS FiscalYear,
    cal.FISC_PER_N AS FiscalPeriod,
    SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) AS Net_Revenue,
    MAX(biz.Event_Description) AS Qualitative_Explanation,
    MAX(biz.Root_Cause) AS Root_Cause
FROM `l400_agentic_da.SLS_ORD_HDR` hdr
JOIN `l400_agentic_da.SYS_CAL_DIM` cal 
    ON hdr.ORD_DT_SID = cal.DT_SK
JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln 
    ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
-- THE NATURAL JOIN PATTERN:
LEFT JOIN `l400_agentic_da.dim_business_events` biz 
    ON cal.CAL_DT BETWEEN biz.Event_Start_Date AND biz.Event_End_Date
WHERE hdr.STS_CDE = 'C' AND cal.FISC_YR_N = 2025
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Prompt to trigger
Why did gross margins drop in Q3?
