-- ==============================================================================
-- 1. FINANCE & ACCOUNTING (General Ledger)
-- ==============================================================================

CREATE OR REPLACE TABLE `l400_agentic_da.GL_ACCT_MSTR` (
    ACCT_ID_X STRING,         -- e.g., 'GL00100'
    ACCT_NM_STR STRING,       -- e.g., 'Gross Revenue - Retail'
    BAL_SHT_FLG INT64,        -- 1 = Balance Sheet, 0 = Income Statement
    ACT_INACT_IND STRING      -- 'A' or 'I'
);

CREATE OR REPLACE TABLE `l400_agentic_da.GL_F_TRX_00` (
    TRX_ID_N INT64,
    ACCT_ID_X STRING,
    POST_DT_SK INT64,         -- e.g., 20241031 (Date Dimension Key)
    DR_CR_IND STRING,         -- 'D' (Debit) or 'C' (Credit)
    AMT_BASE NUMERIC,         -- Transaction amount
    SRC_SYS_CDE STRING        -- 'SLS', 'INV', 'HR'
);

CREATE OR REPLACE TABLE `l400_agentic_da.FIN_OPEX_DTL` (
    EXP_ID STRING,
    DEPT_CD STRING,           -- 'MKTG', 'SALES', 'IT'
    SPND_TYP_IND INT64,       -- 10 = Digital Ad, 20 = Print, 30 = Event
    AMT NUMERIC,
    POST_DT DATE
);

-- ==============================================================================
-- 2. SYSTEM DATE DIMENSION (Classic Legacy ERP Feature)
-- ==============================================================================

CREATE OR REPLACE TABLE `l400_agentic_da.SYS_CAL_DIM` (
    DT_SK INT64,              -- 20241031
    CAL_DT DATE,              -- 2024-10-31
    FISC_YR_N INT64,          -- 2025
    FISC_QTR_N INT64,         -- 3
    FISC_PER_N INT64          -- 9 (Month of Fiscal Year)
);

-- ==============================================================================
-- 3. SALES & ORDERS (The "Maze")
-- ==============================================================================

CREATE OR REPLACE TABLE `l400_agentic_da.SLS_ORD_HDR` (
    ORD_NO_SYS STRING,
    CUST_NUM_ID STRING,       -- Null if wholesale
    DIST_ACCT_ID STRING,      -- Null if D2C
    ORD_DT_SID INT64,         -- Date Key
    CHN_FLG INT64,            -- 1 = D2C, 2 = Wholesale
    STS_CDE STRING            -- 'O' (Open), 'C' (Closed/Fulfilled), 'V' (Void)
);

CREATE OR REPLACE TABLE `l400_agentic_da.SLS_ORD_DTL_LN` (
    ORD_NO_SYS STRING,
    LN_NO_N INT64,
    PRD_SKU_CD STRING,
    QTY_N INT64,
    UNIT_PRC_AMT NUMERIC,
    DISC_PCT_N FLOAT64        -- e.g., 0.15 for 15% discount
);

CREATE OR REPLACE TABLE `l400_agentic_da.SLS_RTN_LOGS_V2` (
    RTN_AUTH_ID STRING,
    ORD_NO_SYS STRING,
    PRD_SKU_CD STRING,
    RTN_DT DATE,
    RSN_CDE_N INT64,          -- 1=Defective, 2=Wrong Size, 3=Changed Mind
    RFN_AMT NUMERIC
);

CREATE OR REPLACE TABLE `l400_agentic_da.B2B_INV_AGING` (
    INV_NUM_X STRING,
    DIST_ACCT_ID STRING,
    ISSUE_DT DATE,
    PAID_DT DATE,             -- Null if unpaid
    AMT_DUE NUMERIC,
    STS_FLG INT64             -- 0 = Open, 1 = Paid, 9 = Default/Collections
);

-- ==============================================================================
-- 4. CUSTOMERS & CHANNELS
-- ==============================================================================

