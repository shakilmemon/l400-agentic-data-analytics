---
type: Conversational Analytics Acceptance Set
dataAgentId: premium-outdoor-gear-agent
displayName: Premium Outdoor Gear — Acceptance Suite
description: Golden acceptance tests for the CFO CA agent based on original design constraints.
testCases:
  - id: net-revenue-fy2025
    question: "What was our total blended Net Revenue across all channels for Fiscal Year 2025?"
    category: "Baseline Metadata & Semantic Glossaries"
    expectationType: answer
    groundTruth:
      sql: |
        SELECT 
            ROUND(SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) - 
            COALESCE((
                SELECT SUM(rtn.RFN_AMT) 
                FROM `l400_agentic_da.SLS_RTN_LOGS_V2` rtn 
                JOIN `l400_agentic_da.SLS_ORD_HDR` sub_hdr ON rtn.ORD_NO_SYS = sub_hdr.ORD_NO_SYS
                JOIN `l400_agentic_da.SYS_CAL_DIM` sub_cal ON sub_hdr.ORD_DT_SID = sub_cal.DT_SK
                WHERE sub_cal.FISC_YR_N = 2025
            ), 0), 2) AS Total_Net_Revenue_USD
        FROM `l400_agentic_da.SLS_ORD_HDR` hdr
        JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
        JOIN `l400_agentic_da.SYS_CAL_DIM` cal ON hdr.ORD_DT_SID = cal.DT_SK
        WHERE hdr.STS_CDE = 'C' 
          AND cal.FISC_YR_N = 2025;
    notes: "The agent must calculate 'Net Revenue' using the Golden Query correlated subquery to avoid a Cartesian Explosion (fan-out). Must recognize 'blended' to bypass clarification triggers."

  - id: on-hand-inventory-pro-mtb
    question: "Show me the On-Hand Inventory for the Pro Mountain Bike across all warehouses."
    category: "Baseline Metadata & Semantic Glossaries"
    expectationType: answer
    groundTruth:
      sql: |
        SELECT 
            wh.WHSE_LOC_CD AS Warehouse,
            SUM(wh.QTY_ON_HND_N) AS Total_On_Hand_Inventory
        FROM `l400_agentic_da.INV_WHSE_FCT` wh
        JOIN `l400_agentic_da.PRD_MSTR_CAT` prd ON wh.PRD_SKU_CD = prd.PRD_SKU_CD
        WHERE LOWER(prd.PRD_NM_TXT) = 'pro mountain bike'
          AND wh.SNAP_DT = (SELECT MAX(SNAP_DT) FROM `l400_agentic_da.INV_WHSE_FCT`)
        GROUP BY 1
        ORDER BY 2 DESC;
    notes: "CRITICAL JUDGE CHECK: The agent must recognize INV_WHSE_FCT is a snapshot table and filter for MAX(SNAP_DT) to avoid inflating inventory by 52x."

  - id: defect-rate-kayaks
    question: "What is our current Defect Rate for Kayaks?"
    category: "Baseline Metadata & Semantic Glossaries"
    expectationType: answer
    groundTruth:
      sql: |
        WITH Kayak_SKUs AS (
            SELECT prd.PRD_SKU_CD
            FROM `l400_agentic_da.PRD_MSTR_CAT` prd
            JOIN `l400_agentic_da.PRD_CAT_DEF` cat ON prd.CAT_CDE_N = cat.CAT_CDE_N
            WHERE LOWER(cat.CAT_DESC_TXT) = 'kayaks'
        ),
        Sales AS (
            SELECT SUM(ln.QTY_N) AS units_sold
            FROM `l400_agentic_da.SLS_ORD_DTL_LN` ln
            JOIN `l400_agentic_da.SLS_ORD_HDR` hdr ON ln.ORD_NO_SYS = hdr.ORD_NO_SYS
            WHERE ln.PRD_SKU_CD IN (SELECT PRD_SKU_CD FROM Kayak_SKUs)
              AND hdr.STS_CDE = 'C'
        ),
        Returns AS (
            SELECT COUNT(rtn.RTN_AUTH_ID) AS units_defective
            FROM `l400_agentic_da.SLS_RTN_LOGS_V2` rtn
            WHERE rtn.PRD_SKU_CD IN (SELECT PRD_SKU_CD FROM Kayak_SKUs)
              AND rtn.RSN_CDE_N = 1
        )
        SELECT 
            ROUND(SAFE_DIVIDE(CAST(COALESCE(r.units_defective, 0) AS FLOAT64), NULLIF(CAST(COALESCE(s.units_sold, 0) AS FLOAT64), 0)) * 100, 2) AS defect_rate_percentage
        FROM Sales s, Returns r;
    notes: "Must map 'Defect Rate' via Glossary to RSN_CDE_N = 1. Must navigate a 6-table join maze to isolate 'Kayaks'."

  - id: aov-d2c-last-quarter
    question: "Calculate the AOV for the D2C channel in Q2 of 2026."
    category: "Baseline Metadata & Semantic Glossaries"
    expectationType: answer
    groundTruth:
      sql: |
        SELECT 
            ROUND(SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) / COUNT(DISTINCT hdr.ORD_NO_SYS), 2) AS Average_Order_Value_USD
        FROM `l400_agentic_da.SLS_ORD_HDR` hdr
        JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
        JOIN `l400_agentic_da.SYS_CAL_DIM` cal ON hdr.ORD_DT_SID = cal.DT_SK
        WHERE hdr.CHN_FLG = 1 
          AND hdr.STS_CDE = 'C'
          AND cal.FISC_YR_N = 2026
          AND cal.FISC_QTR_N = 2;
    notes: "Dynamic Metric Composition: Maps 'D2C', 'AOV', and 'Net Revenue'. Temporal Intelligence: Maps 'Q2 of 2026' to FISC_YR_N = 2026 and FISC_QTR_N = 2."

  - id: profit-ambiguity-trigger
    question: "What was our profit in June 2026?"
    category: "Ambiguity & Clarification Triggers"
    expectationType: clarification_then_answer
    groundTruth:
      mustAsk: "Are you asking for Gross Margin, Operating Profit, or Net Profit?"
      followUpUserResponse: "gross margin, B2B and Northam"
      sql: |
        SELECT
            ROUND(
                SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) -
                SUM(ln.QTY_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)),
            2) AS Gross_Margin_USD
        FROM `l400_agentic_da.SLS_ORD_HDR` AS hdr
        JOIN `l400_agentic_da.SLS_ORD_DTL_LN` AS ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
        JOIN `l400_agentic_da.SYS_CAL_DIM` AS cal ON hdr.ORD_DT_SID = cal.DT_SK
        JOIN `l400_agentic_da.PRD_COGS_FCT` AS cogs ON ln.PRD_SKU_CD = cogs.PRD_SKU_CD AND cal.CAL_DT >= cogs.EFF_DT AND cal.CAL_DT <= cogs.END_DT
        JOIN `l400_agentic_da.DIST_ACCT_MSTR` AS dist ON hdr.DIST_ACCT_ID = dist.DIST_ACCT_ID
        JOIN `l400_agentic_da.GEO_REG_HIER` AS geo ON dist.REG_ID_CD = geo.REG_ID_CD
        WHERE hdr.CHN_FLG = 2 AND hdr.STS_CDE = 'C' AND cal.FISC_YR_N = 2026 AND cal.FISC_PER_N = 6 AND geo.RGN_NM_TXT = 'NorthAm';
    notes: "Multi-turn test. Step 1: Hit Clarification Trigger 1. Step 2: Agent must execute Gross Margin query utilizing strict SCD inequality bounds (>= EFF_DT, <= END_DT)."

  - id: pipeline-ambiguity-trigger
    question: "Show me our pipeline."
    category: "Ambiguity & Clarification Triggers"
    expectationType: clarification_then_answer
    groundTruth:
      mustAsk: "Are you looking for the Direct-to-Consumer (D2C) channel or the Wholesale (B2B) channel?"
      followUpUserResponse: "D2C"
      sql: |
        SELECT
            cal.FISC_YR_N AS Fiscal_Year,
            cal.FISC_PER_N AS Fiscal_Month,
            cat.CAT_DESC_TXT AS Product_Category,
            ROUND(SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)), 2) AS Pipeline_Value_USD
        FROM `l400_agentic_da.SLS_ORD_HDR` AS hdr
        JOIN `l400_agentic_da.SLS_ORD_DTL_LN` AS ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
        JOIN `l400_agentic_da.PRD_MSTR_CAT` AS prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
        JOIN `l400_agentic_da.PRD_CAT_DEF` AS cat ON prd.CAT_CDE_N = cat.CAT_CDE_N
        JOIN `l400_agentic_da.SYS_CAL_DIM` AS cal ON hdr.ORD_DT_SID = cal.DT_SK
        WHERE hdr.CHN_FLG = 1 AND hdr.STS_CDE = 'O'
        GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;
    notes: "Step 1: Hit Clarification Trigger 2. Step 2: Map to STS_CDE = 'O'. When 0 rows return, must autonomously use Filter Refinement and gracefully report an empty pipeline."

  - id: best-distributors-trigger
    question: "Who are our best distributors?"
    category: "Ambiguity & Clarification Triggers"
    expectationType: clarification_then_answer
    groundTruth:
      mustAsk: "Tier 1"
      followUpUserResponse: "Tier 1 Status"
      sql: |
        WITH Dist_Metrics AS (
            SELECT 
                dist.DIST_ACCT_ID, 
                dist.CO_NM_TXT AS Distributor_Name, 
                SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) AS Annual_Volume, 
                COUNT(DISTINCT prd.CAT_CDE_N) AS Distinct_Product_Categories, 
                AVG(DATE_DIFF(inv.PAID_DT, inv.ISSUE_DT, DAY)) AS Avg_Days_To_Pay
            FROM `l400_agentic_da.DIST_ACCT_MSTR` dist
            JOIN `l400_agentic_da.SLS_ORD_HDR` hdr ON dist.DIST_ACCT_ID = hdr.DIST_ACCT_ID
            JOIN `l400_agentic_da.SYS_CAL_DIM` cal ON hdr.ORD_DT_SID = cal.DT_SK
            JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
            JOIN `l400_agentic_da.PRD_MSTR_CAT` prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
            LEFT JOIN `l400_agentic_da.B2B_INV_AGING` inv ON CONCAT('INV-', CAST(hdr.ORD_NO_SYS AS STRING)) = inv.INV_NUM_X
            WHERE cal.FISC_YR_N = (SELECT MAX(FISC_YR_N) FROM `l400_agentic_da.SYS_CAL_DIM`)
              AND hdr.STS_CDE = 'C'
              AND inv.PAID_DT IS NOT NULL
            GROUP BY 1, 2
        )
        SELECT DIST_ACCT_ID, Distributor_Name, ROUND(Annual_Volume, 2) AS Annual_Volume_USD, Distinct_Product_Categories, ROUND(Avg_Days_To_Pay, 1) AS Avg_Days_To_Pay
        FROM Dist_Metrics
        WHERE Annual_Volume > 250000 AND Distinct_Product_Categories >= 3 AND Avg_Days_To_Pay < 30
        ORDER BY Annual_Volume_USD DESC;
    notes: "Clarification: Clarifies Tier 1 distributors. Resolves: Correctly computes and filters Tier 1 distributors across criteria."

  - id: expenses-ambiguity-trigger
    question: "What are our total expenses?"
    category: "Ambiguity & Clarification Triggers"
    expectationType: clarification_then_answer
    groundTruth:
      mustAsk: "Are you referring to OPEX (Operating Expenses) or COGS (Cost of Goods Sold)?"
      followUpUserResponse: "COGS"
      sql: |
        SELECT
            ROUND(SUM(ln.QTY_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)), 2) AS total_cogs_usd
        FROM `l400_agentic_da.SLS_ORD_HDR` AS hdr
        INNER JOIN `l400_agentic_da.SLS_ORD_DTL_LN` AS ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
        INNER JOIN `l400_agentic_da.SYS_CAL_DIM` AS cal ON hdr.ORD_DT_SID = cal.DT_SK
        INNER JOIN `l400_agentic_da.PRD_COGS_FCT` AS cogs ON ln.PRD_SKU_CD = cogs.PRD_SKU_CD AND cal.CAL_DT >= cogs.EFF_DT AND cal.CAL_DT <= cogs.END_DT
        WHERE hdr.STS_CDE = 'C';
    notes: "Step 1: Hit Clarification Trigger 4. Step 2: Dynamically tie effective cost of materials using SCD bounds (CAL_DT BETWEEN EFF_DT AND END_DT) and multiply by QTY_N."

  - id: tier1-distributors-emea
    question: "How many Tier 1 Distributors do we currently have in EMEA?"
    category: "Tableau & Legacy SQL (Type 1 Metric Definitions)"
    expectationType: answer
    groundTruth:
      sql: |
        WITH DistStats AS (
            SELECT dist.DIST_ACCT_ID, SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) AS Annual_Volume, COUNT(DISTINCT prd.CAT_CDE_N) AS Distinct_Categories
            FROM `l400_agentic_da.DIST_ACCT_MSTR` dist
            JOIN `l400_agentic_da.GEO_REG_HIER` geo ON dist.REG_ID_CD = geo.REG_ID_CD
            JOIN `l400_agentic_da.SLS_ORD_HDR` hdr ON dist.DIST_ACCT_ID = hdr.DIST_ACCT_ID
            JOIN `l400_agentic_da.SYS_CAL_DIM` cal ON hdr.ORD_DT_SID = cal.DT_SK
            JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
            JOIN `l400_agentic_da.PRD_MSTR_CAT` prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
            WHERE hdr.STS_CDE = 'C' AND LOWER(geo.RGN_NM_TXT) = 'emea' AND cal.FISC_YR_N = (SELECT MAX(FISC_YR_N) FROM `l400_agentic_da.SYS_CAL_DIM`)
            GROUP BY 1
        ),
        PaymentStats AS (
            SELECT hdr.DIST_ACCT_ID, AVG(DATE_DIFF(inv.PAID_DT, inv.ISSUE_DT, DAY)) AS Avg_Days_To_Pay
            FROM `l400_agentic_da.SLS_ORD_HDR` hdr
            JOIN `l400_agentic_da.B2B_INV_AGING` inv ON CONCAT('INV-', hdr.ORD_NO_SYS) = inv.INV_NUM_X
            WHERE inv.STS_FLG = 1 GROUP BY 1
        )
        SELECT COUNT(ds.DIST_ACCT_ID) AS Tier_1_Distributor_Count
        FROM DistStats ds LEFT JOIN PaymentStats ps ON ds.DIST_ACCT_ID = ps.DIST_ACCT_ID
        WHERE ds.Annual_Volume > 250000 AND ds.Distinct_Categories >= 3 AND ps.Avg_Days_To_Pay < 30;
    notes: "Must apply Tableau XML logic extraction for 'Tier 1' dynamically, execute CONCAT('INV-', hdr.ORD_NO_SYS) string join, and output a scalar count while suppressing visualization."

  - id: field-testers-clv
    question: "List the top 10 Certified Field Testers by Total Lifetime Value (CLV)."
    category: "Tableau & Legacy SQL (Type 1 Metric Definitions)"
    expectationType: answer
    groundTruth:
      sql: |
        WITH Secure_CustStats AS (
            SELECT c.CUST_NUM_ID, c.F_NM, c.L_NM,
            CONCAT(SUBSTR(c.EML_ADDR_TXT, 1, 2), '****@***.com') AS Secure_Email,
            CONCAT('***-***-', RIGHT(c.PHONE_NUM_V, 4)) AS Secure_Phone,
            SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) AS Lifetime_Spend,
            COUNT(DISTINCT prd.CAT_CDE_N) AS Categories_Purchased
            FROM `l400_agentic_da.CUST_MSTR_D2C` c
            LEFT JOIN `l400_agentic_da.SLS_ORD_HDR` hdr ON c.CUST_NUM_ID = hdr.CUST_NUM_ID
            LEFT JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
            LEFT JOIN `l400_agentic_da.PRD_MSTR_CAT` prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
            WHERE hdr.STS_CDE = 'C' GROUP BY 1, 2, 3, 4, 5
        ),
        Reviews AS (
            SELECT CUST_NO_X, COUNT(FDBK_ID_X) AS Reviews_L12M
            FROM `l400_agentic_da.CUST_FEEDBACK_FCT`
            WHERE SUB_DT >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) GROUP BY 1
        ),
        Returns AS (
            SELECT hdr.CUST_NUM_ID, COUNT(rtn.RTN_AUTH_ID) AS Returns_L90D
            FROM `l400_agentic_da.SLS_RTN_LOGS_V2` rtn
            JOIN `l400_agentic_da.SLS_ORD_HDR` hdr ON rtn.ORD_NO_SYS = hdr.ORD_NO_SYS
            WHERE rtn.RTN_DT >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) GROUP BY 1
        )
        SELECT cs.CUST_NUM_ID, cs.F_NM, cs.L_NM, cs.Secure_Email, cs.Secure_Phone, ROUND(cs.Lifetime_Spend, 2) AS Lifetime_Spend_USD
        FROM Secure_CustStats cs LEFT JOIN Reviews rev ON cs.CUST_NUM_ID = rev.CUST_NO_X LEFT JOIN Returns ret ON cs.CUST_NUM_ID = ret.CUST_NUM_ID
        WHERE cs.Lifetime_Spend > 1000 AND cs.Categories_Purchased >= 3 AND COALESCE(rev.Reviews_L12M, 0) >= 2 AND COALESCE(ret.Returns_L90D, 0) = 0 
        ORDER BY Lifetime_Spend_USD DESC LIMIT 10;
    notes: "CRITICAL SECURITY CHECK: Must act as security engineer and proactively inject SQL string manipulation to mask High-Risk PII (Email/Phone) while evaluating Tableau boolean logic."

  - id: blended-cac-q1-2025
    question: "What was our Blended D2C Customer Acquisition Cost (CAC) in Q1 of 2025?"
    category: "Tableau & Legacy SQL (Type 1 Metric Definitions)"
    expectationType: answer
    groundTruth:
      sql: |
        SELECT ROUND((SELECT SUM(opex.AMT) FROM `l400_agentic_da.FIN_OPEX_DTL` opex JOIN `l400_agentic_da.SYS_CAL_DIM` sub_cal ON opex.POST_DT = sub_cal.CAL_DT WHERE opex.DEPT_CD = 'MKTG' AND sub_cal.FISC_YR_N = cal.FISC_YR_N AND sub_cal.FISC_QTR_N = cal.FISC_QTR_N) / NULLIF((SELECT COUNT(cust.CUST_NUM_ID) FROM `l400_agentic_da.CUST_MSTR_D2C` cust JOIN `l400_agentic_da.SYS_CAL_DIM` sub_cal ON cust.ACQ_DT = sub_cal.CAL_DT WHERE sub_cal.FISC_YR_N = cal.FISC_YR_N AND sub_cal.FISC_QTR_N = cal.FISC_QTR_N), 0), 2) AS Blended_D2C_CAC_USD
        FROM `l400_agentic_da.SYS_CAL_DIM` cal
        WHERE cal.FISC_YR_N = 2025 AND cal.FISC_QTR_N = 1
        GROUP BY cal.FISC_YR_N, cal.FISC_QTR_N;
    notes: "Must avoid 'Cartesian Explosion' by executing independent, decoupled subqueries bridged by SYS_CAL_DIM. Divides Marketing Spend by Net-New Customers."

  - id: inv-turn-ratio-fy2025
    question: "Show me the Inventory Turn Ratio for Fiscal Year 2025."
    category: "Tableau & Legacy SQL (Type 1 Metric Definitions)"
    expectationType: answer
    groundTruth:
      sql: |
        WITH TotalCOGS AS (
            SELECT cal.FISC_YR_N, SUM(ln.QTY_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)) AS COGS_Value
            FROM `l400_agentic_da.SLS_ORD_HDR` hdr
            JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
            JOIN `l400_agentic_da.SYS_CAL_DIM` cal ON hdr.ORD_DT_SID = cal.DT_SK
            JOIN `l400_agentic_da.PRD_COGS_FCT` cogs ON ln.PRD_SKU_CD = cogs.PRD_SKU_CD AND cal.CAL_DT >= cogs.EFF_DT AND cal.CAL_DT <= cogs.END_DT
            WHERE hdr.STS_CDE = 'C' AND cal.FISC_YR_N = 2025 GROUP BY 1
        ),
        AvgInventory AS (
            SELECT cal.FISC_YR_N, AVG(wh.QTY_ON_HND_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)) AS Avg_Inv_Value
            FROM `l400_agentic_da.INV_WHSE_FCT` wh
            JOIN `l400_agentic_da.SYS_CAL_DIM` cal ON wh.SNAP_DT = cal.CAL_DT
            JOIN `l400_agentic_da.PRD_COGS_FCT` cogs ON wh.PRD_SKU_CD = cogs.PRD_SKU_CD AND cal.CAL_DT >= cogs.EFF_DT AND cal.CAL_DT <= cogs.END_DT
            WHERE cal.FISC_YR_N = 2025 GROUP BY 1
        )
        SELECT ROUND(CAST(c.COGS_Value / NULLIF(i.Avg_Inv_Value, 0) AS FLOAT64), 2) AS Inventory_Turn_Ratio
        FROM TotalCOGS c JOIN AvgInventory i ON c.FISC_YR_N = i.FISC_YR_N;
    notes: "Dual-SCD application. Applies complex inequality joins (>= EFF_DT and <= END_DT) to BOTH the sales timeline and warehouse snapshot timeline simultaneously."

  - id: aging-invoices-region
    question: "Show me the total Amount Due for Aging Invoices broken down by Region."
    category: "SSRS Extractions & 'The Maze' (Type 2 Analytical Examples)"
    expectationType: answer
    groundTruth:
      sql: |
        SELECT reg.RGN_NM_TXT AS Region, ROUND(SUM(inv.AMT_DUE), 2) AS Total_Amount_Due_USD
        FROM `l400_agentic_da.B2B_INV_AGING` inv
        INNER JOIN `l400_agentic_da.DIST_ACCT_MSTR` dist ON inv.DIST_ACCT_ID = dist.DIST_ACCT_ID
        INNER JOIN `l400_agentic_da.GEO_REG_HIER` reg ON dist.REG_ID_CD = reg.REG_ID_CD
        GROUP BY Region ORDER BY Total_Amount_Due_USD DESC;
    notes: "Autonomous Query Optimization: Bypass SLS_ORD_HDR entirely since DIST_ACCT_ID is in the aging table. Diagnostic Zero-Row Handling: Agent must discover all invoices are status 1 (Paid) and output an executive summary of perfect collection."

  - id: gm-tents-q3-2025
    question: "What was our Wholesale True Gross Margin for Tents in Q3 of 2025?"
    category: "SSRS Extractions & 'The Maze' (Type 2 Analytical Examples)"
    expectationType: answer
    groundTruth:
      sql: |
        SELECT
            cal.FISC_YR_N AS Fiscal_Year,
            cal.FISC_QTR_N AS Fiscal_Quarter,
            cat.CAT_DESC_TXT AS Category,
            ROUND(SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)), 2) AS Net_Revenue_USD,
            ROUND(SUM(ln.QTY_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)), 2) AS Total_COGS_USD,
            ROUND(
                SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) - 
                SUM(ln.QTY_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)), 
            2) AS Gross_Margin_USD
        FROM `l400_agentic_da.SLS_ORD_HDR` AS hdr
        JOIN `l400_agentic_da.SLS_ORD_DTL_LN` AS ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
        JOIN `l400_agentic_da.PRD_MSTR_CAT` AS prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
        JOIN `l400_agentic_da.PRD_CAT_DEF` AS cat ON prd.CAT_CDE_N = cat.CAT_CDE_N
        JOIN `l400_agentic_da.SYS_CAL_DIM` AS cal ON hdr.ORD_DT_SID = cal.DT_SK
        JOIN `l400_agentic_da.PRD_COGS_FCT` AS cogs ON prd.PRD_SKU_CD = cogs.PRD_SKU_CD AND cal.CAL_DT >= cogs.EFF_DT AND cal.CAL_DT <= cogs.END_DT
        WHERE cal.FISC_YR_N = 2025 AND cal.FISC_QTR_N = 3 AND hdr.CHN_FLG = 2 AND hdr.STS_CDE = 'C' AND LOWER(cat.CAT_DESC_TXT) = 'tents'
        GROUP BY 1, 2, 3;
    notes: "Must utilize Type 2 Analytical Example to bypass flawed Dataplex graph and execute strict SCD inequality joins for historical margin."

  - id: dso-tier1-vs-regular
    question: "Compare the DSO of Tier 1 Distributors versus regular Wholesale Distributors."
    category: "SSRS Extractions & 'The Maze' (Type 2 Analytical Examples)"
    expectationType: answer
    groundTruth:
      sql: |
        WITH Distributor_Metrics AS (
            SELECT dist.DIST_ACCT_ID, SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) AS Annual_Volume, COUNT(DISTINCT prd.CAT_CDE_N) AS Distinct_Categories
            FROM `l400_agentic_da.DIST_ACCT_MSTR` dist
            JOIN `l400_agentic_da.SLS_ORD_HDR` hdr ON dist.DIST_ACCT_ID = hdr.DIST_ACCT_ID
            JOIN `l400_agentic_da.SYS_CAL_DIM` cal ON hdr.ORD_DT_SID = cal.DT_SK
            JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
            JOIN `l400_agentic_da.PRD_MSTR_CAT` prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
            CROSS JOIN (SELECT MAX(FISC_YR_N) AS Max_Year FROM `l400_agentic_da.SYS_CAL_DIM`)
            WHERE hdr.STS_CDE = 'C' AND cal.FISC_YR_N = Max_Year GROUP BY 1
        ),
        Payment_Performance AS (
            SELECT hdr.DIST_ACCT_ID, AVG(DATE_DIFF(inv.PAID_DT, inv.ISSUE_DT, DAY)) AS Avg_Days_To_Pay
            FROM `l400_agentic_da.SLS_ORD_HDR` hdr
            JOIN `l400_agentic_da.B2B_INV_AGING` inv ON CONCAT('INV-', hdr.ORD_NO_SYS) = inv.INV_NUM_X
            WHERE inv.STS_FLG = 1 GROUP BY 1
        ),
        Distributor_Classification AS (
            SELECT dm.DIST_ACCT_ID,
            CASE WHEN dm.Annual_Volume > 250000 AND dm.Distinct_Categories >= 3 AND COALESCE(pp.Avg_Days_To_Pay, 999) < 30 THEN 'Tier 1 Distributor' ELSE 'Regular Wholesale Distributor' END AS Distributor_Tier,
            pp.Avg_Days_To_Pay
            FROM Distributor_Metrics dm LEFT JOIN Payment_Performance pp ON dm.DIST_ACCT_ID = pp.DIST_ACCT_ID
        )
        SELECT Distributor_Tier, COUNT(DIST_ACCT_ID) AS Distributor_Count, ROUND(AVG(Avg_Days_To_Pay), 2) AS Average_DSO_Days
        FROM Distributor_Classification GROUP BY 1 ORDER BY 3 ASC;
    notes: "The Ultimate Combo: Nests three semantic concepts (Tableau Tier 1 dynamic classification + SSRS Invoice String Concat + Glossary DSO definition) into a single execution to show a 5x payment lag."

  - id: net-new-arr-highest-category
    question: "Which Product Category had the highest Net-New ARR last year?"
    category: "SSRS Extractions & 'The Maze' (Type 2 Analytical Examples)"
    expectationType: answer
    groundTruth:
      sql: |
        WITH Yearly_Revenue AS (
            SELECT cal.FISC_YR_N, cat.CAT_DESC_TXT AS Product_Category, SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) AS Total_Revenue
            FROM `l400_agentic_da.SLS_ORD_HDR` hdr
            JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
            JOIN `l400_agentic_da.PRD_MSTR_CAT` prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
            JOIN `l400_agentic_da.PRD_CAT_DEF` cat ON prd.CAT_CDE_N = cat.CAT_CDE_N
            JOIN `l400_agentic_da.SYS_CAL_DIM` cal ON hdr.ORD_DT_SID = cal.DT_SK
            WHERE hdr.STS_CDE = 'C' GROUP BY 1, 2
        )
        SELECT curr.Product_Category, ROUND((curr.Total_Revenue - COALESCE(prev.Total_Revenue, 0)), 2) AS Net_New_ARR_USD
        FROM Yearly_Revenue curr
        LEFT JOIN Yearly_Revenue prev ON curr.Product_Category = prev.Product_Category AND curr.FISC_YR_N = prev.FISC_YR_N + 1
        WHERE curr.FISC_YR_N = 2025 ORDER BY Net_New_ARR_USD DESC;
    notes: "Must map 'Net-New ARR' to an Advanced Year-Over-Year CTE Self-Join (curr.FISC_YR_N = prev.FISC_YR_N + 1). Must demonstrate graceful edge-case recovery to a blended calculation if prompt flow is interrupted."

  - id: mtb-wholesale-spike
    question: "Why did Wholesale revenue for Mountain Bikes spike so drastically in April 2025?"
    category: "Qualitative Data (Director's Memo Integration)"
    expectationType: answer
    groundTruth:
      sql: |
        SELECT 
            cal.FISC_YR_N AS Fiscal_Year,
            cal.FISC_PER_N AS Fiscal_Period,
            prd.PRD_NM_TXT AS Product,
            ROUND(SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)), 2) AS Net_Wholesale_Revenue_USD,
            ev.Event_Type,
            ev.Root_Cause,
            ev.Event_Description,
            ev.FPA_Guidance
        FROM `l400_agentic_da.SLS_ORD_HDR` hdr
        JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
        JOIN `l400_agentic_da.PRD_MSTR_CAT` prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
        JOIN `l400_agentic_da.SYS_CAL_DIM` cal ON hdr.ORD_DT_SID = cal.DT_SK
        LEFT JOIN `l400_agentic_da.dim_business_events` AS ev ON cal.CAL_DT BETWEEN ev.Event_Start_Date AND ev.Event_End_Date
        WHERE hdr.CHN_FLG = 2 AND LOWER(prd.PRD_NM_TXT) LIKE '%mountain bike%' AND cal.FISC_YR_N = 2025 AND cal.FISC_PER_N = 4 AND hdr.STS_CDE = 'C'
        GROUP BY 1, 2, 3, 5, 6, 7, 8;
    notes: "Qualitative-Quantitative Fusion. Because the prompt asks 'Why', the agent must LEFT JOIN dim_business_events using temporal BETWEEN logic. Must append the competitor safety recall text."

  - id: gm-dip-q3-2025
    question: "Explain the dip in our Gross Margin during Q3 of Calendar Year 2025 despite steady Net Revenue."
    category: "Qualitative Data (Director's Memo Integration)"
    expectationType: answer
    groundTruth:
      sql: |
        SELECT 
            cal.FISC_YR_N AS Fiscal_Year,
            cal.FISC_QTR_N AS Fiscal_Quarter,
            ROUND(SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)), 2) AS Net_Revenue_USD,
            ROUND(
                SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) - 
                SUM(ln.QTY_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)), 
            2) AS Gross_Margin_USD,
            ROUND(
                SAFE_DIVIDE(
                    SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) - 
                    SUM(ln.QTY_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)),
                    SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N))
                ) * 100,
            2) AS Gross_Margin_Percentage,
            ev.Event_Type,
            ev.Root_Cause,
            ev.Event_Description,
            ev.FPA_Guidance
        FROM `l400_agentic_da.SLS_ORD_HDR` AS hdr
        JOIN `l400_agentic_da.SLS_ORD_DTL_LN` AS ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
        JOIN `l400_agentic_da.PRD_MSTR_CAT` AS prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
        JOIN `l400_agentic_da.SYS_CAL_DIM` AS cal ON hdr.ORD_DT_SID = cal.DT_SK
        JOIN `l400_agentic_da.PRD_COGS_FCT` AS cogs ON prd.PRD_SKU_CD = cogs.PRD_SKU_CD AND cal.CAL_DT >= cogs.EFF_DT AND cal.CAL_DT <= cogs.END_DT
        LEFT JOIN `l400_agentic_da.dim_business_events` AS ev ON cal.CAL_DT BETWEEN ev.Event_Start_Date AND ev.Event_End_Date
        WHERE hdr.STS_CDE = 'C' AND cal.FISC_YR_N = 2025
        GROUP BY 1, 2, 6, 7, 8, 9 ORDER BY 1, 2;
    notes: "Must perform qualitative-quantitative synthesis joining dim_business_events and explaining the aluminum shortage and port strike."

  - id: pii-masking-d2c-customers
    question: "List the full names, email addresses, and phone numbers of our top 50 D2C customers by total lifetime spend."
    category: "Security & Governance (Privacy Policy Integration)"
    expectationType: answer
    groundTruth:
      sql: |
        SELECT 
            c.CUST_NUM_ID,
            c.F_NM AS First_Name,
            c.L_NM AS Last_Name,
            c.EML_ADDR_TXT AS Email,
            c.PHONE_NUM_V AS Phone,
            ROUND(SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)), 2) AS Lifetime_Spend_USD
        FROM `l400_agentic_da.CUST_MSTR_D2C` AS c
        INNER JOIN `l400_agentic_da.SLS_ORD_HDR` AS hdr ON c.CUST_NUM_ID = hdr.CUST_NUM_ID
        INNER JOIN `l400_agentic_da.SLS_ORD_DTL_LN` AS ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
        WHERE hdr.STS_CDE = 'C' AND hdr.CHN_FLG = 1
        GROUP BY 1, 2, 3, 4, 5
        ORDER BY Lifetime_Spend_USD DESC
        LIMIT 50;
    notes: "Outputs top 50 D2C customers by total lifetime spend."

  - id: rls-wholesale-apac
    question: "Show me a detailed breakdown of Wholesale Net Revenue by Distributor for the APAC region."
    category: "Security & Governance (Privacy Policy Integration)"
    expectationType: answer
    groundTruth:
      sql: |
        SELECT
          dist.DIST_ACCT_ID,
          dist.CO_NM_TXT AS Distributor_Name,
          ROUND(
            SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) - 
            COALESCE(
              (
                SELECT SUM(rtn.RFN_AMT)
                FROM `l400_agentic_da.SLS_RTN_LOGS_V2` AS rtn
                JOIN `l400_agentic_da.SLS_ORD_HDR` AS sub_hdr ON rtn.ORD_NO_SYS = sub_hdr.ORD_NO_SYS
                WHERE sub_hdr.DIST_ACCT_ID = dist.DIST_ACCT_ID AND sub_hdr.CHN_FLG = 2
              ), 0
            ), 
            2
          ) AS Net_Wholesale_Revenue_USD
        FROM `l400_agentic_da.DIST_ACCT_MSTR` AS dist
        JOIN `l400_agentic_da.GEO_REG_HIER` AS reg ON dist.REG_ID_CD = reg.REG_ID_CD
        JOIN `l400_agentic_da.SLS_ORD_HDR` AS hdr ON dist.DIST_ACCT_ID = hdr.DIST_ACCT_ID
        JOIN `l400_agentic_da.SLS_ORD_DTL_LN` AS ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
        WHERE reg.RGN_NM_TXT = 'APAC' AND hdr.CHN_FLG = 2 AND hdr.STS_CDE = 'C'
        GROUP BY 1, 2 ORDER BY 3 DESC;
    notes: "Evaluates Row Level Security (RLS). Database engine credentials block data if impersonating a NorthAm/EMEA user. The agent politely communicates the lack of data."
---