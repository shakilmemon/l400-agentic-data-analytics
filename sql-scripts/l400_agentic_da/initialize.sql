/*##################################################################################
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     https://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###################################################################################*/

/*
Author: Adam Paternostro 

Use Cases:
    - Initializes the system (you can re-run this)

Description: 
    - Loads all tables from the public storage account
    - Uses AVRO so we can bring in JSON and GEO types

References:
    - 

Clean up / Reset script:
    -  n/a

*/


------------------------------------------------------------------------------------------------------------
-- Create GenAI / Vertex AI connections
------------------------------------------------------------------------------------------------------------
CREATE MODEL IF NOT EXISTS `${project_id}.${bigquery_l400_agentic_da_dataset}.gemini_3_0_flash`
  REMOTE WITH CONNECTION `${project_id}.us.vertex-ai`
  OPTIONS (endpoint = 'https://aiplatform.googleapis.com/v1/projects/${project_id}/locations/global/publishers/google/models/gemini-3-flash-preview');

CREATE MODEL IF NOT EXISTS `${project_id}.${bigquery_l400_agentic_da_dataset}.gemini_embedding_2`
  REMOTE WITH CONNECTION `${project_id}.us.vertex-ai`
  OPTIONS (endpoint = 'gemini-embedding-2');


------------------------------------------------------------------------------------------------------------
-- Load all data
------------------------------------------------------------------------------------------------------------
/*
LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.campaign` 
CLUSTER BY campaign_id 
FROM FILES ( format = 'AVRO', enable_logical_types = true, uris = ['gs://data-analytics-golden-demo/l400-agentic-da/v1/Data-Export/campaign/campaign_*.avro']);
*/
-- ==============================================================================
-- 1. FINANCE & ACCOUNTING (General Ledger)
-- ==============================================================================
LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.GL_ACCT_MSTR`
(
    ACCT_ID_X STRING,         -- e.g., 'GL00100'
    ACCT_NM_STR STRING,       -- e.g., 'Gross Revenue - Retail'
    BAL_SHT_FLG INT64,        -- 1 = Balance Sheet, 0 = Income Statement
    ACT_INACT_IND STRING      -- 'A' or 'I'
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/GL_ACCT_MSTR.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.GL_F_TRX_00`
(
    TRX_ID_N INT64,
    ACCT_ID_X STRING,
    POST_DT_SK INT64,         -- e.g., 20241031 (Date Dimension Key)
    DR_CR_IND STRING,         -- 'D' (Debit) or 'C' (Credit)
    AMT_BASE NUMERIC,         -- Transaction amount
    SRC_SYS_CDE STRING        -- 'SLS', 'INV', 'HR'
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/GL_F_TRX_00.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.FIN_OPEX_DTL`
(
    EXP_ID STRING,
    DEPT_CD STRING,           -- 'MKTG', 'SALES', 'IT'
    SPND_TYP_IND INT64,       -- 10 = Digital Ad, 20 = Print, 30 = Event
    AMT NUMERIC,
    POST_DT DATE
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/FIN_OPEX_DTL.csv']);

-- ==============================================================================
-- 2. SYSTEM DATE DIMENSION (Classic Legacy ERP Feature)
-- ==============================================================================

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.SYS_CAL_DIM`
(
    DT_SK INT64,              -- 20241031
    CAL_DT DATE,              -- 2024-10-31
    FISC_YR_N INT64,          -- 2025
    FISC_QTR_N INT64,         -- 3
    FISC_PER_N INT64          -- 9 (Month of Fiscal Year)
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/SYS_CAL_DIM.csv']);

-- ==============================================================================
-- 3. SALES & ORDERS (The "Maze")
-- ==============================================================================

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.SLS_ORD_HDR`
(
    ORD_NO_SYS STRING,
    CUST_NUM_ID STRING,       -- Null if wholesale
    DIST_ACCT_ID STRING,      -- Null if D2C
    ORD_DT_SID INT64,         -- Date Key
    CHN_FLG INT64,            -- 1 = D2C, 2 = Wholesale
    STS_CDE STRING            -- 'O' (Open), 'C' (Closed/Fulfilled), 'V' (Void)
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/SLS_ORD_HDR.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.SLS_ORD_DTL_LN`
(
    ORD_NO_SYS STRING,
    LN_NO_N INT64,
    PRD_SKU_CD STRING,
    QTY_N INT64,
    UNIT_PRC_AMT NUMERIC,
    DISC_PCT_N FLOAT64        -- e.g., 0.15 for 15% discount
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/SLS_ORD_DTL_LN.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.SLS_RTN_LOGS_V2`
(
    RTN_AUTH_ID STRING,
    ORD_NO_SYS STRING,
    PRD_SKU_CD STRING,
    RTN_DT DATE,
    RSN_CDE_N INT64,          -- 1=Defective, 2=Wrong Size, 3=Changed Mind
    RFN_AMT NUMERIC
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/SLS_RTN_LOGS_V2.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.B2B_INV_AGING`
(
    INV_NUM_X STRING,
    DIST_ACCT_ID STRING,
    ISSUE_DT DATE,
    PAID_DT DATE,             -- Null if unpaid
    AMT_DUE NUMERIC,
    STS_FLG INT64             -- 0 = Open, 1 = Paid, 9 = Default/Collections
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/B2B_INV_AGING.csv']);

-- ==============================================================================
-- 4. CUSTOMERS & CHANNELS
-- ==============================================================================

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.CUST_MSTR_D2C`
(
    CUST_NUM_ID STRING,
    F_NM STRING,              -- PII
    L_NM STRING,              -- PII
    EML_ADDR_TXT STRING,      -- PII: Target for BigQuery Policy Tags
    PHONE_NUM_V STRING,       -- PII
    ACQ_DT DATE,
    OPT_IN_FLG INT64          -- 1 = Yes, 0 = No
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/CUST_MSTR_D2C.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.DIST_ACCT_MSTR`
(
    DIST_ACCT_ID STRING,
    CO_NM_TXT STRING,
    REG_ID_CD STRING,
    ONBRD_DT DATE
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/DIST_ACCT_MSTR.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.GEO_REG_HIER`
(
    REG_ID_CD STRING,         -- e.g., 'R_01'
    CTRY_CD STRING,           -- 'US', 'UK', 'DE'
    RGN_NM_TXT STRING,        -- 'NorthAm', 'EMEA', 'APAC'
    SUB_RGN_TXT STRING        -- 'West Coast', 'Nordics'
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/GEO_REG_HIER.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.CUST_FEEDBACK_FCT`
(
    FDBK_ID_X STRING,
    CUST_NO_X STRING,         -- Intentionally named differently than CUST_NUM_ID
    PRD_SKU_CD STRING,
    SUB_DT DATE,
    RTG_N INT64,              -- 1 to 5 stars
    VLD_FLG STRING            -- 'Y' (Verified Purchase) or 'N'
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/CUST_FEEDBACK_FCT.csv']);

-- ==============================================================================
-- 5. PRODUCTS & SUPPLY CHAIN
-- ==============================================================================

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.PRD_MSTR_CAT`
(
    PRD_SKU_CD STRING,
    PRD_NM_TXT STRING,
    CAT_CDE_N INT64,          -- Intentionally normalized to force JOINs
    SUB_CAT_CDE_N INT64,
    LCH_DT DATE
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/PRD_MSTR_CAT.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.PRD_CAT_DEF`
(
    CAT_CDE_N INT64,          -- e.g., 100, 200, 300
    CAT_DESC_TXT STRING       -- e.g., 'Bikes', 'Outerwear', 'Kayaks'
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/PRD_CAT_DEF.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.PRD_COGS_FCT`
(
    PRD_SKU_CD STRING,
    EFF_DT DATE,
    END_DT DATE,
    MTL_CST_AMT NUMERIC,      -- Raw material cost (e.g., Aluminum)
    LBR_CST_AMT NUMERIC,      -- Labor cost
    TRFF_AMT NUMERIC          -- Tariffs
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/PRD_COGS_FCT.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.INV_WHSE_FCT`
(
    WHSE_LOC_CD STRING,
    PRD_SKU_CD STRING,
    SNAP_DT DATE,             -- Weekly snapshot of inventory
    QTY_ON_HND_N INT64
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/INV_WHSE_FCT.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.VNDR_SPLY_MSTR`
(
    VNDR_ID_C STRING,
    VNDR_NM STRING,
    MTL_TYP_CD STRING         -- 'ALUM', 'CRBN', 'NYLN'
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/VNDR_SPLY_MSTR.csv']);

-- ==============================================================================
-- 6. HR & OPERATIONS
-- ==============================================================================

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.HR_EMP_MSTR`
(
    EMP_ID_N INT64,
    EMP_NM STRING,
    DEPT_CD STRING,
    HIRE_DT DATE
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/HR_EMP_MSTR.csv']);

LOAD DATA OVERWRITE `${project_id}.${bigquery_l400_agentic_da_dataset}.SLS_REP_QUOTA`
(
    EMP_ID_N INT64,
    REG_ID_CD STRING,
    QTR_TXT STRING,           -- e.g., '2024-Q1'
    QTA_AMT NUMERIC
)
FROM FILES (format = 'CSV', skip_leading_rows = 1, uris = ['gs://data-analytics-golden-demo/l400_agentic_da/SLS_REP_QUOTA.csv']);

------------------------------------------------------------------------------------------------------------
-- Create Views
------------------------------------------------------------------------------------------------------------
/*
CREATE OR REPLACE VIEW `${project_id}.${bigquery_l400_agentic_da_dataset}.insights`(
          store_name OPTIONS (DESCRIPTION='Name of the Store'),
          store_address OPTIONS (DESCRIPTION='The address of the store'),
 ...
    SELECT store_name,
          store_address,
          store_latitude,
          store_longitude,
          customer_name,
 ...          
  FROM `${project_id}.${bigquery_l400_agentic_da_dataset}.store` store
       INNER JOIN `${project_id}.${bigquery_l400_agentic_da_dataset}.order` orders
               ON store.store_id = orders.store_id
       INNER JOIN `${project_id}.${bigquery_l400_agentic_da_dataset}.order_item` order_item
               ON order_item.order_id=orders.order_id
       INNER JOIN `${project_id}.${bigquery_l400_agentic_da_dataset}.menu` menu
               ON menu.menu_id=order_item.menu_id
       INNER JOIN `${project_id}.${bigquery_l400_agentic_da_dataset}.customer` customer
               ON customer.customer_id=orders.customer_id;
*/

-- You cannot end Terraform on a comment, so this just prevents the error.
SELECT 1;