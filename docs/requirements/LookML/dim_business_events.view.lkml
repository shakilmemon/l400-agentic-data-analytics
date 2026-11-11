view: dim_business_events {
  sql_table_name: `l400_agentic_da.dim_business_events` ;;

  dimension: event_month {
    type: date_month
    sql: ${TABLE}.Event_Month ;;
  }

  dimension: affected_division {
    type: string
    sql: ${TABLE}.Affected_Division ;;
  }

  dimension: event_description {
    type: string
    sql: ${TABLE}.Event_Description ;;
    description: "Qualitative business context explaining market anomalies, supply chain shortages, or competitive intelligence."
  }
}