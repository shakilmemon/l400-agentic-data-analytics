/* ==============================================================================
   FILE: Legacy_Oracle_Export.sql
   OWNER: Corporate Finance / Supply Chain
   NOTE: Run these manually on the 5th of every month for the executive packet.
============================================================================== */

-- ------------------------------------------------------------------------------
-- METRIC: Blended D2C Customer Acquisition Cost (CAC)
-- DESCRIPTION: Calculates how much marketing spend it takes to acquire a new D2C customer. Matches the Glossary definition by dividing Marketing OPEX by Net-New D2C customers.
-- CAUTION: Only include Marketing department OPEX.
-- ------------------------------------------------------------------------------
SELECT 
    cal.FISC_YR_N,
    cal.FISC_QTR_N,
    (
        -- Total Marketing OPEX for the period
        SELECT SUM(AMT) 
        FROM l400_agentic_da.FIN_OPEX_DTL opex
        JOIN l400_agentic_da.SYS_CAL_DIM sub_cal ON opex.POST_DT = sub_cal.CAL_DT
        WHERE opex.DEPT_CD = 'MKTG' 
          AND sub_cal.FISC_YR_N = cal.FISC_YR_N 
          AND sub_cal.FISC_QTR_N = cal.FISC_QTR_N
    ) / 
    (
        -- Divided by Net New D2C Customers Acquired
        SELECT COUNT(CUST_NUM_ID) 
        FROM l400_agentic_da.CUST_MSTR_D2C cust
        JOIN l400_agentic_da.SYS_CAL_DIM sub_cal ON cust.ACQ_DT = sub_cal.CAL_DT
        WHERE sub_cal.FISC_YR_N = cal.FISC_YR_N 
          AND sub_cal.FISC_QTR_N = cal.FISC_QTR_N
    ) AS Blended_D2C_CAC
FROM l400_agentic_da.SYS_CAL_DIM cal
GROUP BY 1, 2
ORDER BY 1 DESC, 2 DESC;


-- ------------------------------------------------------------------------------
-- METRIC: Inventory Turn Ratio 
-- DESCRIPTION: Measures how many times inventory is sold and replaced over a period.
-- FORMULA: Total COGS / Average Inventory Value
-- ------------------------------------------------------------------------------
WITH TotalCOGS AS (
    SELECT 
        cal.FISC_YR_N,
        SUM(ln.QTY_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)) AS COGS_Value
    FROM l400_agentic_da.SLS_ORD_HDR hdr
    JOIN l400_agentic_da.SLS_ORD_DTL_LN ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
    JOIN l400_agentic_da.SYS_CAL_DIM cal ON hdr.ORD_DT_SID = cal.DT_SK
    JOIN l400_agentic_da.PRD_COGS_FCT cogs 
        ON ln.PRD_SKU_CD = cogs.PRD_SKU_CD
        AND cal.CAL_DT >= cogs.EFF_DT 
        AND cal.CAL_DT <= cogs.END_DT
    WHERE hdr.STS_CDE = 'C'
    GROUP BY 1
),
AvgInventory AS (
    SELECT 
        cal.FISC_YR_N,
        AVG(wh.QTY_ON_HND_N * (cogs.MTL_CST_AMT + cogs.LBR_CST_AMT + cogs.TRFF_AMT)) AS Avg_Inv_Value
    FROM l400_agentic_da.INV_WHSE_FCT wh
    JOIN l400_agentic_da.SYS_CAL_DIM cal ON wh.SNAP_DT = cal.CAL_DT
    JOIN l400_agentic_da.PRD_COGS_FCT cogs 
        ON wh.PRD_SKU_CD = cogs.PRD_SKU_CD
        AND cal.CAL_DT >= cogs.EFF_DT 
        AND cal.CAL_DT <= cogs.END_DT
    GROUP BY 1
)
SELECT 
    c.FISC_YR_N AS FiscalYear,
    c.COGS_Value / NULLIF(i.Avg_Inv_Value, 0) AS Inventory_Turn_Ratio
FROM TotalCOGS c
JOIN AvgInventory i ON c.FISC_YR_N = i.FISC_YR_N;