CREATE OR REPLACE TABLE `l400_agentic_da.CUST_MSTR_D2C` (
    CUST_NUM_ID STRING,
    F_NM STRING,              -- PII
    L_NM STRING,              -- PII
    EML_ADDR_TXT STRING,      -- PII: Target for BigQuery Policy Tags
    PHONE_NUM_V STRING,       -- PII
    ACQ_DT DATE,
    OPT_IN_FLG INT64          -- 1 = Yes, 0 = No
);

CREATE OR REPLACE TABLE `l400_agentic_da.DIST_ACCT_MSTR` (
    DIST_ACCT_ID STRING,
    CO_NM_TXT STRING,
    REG_ID_CD STRING,
    ONBRD_DT DATE
);

CREATE OR REPLACE TABLE `l400_agentic_da.GEO_REG_HIER` (
    REG_ID_CD STRING,         -- e.g., 'R_01'
    CTRY_CD STRING,           -- 'US', 'UK', 'DE'
    RGN_NM_TXT STRING,        -- 'NorthAm', 'EMEA', 'APAC'
    SUB_RGN_TXT STRING        -- 'West Coast', 'Nordics'
);

CREATE OR REPLACE TABLE `l400_agentic_da.CUST_FEEDBACK_FCT` (
    FDBK_ID_X STRING,
    CUST_NO_X STRING,         -- Intentionally named differently than CUST_NUM_ID
    PRD_SKU_CD STRING,
    SUB_DT DATE,
    RTG_N INT64,              -- 1 to 5 stars
    VLD_FLG STRING            -- 'Y' (Verified Purchase) or 'N'
);

-- ==============================================================================
-- 5. PRODUCTS & SUPPLY CHAIN
-- ==============================================================================

CREATE OR REPLACE TABLE `l400_agentic_da.PRD_MSTR_CAT` (
    PRD_SKU_CD STRING,
    PRD_NM_TXT STRING,
    CAT_CDE_N INT64,          -- Intentionally normalized to force JOINs
    SUB_CAT_CDE_N INT64,
    LCH_DT DATE
);

CREATE OR REPLACE TABLE `l400_agentic_da.PRD_CAT_DEF` (
    CAT_CDE_N INT64,          -- e.g., 100, 200, 300
    CAT_DESC_TXT STRING       -- e.g., 'Bikes', 'Outerwear', 'Kayaks'
);

CREATE OR REPLACE TABLE `l400_agentic_da.PRD_COGS_FCT` (
    PRD_SKU_CD STRING,
    EFF_DT DATE,
    END_DT DATE,
    MTL_CST_AMT NUMERIC,      -- Raw material cost (e.g., Aluminum)
    LBR_CST_AMT NUMERIC,      -- Labor cost
    TRFF_AMT NUMERIC          -- Tariffs
);

CREATE OR REPLACE TABLE `l400_agentic_da.INV_WHSE_FCT` (
    WHSE_LOC_CD STRING,
    PRD_SKU_CD STRING,
    SNAP_DT DATE,             -- Weekly snapshot of inventory
    QTY_ON_HND_N INT64
);

CREATE OR REPLACE TABLE `l400_agentic_da.VNDR_SPLY_MSTR` (
    VNDR_ID_C STRING,
    VNDR_NM STRING,
    MTL_TYP_CD STRING         -- 'ALUM', 'CRBN', 'NYLN'
);

-- ==============================================================================
-- 6. HR & OPERATIONS
-- ==============================================================================

CREATE OR REPLACE TABLE `l400_agentic_da.HR_EMP_MSTR` (
    EMP_ID_N INT64,
    EMP_NM STRING,
    DEPT_CD STRING,
    HIRE_DT DATE
);

CREATE OR REPLACE TABLE `l400_agentic_da.SLS_REP_QUOTA` (
    EMP_ID_N INT64,
    REG_ID_CD STRING,
    QTR_TXT STRING,           -- e.g., '2024-Q1'
    QTA_AMT NUMERIC
);