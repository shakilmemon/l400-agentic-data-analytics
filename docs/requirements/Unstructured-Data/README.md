Here are the unstructured data documents. 

In the lab, these files will be placed into a Google Cloud Storage (GCS) bucket. The CE will create a BigQuery Object Table over this bucket and use a BigQuery ML prompt (`ML.GENERATE_TEXT` via Gemini) to read these raw corporate memos and extract them into the structured `l400_agentic_da.dim_business_events` table (Columns: `Event_Month`, `Affected_Division`, `Event_Description`). 

This proves to the customer that we can seamlessly turn unstructured "dark data" into SQL-queryable context!

***

### Document 1: Market Intelligence Alert
*(Save this as `Market_Intelligence_Alert_April_2025.md`)*

```markdown
# URGENT: Market Intelligence & Competitive Alert
**Date:** April 4, 2025
**From:** Global Competitive Intelligence Desk
**To:** All Regional Sales Directors, Wholesale Account Managers
**Subject:** Competitor Safety Recall - Immediate Wholesale Opportunities

**Executive Summary:**
Early this morning, our largest international competitor, *Apex Trail Dynamics*, issued a mandatory, global safety recall on all of their 2024 and 2025 carbon mountain bike frames due to critical weld failures. They have ordered all retailers to immediately pull the stock from their showroom floors.

**Market Impact & Sales Strategy:**
This recall has created an immediate vacuum in the wholesale market. Distributors and local bike shops are panic-buying to fill their empty showroom floors ahead of the summer riding season. 

**Expected Anomaly:**
As a result of our sales team capitalizing on this competitor failure, we anticipate a massive, one-time spike in Wholesale (B2B) revenue specifically for our Mountain Bike product lines throughout the month of **April 2025**. 

*Please Note for FP&A:* This 500% surge in mountain bike sales volume is a strictly opportunistic anomaly and should NOT be factored into baseline run-rate projections or quota planning for the upcoming fiscal year.
```

***

### Document 2: Global Supply Chain Advisory
*(Save this as `Global_Supply_Chain_Advisory_Q3_2025.md`)*

```markdown
# Global Supply Chain Advisory
**Date:** June 15, 2025
**From:** VP of Global Supply Chain & Manufacturing
**To:** Executive Leadership, FP&A, Inventory Management
**Subject:** Severe Aluminum Shortage & Q3 Gross Margin Warning

**Situation Overview:**
Due to sudden geopolitical export restrictions in major bauxite-producing regions combined with a localized port strike, we are experiencing an unprecedented bottleneck in the global supply of raw aluminum. 

**Financial Impact (Effective July 1 - Sept 30, 2025):**
Our raw material suppliers have informed us that the cost of raw aluminum will increase by approximately 2.5x effective July 1st. Because we have existing MAP (Minimum Advertised Price) commitments and distributor contracts, we cannot pass these price increases on to the customer in the short term.

**Forecasting Adjustments:**
*   **Revenue:** Top-line Gross and Net Revenue will remain unaffected as consumer demand remains highly stable.
*   **Cost of Goods Sold (COGS):** Total COGS will skyrocket across all manufacturing divisions.
*   **Gross Margin:** You will see a significant, unavoidable dip in our True Gross Margins for the entirety of **Q3 2025** (July, August, and September).
*   **Affected Products:** This margin compression will severely impact our Aluminum-heavy product lines, specifically **Bicycles** (Category 100) and **Tents / Tent Poles** (Category 400). 

Supply chain stabilization protocols have been initiated, and we expect raw material costs to normalize to their standard baseline by October 1st, 2025. 
```

***

### How this connects to the Lab and Evalset:
When the CE uses Gemini to process these documents, the LLM will output something like:
*   `2025-04-01 | Wholesale | Revenue spiked due to a major competitor's safety recall, causing distributors to urgently restock mountain bikes.`
*   `2025-07-01 | All | Gross Margin dipped significantly due to a global supply chain disruption that skyrocketed the cost of raw aluminum.`

Because the CE added the **Agent Instruction** *(from our previous step)* telling CA to LEFT JOIN the `dim_business_events` table whenever a user asks "Why" or "Explain", the agent will natively read these extracted strings and present them as the answer to **Prompts 17 and 18**!

What is the next item on your hit list? Shall we draft the **Step-by-Step Lab Guide** outline, or dive into formatting the **Evalset JSON**?