-- ------------------------------------------------------------------------------
-- METRIC: Net Revenue
-- DESCRIPTION: Calculates the total revenue after accounting for returns. This fulfills the Dataplex Glossary definition ("Gross Revenue minus applied discounts and refunds") without duplicating the underlying sales lines. Uses a correlated subquery to map return dates back to the original order's fiscal period.
-- FORMULA: Gross Revenue - Returns
-- ------------------------------------------------------------------------------
SELECT 
    cal.FISC_YR_N AS FiscalYear,
    SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) - 
    COALESCE((
        SELECT SUM(rtn.RFN_AMT) 
        FROM l400_agentic_da.SLS_RTN_LOGS_V2 rtn 
        JOIN l400_agentic_da.SLS_ORD_HDR sub_hdr ON rtn.ORD_NO_SYS = sub_hdr.ORD_NO_SYS
        JOIN l400_agentic_da.SYS_CAL_DIM sub_cal ON sub_hdr.ORD_DT_SID = sub_cal.DT_SK
        WHERE sub_hdr.CHN_FLG = hdr.CHN_FLG AND sub_cal.FISC_YR_N = cal.FISC_YR_N
    ), 0) AS Net_Revenue
FROM l400_agentic_da.SLS_ORD_HDR hdr
JOIN l400_agentic_da.SLS_ORD_DTL_LN ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
JOIN l400_agentic_da.SYS_CAL_DIM cal ON hdr.ORD_DT_SID = cal.DT_SK
WHERE hdr.STS_CDE = 'C'
GROUP BY 1, hdr.CHN_FLG
ORDER BY 1 DESC;


-- ------------------------------------------------------------------------------
-- METRIC: Current On-Hand Inventory
-- DESCRIPTION: Calculates the current inventory levels across warehouses. CRITICAL: The inventory table is a weekly snapshot. We must ONLY sum the most recent snapshot date, otherwise historical units will be double-counted.
-- ------------------------------------------------------------------------------
SELECT 
    wh.WHSE_LOC_CD AS Warehouse,
    SUM(wh.QTY_ON_HND_N) AS Total_On_Hand_Inventory
FROM l400_agentic_da.INV_WHSE_FCT wh
JOIN l400_agentic_da.PRD_MSTR_CAT prd ON wh.PRD_SKU_CD = prd.PRD_SKU_CD
WHERE wh.SNAP_DT = (SELECT MAX(SNAP_DT) FROM l400_agentic_da.INV_WHSE_FCT)
GROUP BY 1
ORDER BY 2 DESC;


-- ------------------------------------------------------------------------------
-- METRIC: Net-New ARR (Year-Over-Year Delta)
-- DESCRIPTION: Calculates the true Net-New growth by comparing current year revenue against the previous year's revenue (Year-over-Year Delta) for each product category.
-- ------------------------------------------------------------------------------
WITH Yearly_Revenue AS (
    SELECT 
        cal.FISC_YR_N,
        cat.CAT_DESC_TXT AS Product_Category,
        SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) AS Total_Revenue
    FROM l400_agentic_da.SLS_ORD_HDR hdr
    JOIN l400_agentic_da.SLS_ORD_DTL_LN ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
    JOIN l400_agentic_da.PRD_MSTR_CAT prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
    JOIN l400_agentic_da.PRD_CAT_DEF cat ON prd.CAT_CDE_N = cat.CAT_CDE_N
    JOIN l400_agentic_da.SYS_CAL_DIM cal ON hdr.ORD_DT_SID = cal.DT_SK
    WHERE hdr.STS_CDE = 'C'
    GROUP BY 1, 2
)
SELECT 
    curr.FISC_YR_N AS FiscalYear,
    curr.Product_Category,
    ROUND((curr.Total_Revenue - COALESCE(prev.Total_Revenue, 0)), 2) AS Net_New_ARR
FROM Yearly_Revenue curr
LEFT JOIN Yearly_Revenue prev 
    ON curr.Product_Category = prev.Product_Category 
    AND curr.FISC_YR_N = prev.FISC_YR_N + 1
ORDER BY curr.FISC_YR_N DESC, Net_New_ARR DESC;