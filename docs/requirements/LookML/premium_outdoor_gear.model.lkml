connection: "l400_agentic_da_bq"

include: "/views/*.view.lkml"

explore: sls_ord_hdr {
  label: "Enterprise Sales & Operations"
  description: "Core explore for querying revenue, margins, and sales across D2C and Wholesale channels."

  join: sls_ord_dtl_ln {
    type: left_outer
    sql_on: ${sls_ord_hdr.ord_no_sys} = ${sls_ord_dtl_ln.ord_no_sys} ;;
    relationship: one_to_many
  }

  join: sys_cal_dim {
    type: left_outer
    sql_on: ${sls_ord_hdr.ord_dt_sid} = ${sys_cal_dim.dt_sk} ;;
    relationship: many_to_one
  }

  join: prd_mstr_cat {
    type: left_outer
    sql_on: ${sls_ord_dtl_ln.prd_sku_cd} = ${prd_mstr_cat.prd_sku_cd} ;;
    relationship: many_to_one
  }

  join: dist_acct_mstr {
    type: left_outer
    sql_on: ${sls_ord_hdr.dist_acct_id} = ${dist_acct_mstr.dist_acct_id} ;;
    relationship: many_to_one
  }

  # --- TYPE 2 METRIC OVERRIDE: THE STRING CONCAT JOIN ---
  join: b2b_inv_aging {
    type: left_outer
    sql_on: CONCAT('INV-', ${sls_ord_hdr.ord_no_sys}) = ${b2b_inv_aging.inv_num_x} ;;
    relationship: one_to_one
  }

  # --- TYPE 2 METRIC OVERRIDE: THE SCD DATE BOUNDARY JOIN ---
  join: prd_cogs_fct {
    type: left_outer
    sql_on: ${prd_mstr_cat.prd_sku_cd} = ${prd_cogs_fct.prd_sku_cd}
        AND ${sys_cal_dim.cal_dt} >= ${prd_cogs_fct.eff_dt}
        AND ${sys_cal_dim.cal_dt} <= ${prd_cogs_fct.end_dt} ;;
    relationship: many_to_one
  }

  # Join to Derived Table for Complex Distributor Status
  join: dt_tier_1_distributors {
    type: left_outer
    sql_on: ${dist_acct_mstr.dist_acct_id} = ${dt_tier_1_distributors.dist_acct_id} ;;
    relationship: one_to_one
  }
}