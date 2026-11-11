import pandas as pd
import numpy as np
from faker import Faker
import datetime
import random
import os
import time

fake = Faker()
Faker.seed(42)
np.random.seed(42)

# Configuration
START_DATE = datetime.date(2024, 7, 1)
END_DATE = datetime.date(2026, 6, 30)
NUM_DAYS = (END_DATE - START_DATE).days + 1
OUTPUT_DIR = "mock_erp_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Starting Mock ERP Data Generation (BigQuery Scale)...")
start_time = time.time()

# =====================================================================
# 2. SYSTEM DATE DIMENSION
# =====================================================================
date_list = [START_DATE + datetime.timedelta(days=x) for x in range(NUM_DAYS)]
sys_cal_dim = pd.DataFrame({
    'DT_SK': [int(d.strftime('%Y%m%d')) for d in date_list],
    'CAL_DT': date_list,
    'FISC_YR_N': [d.year for d in date_list],
    'FISC_QTR_N': [((d.month - 1) // 3) + 1 for d in date_list],
    'FISC_PER_N': [d.month for d in date_list]
})
sys_cal_dim.to_csv(f"{OUTPUT_DIR}/SYS_CAL_DIM.csv", index=False)

# =====================================================================
# 4. CHANNELS, GEOGRAPHY & CUSTOMERS
# =====================================================================
geo_reg_hier = pd.DataFrame({
    'REG_ID_CD': ['R_01', 'R_02', 'R_03', 'R_04'],
    'CTRY_CD': ['US', 'UK', 'DE', 'AU'],
    'RGN_NM_TXT': ['NorthAm', 'EMEA', 'EMEA', 'APAC'],
    'SUB_RGN_TXT': ['West Coast', 'Nordics', 'Central', 'Oceania']
})
geo_reg_hier.to_csv(f"{OUTPUT_DIR}/GEO_REG_HIER.csv", index=False)

# Wholesale Distributors (200)
dist_acct_mstr = pd.DataFrame({
    'DIST_ACCT_ID': [f"DIST-{str(i).zfill(3)}" for i in range(1, 201)],
    'CO_NM_TXT': [fake.company() for _ in range(200)],
    'REG_ID_CD': np.random.choice(['R_01', 'R_02', 'R_03', 'R_04'], 200),
    'ONBRD_DT': [fake.date_between(start_date='-5y', end_date='-2y') for _ in range(200)]
})
dist_acct_mstr.to_csv(f"{OUTPUT_DIR}/DIST_ACCT_MSTR.csv", index=False)

# D2C Customers (50,000 for Scale)
print("Generating 50,000 Customers...")
cust_mstr_d2c = pd.DataFrame({
    'CUST_NUM_ID': [f"CUST-{str(i).zfill(5)}" for i in range(1, 50001)],
    'F_NM': [fake.first_name() for _ in range(50000)],
    'L_NM': [fake.last_name() for _ in range(50000)],
    'EML_ADDR_TXT': [f"user{i}@{fake.domain_name()}" for i in range(50000)], # Faster than fake.email() in loop
    'PHONE_NUM_V': [fake.phone_number() for _ in range(50000)],
    'ACQ_DT': [fake.date_between(start_date='-3y', end_date='today') for _ in range(50000)],
    'OPT_IN_FLG': np.random.choice([0, 1], 50000, p=[0.2, 0.8])
})
cust_mstr_d2c.to_csv(f"{OUTPUT_DIR}/CUST_MSTR_D2C.csv", index=False)

# =====================================================================
# 5. PRODUCTS & SUPPLY CHAIN
# =====================================================================
prd_cat_def = pd.DataFrame({
    'CAT_CDE_N': [100, 200, 300, 400],
    'CAT_DESC_TXT': ['Bikes', 'Outerwear', 'Kayaks', 'Tents']
})
prd_cat_def.to_csv(f"{OUTPUT_DIR}/PRD_CAT_DEF.csv", index=False)

products = [
    ('SKU-101', 'Pro Mountain Bike', 100, 101, 2500, 1200),
    ('SKU-102', 'Carbon Road Bike', 100, 102, 3200, 1500),
    ('SKU-103', 'E-Bike XL', 100, 103, 4000, 2000),
    ('SKU-201', 'Winter Parka Pro', 200, 201, 450, 150),
    ('SKU-202', 'Thermal Gloves', 200, 202, 85, 25),
    ('SKU-203', 'Snow Pants', 200, 203, 200, 70),
    ('SKU-301', 'Tandem Kayak', 300, 301, 850, 400),
    ('SKU-302', 'River Kayak Single', 300, 302, 600, 250),
    ('SKU-401', '4-Person Dome Tent', 400, 401, 350, 120),
    ('SKU-402', 'Ultralight Backpacking Tent', 400, 402, 450, 180)
]

while len(products) < 25:
    cat = random.choice([100, 200, 300, 400])
    pid = len(products) + 1
    products.append((f'SKU-{cat + pid}', f'Gear Item {pid}', cat, cat+1, random.randint(50, 500), random.randint(20, 200)))

prd_mstr_cat = pd.DataFrame(products, columns=['PRD_SKU_CD', 'PRD_NM_TXT', 'CAT_CDE_N', 'SUB_CAT_CDE_N', 'PRICE', 'BASE_COGS'])
prd_mstr_cat.assign(
    LCH_DT=START_DATE - datetime.timedelta(days=365)
)[['PRD_SKU_CD', 'PRD_NM_TXT', 'CAT_CDE_N', 'SUB_CAT_CDE_N', 'LCH_DT']].to_csv(f"{OUTPUT_DIR}/PRD_MSTR_CAT.csv", index=False)

cogs_data = []
for _, row in prd_mstr_cat.iterrows():
    cogs_data.append([row['PRD_SKU_CD'], START_DATE, datetime.date(2025, 6, 30), round(row['BASE_COGS'] * 0.6, 2), round(row['BASE_COGS'] * 0.3, 2), round(row['BASE_COGS'] * 0.1, 2)])
    spike_mult = 2.5 if row['CAT_CDE_N'] in [100, 400] else 1.0
    cogs_data.append([row['PRD_SKU_CD'], datetime.date(2025, 7, 1), datetime.date(2025, 9, 30), round((row['BASE_COGS'] * 0.6) * spike_mult, 2), round(row['BASE_COGS'] * 0.3, 2), round(row['BASE_COGS'] * 0.1, 2)])
    cogs_data.append([row['PRD_SKU_CD'], datetime.date(2025, 10, 1), END_DATE, round(row['BASE_COGS'] * 0.65, 2), round(row['BASE_COGS'] * 0.3, 2), round(row['BASE_COGS'] * 0.1, 2)])
pd.DataFrame(cogs_data, columns=['PRD_SKU_CD', 'EFF_DT', 'END_DT', 'MTL_CST_AMT', 'LBR_CST_AMT', 'TRFF_AMT']).to_csv(f"{OUTPUT_DIR}/PRD_COGS_FCT.csv", index=False, float_format="%.2f")


# =====================================================================
# 3. SALES & ORDERS (The "Maze") - SCALED FOR BIGQUERY
# =====================================================================
headers, lines, returns, feedback, invoices = [], [], [], [], []
order_id_counter = 1000000

print("Generating ~850,000 Orders and ~2,000,000 Order Lines. This will take ~1-2 minutes...")
for d in date_list:
    is_winter = d.month in [11, 12, 1, 2]
    is_summer = d.month in [5, 6, 7, 8]
    is_bike_recall = (d.year == 2025 and d.month == 4)
    
    # Scale up daily volume significantly
    num_orders = random.randint(800, 1200) 
    if is_bike_recall: num_orders += 500
    if is_winter or is_summer: num_orders += 300
    
    if d.day == 1:
        print(f"  ...Processing {d.strftime('%b %Y')} data...")
        
    for _ in range(num_orders):
        is_d2c = random.random() > 0.3
        ord_no = f"ORD-{order_id_counter}"
        order_id_counter += 1
        
        # Hardcode Apex/Tier 1 Customers
        if is_d2c:
            cust_id = f"CUST-{str(random.randint(1, 15)).zfill(5)}" if random.random() < 0.05 else f"CUST-{str(random.randint(16, 50000)).zfill(5)}"
            dist_id = ""
            chn_flg = 1
        else:
            cust_id = ""
            dist_id = f"DIST-{str(random.randint(1, 10)).zfill(3)}" if random.random() < 0.10 else f"DIST-{str(random.randint(11, 200)).zfill(3)}"
            chn_flg = 2
            
        headers.append([ord_no, cust_id, dist_id, int(d.strftime('%Y%m%d')), chn_flg, 'C'])
        
        num_lines = random.randint(1, 5)
        order_total = 0
        
        for ln in range(num_lines):
            if is_bike_recall and not is_d2c and random.random() < 0.8:
                prod = prd_mstr_cat[prd_mstr_cat['CAT_CDE_N'] == 100].sample(1).iloc[0]
            elif is_winter and random.random() < 0.6:
                prod = prd_mstr_cat[prd_mstr_cat['CAT_CDE_N'] == 200].sample(1).iloc[0]
            elif is_summer and random.random() < 0.6:
                prod = prd_mstr_cat[prd_mstr_cat['CAT_CDE_N'] == 300].sample(1).iloc[0]
            else:
                prod = prd_mstr_cat.sample(1).iloc[0]
                
            qty = random.randint(1, 3) if is_d2c else random.randint(20, 100)
            price = prod['PRICE']
            disc = random.choice([0.0, 0.05, 0.10, 0.15])
            
            line_total = round(qty * price * (1 - disc), 2)
            lines.append([ord_no, ln+1, prod['PRD_SKU_CD'], qty, price, disc])
            order_total += line_total
            
            if is_d2c and random.random() < 0.05:
                rating = 5 if int(cust_id.split('-')[1]) <= 15 else random.randint(1, 5)
                feedback.append([f"FB-{ord_no}-{ln}", cust_id, prod['PRD_SKU_CD'], d + datetime.timedelta(days=7), rating, 'Y'])
                
            if is_d2c and random.random() < 0.02 and int(cust_id.split('-')[1]) > 15:
                returns.append([f"RTN-{ord_no}-{ln}", ord_no, prod['PRD_SKU_CD'], d + datetime.timedelta(days=14), random.randint(1,3), line_total])

        order_total = round(order_total, 2)
        if not is_d2c:
            days_to_pay = random.randint(5, 14) if int(dist_id.split('-')[1]) <= 10 else random.randint(15, 90)
            invoices.append([f"INV-{ord_no}", dist_id, d, d + datetime.timedelta(days=days_to_pay), order_total, 1])

pd.DataFrame(headers, columns=['ORD_NO_SYS', 'CUST_NUM_ID', 'DIST_ACCT_ID', 'ORD_DT_SID', 'CHN_FLG', 'STS_CDE']).to_csv(f"{OUTPUT_DIR}/SLS_ORD_HDR.csv", index=False)
pd.DataFrame(lines, columns=['ORD_NO_SYS', 'LN_NO_N', 'PRD_SKU_CD', 'QTY_N', 'UNIT_PRC_AMT', 'DISC_PCT_N']).to_csv(f"{OUTPUT_DIR}/SLS_ORD_DTL_LN.csv", index=False, float_format="%.2f")
pd.DataFrame(returns, columns=['RTN_AUTH_ID', 'ORD_NO_SYS', 'PRD_SKU_CD', 'RTN_DT', 'RSN_CDE_N', 'RFN_AMT']).to_csv(f"{OUTPUT_DIR}/SLS_RTN_LOGS_V2.csv", index=False, float_format="%.2f")
pd.DataFrame(feedback, columns=['FDBK_ID_X', 'CUST_NO_X', 'PRD_SKU_CD', 'SUB_DT', 'RTG_N', 'VLD_FLG']).to_csv(f"{OUTPUT_DIR}/CUST_FEEDBACK_FCT.csv", index=False)
pd.DataFrame(invoices, columns=['INV_NUM_X', 'DIST_ACCT_ID', 'ISSUE_DT', 'PAID_DT', 'AMT_DUE', 'STS_FLG']).to_csv(f"{OUTPUT_DIR}/B2B_INV_AGING.csv", index=False, float_format="%.2f")

# =====================================================================
# 6. HR & OPERATIONS
# =====================================================================
hr_emp_mstr = pd.DataFrame({
    'EMP_ID_N': range(1001, 1051),
    'EMP_NM': [fake.name() for _ in range(50)],
    'DEPT_CD': ['SALES'] * 50,
    'HIRE_DT': [fake.date_between(start_date='-4y', end_date='-1y') for _ in range(50)]
})
hr_emp_mstr.to_csv(f"{OUTPUT_DIR}/HR_EMP_MSTR.csv", index=False)

quotas = []
for emp_id in range(1001, 1051):
    reg = random.choice(['R_01', 'R_02', 'R_03', 'R_04'])
    for yr in [2024, 2025, 2026]:
        for qtr in [1, 2, 3, 4]:
            quotas.append([emp_id, reg, f"{yr}-Q{qtr}", random.randint(250000, 750000)])
pd.DataFrame(quotas, columns=['EMP_ID_N', 'REG_ID_CD', 'QTR_TXT', 'QTA_AMT']).to_csv(f"{OUTPUT_DIR}/SLS_REP_QUOTA.csv", index=False)

# =====================================================================
# 5. SUPPLY CHAIN & WAREHOUSE
# =====================================================================
vndr_sply_mstr = pd.DataFrame({
    'VNDR_ID_C': [f"VND-{i}" for i in range(1, 11)],
    'VNDR_NM': [fake.company() for _ in range(10)],
    'MTL_TYP_CD': np.random.choice(['ALUM', 'CRBN', 'NYLN', 'RBBR', 'STEL'], 10)
})
vndr_sply_mstr.to_csv(f"{OUTPUT_DIR}/VNDR_SPLY_MSTR.csv", index=False)

print("Generating 50 Warehouses of Weekly Inventory Data...")
inv_data = []
for d in date_list[::7]:  
    for wh_num in range(1, 51):
        for sku in prd_mstr_cat['PRD_SKU_CD']:
            inv_data.append([f"WH-{str(wh_num).zfill(2)}", sku, d, random.randint(10, 500)])
pd.DataFrame(inv_data, columns=['WHSE_LOC_CD', 'PRD_SKU_CD', 'SNAP_DT', 'QTY_ON_HND_N']).to_csv(f"{OUTPUT_DIR}/INV_WHSE_FCT.csv", index=False)

# =====================================================================
# 1. FINANCE & ACCOUNTING (General Ledger)
# =====================================================================
gl_acct_mstr = pd.DataFrame({
    'ACCT_ID_X': ['GL1000', 'GL2000', 'GL3000', 'Gl4000', 'GL5000', 'GL6000', 'GL7000'],
    'ACCT_NM_STR': ['Gross Revenue', 'Wholesale Revenue', 'COGS', 'Marketing Expense', 'Payroll', 'Rent', 'Cash'],
    'BAL_SHT_FLG': [0, 0, 0, 0, 0, 0, 1],
    'ACT_INACT_IND': ['A'] * 7
})
gl_acct_mstr.to_csv(f"{OUTPUT_DIR}/GL_ACCT_MSTR.csv", index=False)

opex_data = []
for d in date_list:
    if d.day in [14, 28]: 
        for dep in ['MKTG', 'SALES', 'IT', 'HR']:
            opex_data.append([f"EXP-{d.strftime('%Y%m%d')}-{dep}", dep, 10, random.randint(10000, 100000), d])
pd.DataFrame(opex_data, columns=['EXP_ID', 'DEPT_CD', 'SPND_TYP_IND', 'AMT', 'POST_DT']).to_csv(f"{OUTPUT_DIR}/FIN_OPEX_DTL.csv", index=False)

print("Generating ~1.5 Million General Ledger Fact Rows...")
gl_trx_data = []
trx_id = 1
for d in date_list:
    dt_sk = int(d.strftime('%Y%m%d'))
    # Log 2000 distinct GL entries per day to simulate high-volume transaction system
    for _ in range(2000):
        acct = random.choice(['GL1000', 'GL2000', 'GL3000', 'Gl4000', 'GL5000', 'GL6000', 'GL7000'])
        dr_cr = 'D' if acct in ['GL3000', 'Gl4000', 'GL5000', 'GL6000'] else 'C'
        sys = random.choice(['SLS', 'INV', 'HR', 'SYS'])
        gl_trx_data.append([trx_id, acct, dt_sk, dr_cr, round(random.uniform(500.0, 15000.0), 2), sys])
        trx_id += 1
        
pd.DataFrame(gl_trx_data, columns=['TRX_ID_N', 'ACCT_ID_X', 'POST_DT_SK', 'DR_CR_IND', 'AMT_BASE', 'SRC_SYS_CDE']).to_csv(f"{OUTPUT_DIR}/GL_F_TRX_00.csv", index=False, float_format="%.2f")

end_time = time.time()
print(f"\nSUCCESS! 19 Files saved to /{OUTPUT_DIR}")
print(f"Data Generation took {round(end_time - start_time, 2)} seconds.")