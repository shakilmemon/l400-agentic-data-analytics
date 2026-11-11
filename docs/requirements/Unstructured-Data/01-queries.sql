CREATE OR REPLACE TABLE l400_agentic_da.dim_business_events AS 
SELECT
  CAST(Memo_Date AS DATE) AS Memo_Date, 
  Sender, 
  Event_Type, 
  CAST(Event_Start_Date AS DATE) AS Event_Start_Date, 
  CAST(Event_End_Date AS DATE) AS Event_End_Date, 
  Affected_Division, 
  Impacted_Products, 
  Event_Description, 
  Root_Cause, 
  Financial_Impact_Category,
  FPA_Guidance, 
  Expected_Duration,
  full_response,
  status,
  uri,
  prompt
FROM
  AI.GENERATE_TABLE(
    MODEL `l400_agentic_da.gemini_3_0_flash`, 
    (
      SELECT
        uri,
        STRUCT('Extract each field. Format Memo_Date, Event_Start_Date and Event_End_Date as YYYY-MM-DD. If an event covers a month or quarter, infer the exact start and end dates of that period.' AS prompt,
       [OBJ.GET_ACCESS_URL(ref, 'r')] AS object_ref_runtime
) AS prompt
      FROM `l400_agentic_da.unstructured_data`
    ),
    STRUCT(
      0.0 AS temperature, 
      5000 AS max_output_tokens,
      'Memo_Date STRING, Sender STRING, Event_Type STRING, Event_Start_Date STRING, Event_End_Date STRING, Affected_Division STRING, Impacted_Products STRING, Event_Description STRING, Root_Cause STRING, Financial_Impact_Category STRING, FPA_Guidance STRING, Expected_Duration STRING' AS output_schema
    )
  );