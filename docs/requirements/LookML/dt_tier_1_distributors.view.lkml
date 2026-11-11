view: dt_tier_1_distributors {
  derived_table: {
    sql: 
      SELECT 
          dist.DIST_ACCT_ID,
          TRUE as is_tier_1
      FROM `l400_agentic_da.DIST_ACCT_MSTR` dist
      JOIN `l400_agentic_da.SLS_ORD_HDR` hdr ON dist.DIST_ACCT_ID = hdr.DIST_ACCT_ID
      JOIN `l400_agentic_da.SLS_ORD_DTL_LN` ln ON hdr.ORD_NO_SYS = ln.ORD_NO_SYS
      JOIN `l400_agentic_da.PRD_MSTR_CAT` prd ON ln.PRD_SKU_CD = prd.PRD_SKU_CD
      LEFT JOIN `l400_agentic_da.B2B_INV_AGING` inv ON CONCAT('INV-', hdr.ORD_NO_SYS) = inv.INV_NUM_X
      GROUP BY dist.DIST_ACCT_ID
      HAVING SUM(ln.QTY_N * ln.UNIT_PRC_AMT * (1 - ln.DISC_PCT_N)) > 250000 
         AND COUNT(DISTINCT prd.CAT_CDE_N) >= 3 
         AND AVG(DATE_DIFF(COALESCE(inv.PAID_DT, CURRENT_DATE()), inv.ISSUE_DT, DAY)) < 30
      ;;
  }

  dimension: dist_acct_id {
    type: string
    primary_key: yes
    hidden: yes
    sql: ${TABLE}.DIST_ACCT_ID ;;
  }

  dimension: is_tier_1_distributor {
    type: yesno
    sql: COALESCE(${TABLE}.is_tier_1, FALSE) ;;
    description: "A wholesale partner with over $250k in volume, buying 3+ categories, paying in < 30 days."
  }
}