view: sls_ord_dtl_ln {
  sql_table_name: `l400_agentic_da.SLS_ORD_DTL_LN` ;;

  dimension: ord_no_sys {
    type: string
    sql: ${TABLE}.ORD_NO_SYS ;;
    hidden: yes
  }

  dimension: qty_n {
    type: number
    sql: ${TABLE}.QTY_N ;;
  }

  dimension: unit_prc_amt {
    type: number
    sql: ${TABLE}.UNIT_PRC_AMT ;;
    description: "The base unit price of a product in USD, representing the MSRP or MAP."
  }

  dimension: disc_pct_n {
    type: number
    sql: ${TABLE}.DISC_PCT_N ;;
  }

  # --- FINANCIAL & REVENUE METRICS ---

  measure: gross_revenue {
    type: sum
    sql: ${qty_n} * ${unit_prc_amt} ;;
    value_format_name: usd
    description: "The total top-line sales amount before discounts or returns."
  }

  measure: net_revenue {
    type: sum
    sql: ${qty_n} * ${unit_prc_amt} * (1 - ${disc_pct_n}) ;;
    value_format_name: usd
    description: "Gross Revenue minus applied discounts and refunds."
  }

  measure: total_cogs {
    type: sum
    sql: ${qty_n} * (${prd_cogs_fct.mtl_cst_amt} + ${prd_cogs_fct.lbr_cst_amt} + ${prd_cogs_fct.trff_amt}) ;;
    value_format_name: usd
    description: "Direct production costs including Material, Labor, and Tariffs."
  }

  measure: gross_margin {
    type: number
    sql: ${net_revenue} - ${total_cogs} ;;
    value_format_name: usd
    description: "Net Revenue minus total COGS. The core profitability metric."
  }

  measure: average_order_value {
    type: number
    sql: ${net_revenue} / NULLIF(COUNT(DISTINCT ${ord_no_sys}), 0) ;;
    value_format_name: usd
    description: "Total Net Revenue divided by distinct order headers (AOV)."
  }
}