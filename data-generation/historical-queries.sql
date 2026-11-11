-- ==============================================================================
-- QUERY 1: The "Daily Sales & Margin" Dashboard Seed
-- Teaches Dataplex: Orders -> Lines -> Products -> Categories -> Dates
-- ==============================================================================
SELECT 
    cal.CAL_DT,
    cat.CAT_DESC_TXT,
    prd.PRD_NM_TXT,
    SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) AS Net_Revenue
FROM `l400_agentic_da.SLS_ORD_HDR` hdr
JOIN `l400_agentic_da.SYS_CAL_DIM` cal 
    ON hdr.ORD_DT_SID = cal.DT_SK
JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln 
    ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
JOIN `l400_agentic_da.PRD_MSTR_CAT` prd 
    ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
JOIN `l400_agentic_da.PRD_CAT_DEF` cat 
    ON prd.CAT_CDE_N = cat.CAT_CDE_N
WHERE hdr.STS_CDE = 'C'
GROUP BY 1, 2, 3;


-- ==============================================================================
-- QUERY 2: The "D2C Apex Customer" Dashboard Seed
-- Teaches Dataplex the tricky mismatched key: CUST_NUM_ID = CUST_NO_X
-- Also teaches Returns and Feedback JOIN paths.
-- ==============================================================================
SELECT 
    c.CUST_NUM_ID,
    c.EML_ADDR_TXT,
    COUNT(DISTINCT hdr.ORD_NO_SYS) AS Total_Orders,
    COUNT(DISTINCT fb.FDBK_ID_X) AS Total_Reviews,
    SUM(rtn.RFN_AMT) AS Total_Refunds
FROM `l400_agentic_da.CUST_MSTR_D2C` c
JOIN `l400_agentic_da.SLS_ORD_HDR` hdr 
    ON c.CUST_NUM_ID = hdr.CUST_NUM_ID
LEFT JOIN `l400_agentic_da.CUST_FEEDBACK_FCT` fb 
    ON c.CUST_NUM_ID = fb.CUST_NO_X     -- <== The crucial mismatched key!
LEFT JOIN `l400_agentic_da.SLS_RTN_LOGS_V2` rtn 
    ON hdr.ORD_NO_SYS = rtn.ORD_NO_SYS
GROUP BY 1, 2;


-- ==============================================================================
-- QUERY 3: The "Wholesale Aging & Region" Dashboard Seed
-- Teaches Dataplex: Distributors -> Regions, and Invoice String Concat JOINs
-- ==============================================================================
SELECT 
    reg.RGN_NM_TXT,
    reg.SUB_RGN_TXT,
    dist.CO_NM_TXT,
    inv.ISSUE_DT,
    inv.AMT_DUE
FROM `l400_agentic_da.DIST_ACCT_MSTR` dist
JOIN `l400_agentic_da.GEO_REG_HIER` reg 
    ON dist.REG_ID_CD = reg.REG_ID_CD
JOIN `l400_agentic_da.SLS_ORD_HDR` hdr 
    ON dist.DIST_ACCT_ID = hdr.DIST_ACCT_ID
JOIN `l400_agentic_da.B2B_INV_AGING` inv 
    ON CONCAT('INV-', hdr.ORD_NO_SYS) = inv.INV_NUM_X
WHERE inv.STS_FLG = 0; -- Unpaid invoices


-- ==============================================================================
-- QUERY 4: The "CFO Financial Ledger" Dashboard Seed
-- Teaches Dataplex: GL Facts -> GL Accounts -> Dates
-- ==============================================================================
SELECT 
    cal.FISC_YR_N,
    cal.FISC_QTR_N,
    acct.ACCT_NM_STR,
    SUM(CASE WHEN fct.DR_CR_IND = 'D' THEN fct.AMT_BASE ELSE 0 END) AS Total_Debits,
    SUM(CASE WHEN fct.DR_CR_IND = 'C' THEN fct.AMT_BASE ELSE 0 END) AS Total_Credits
FROM `l400_agentic_da.GL_F_TRX_00` fct
JOIN `l400_agentic_da.GL_ACCT_MSTR` acct 
    ON fct.ACCT_ID_X = acct.ACCT_ID_X
JOIN `l400_agentic_da.SYS_CAL_DIM` cal 
    ON fct.POST_DT_SK = cal.DT_SK
GROUP BY 1, 2, 3;


-- ==============================================================================
-- QUERY 5: The "Supply Chain COGS & Inventory" Dashboard Seed
-- Teaches Dataplex: Slowly Changing Dimensions (Dates between EFF_DT and END_DT)
-- ==============================================================================
SELECT 
    cal.FISC_YR_N,
    cal.FISC_PER_N,
    prd.PRD_NM_TXT,
    wh.WHSE_LOC_CD,
    wh.QTY_ON_HND_N,
    cogs.MTL_CST_AMT,
    cogs.LBR_CST_AMT
FROM `l400_agentic_da.INV_WHSE_FCT` wh
JOIN `l400_agentic_da.PRD_MSTR_CAT` prd 
    ON wh.PRD_SKU_CD = prd.PRD_SKU_CD
JOIN `l400_agentic_da.SYS_CAL_DIM` cal 
    ON wh.SNAP_DT = cal.CAL_DT
JOIN `l400_agentic_da.PRD_COGS_FCT` cogs 
    ON prd.PRD_SKU_CD = cogs.PRD_SKU_CD
    AND cal.CAL_DT >= cogs.EFF_DT 
    AND cal.CAL_DT <= cogs.END_DT;  -- <== Teaches CA how to resolve SCDs