Here is the finalized set of 20 prompts. 

I have specifically designed these to act as the ultimate "Test Suite" for the lab. Every single artifact we just created—the Dataplex history, the Tableau/SSRS logic, the legacy SQL, the qualitative PDF, the security policy, and the glossaries—is explicitly targeted by these questions. 

If the CE misses a step in the lab, the corresponding question below will definitively fail.

### Category 1: Baseline Metadata & Semantic Glossaries
*Goal: Tests if the CE successfully mapped the basic schema and pushed the two PDF Glossaries (Industry & Finance) into Dataplex. The LLM must use the glossary to understand the acronyms.*
1. **"What was our total Net Revenue for Fiscal Year 2025?"** *(Tests Glossary: 'Net Revenue' vs 'Gross Revenue', and 'Fiscal Year' boundaries).*
2. **"Show me the On-Hand Inventory for the Pro Mountain Bike across all warehouses."** *(Tests Glossary: 'On-Hand Inventory', and basic JOINs to the warehouse fact table).*
3. **"What is our current Defect Rate for Kayaks?"** *(Tests Industry Glossary: 'Defect Rate' meaning Return Code = 1).*
4. **"Calculate the AOV for the D2C channel last quarter."** *(Tests Finance Glossary: 'AOV' [Average Order Value], and Industry Glossary: 'D2C' [Channel 1]).*

### Category 2: Ambiguity & Clarification Triggers
*Goal: Tests if the CE authored proper Agent Instructions (System Prompts). The agent must pause and ask for clarification instead of hallucinating an answer.*
5. **"What was our profit last month?"** *(Agent must ask: "Are you asking for Gross Margin, EBIDA, or Net Profit? And for the D2C or Wholesale channel?")*
6. **"Show me our pipeline."** *(Agent must ask: "Are you referring to the Wholesale Sales Pipeline or the Marketing Acquisition Pipeline? And for which Region?")*
7. **"Who are our best distributors?"** *(Agent must ask: "How would you like to define 'best'? By highest Gross Revenue, lowest DSO, or Tier 1 status?")*
8. **"What are our total expenses?"** *(Agent must ask: "Are you asking for OPEX (Operating Expenses) or COGS (Cost of Goods Sold)?")*

### Category 3: Tableau & Legacy SQL (Type 1 Metric Definitions)
*Goal: Tests if the CE successfully extracted the complex formulas from the `.twb` (Tableau) and `.sql` (Oracle/FP&A) files and configured them as Type 1 Verified Queries.*
9. **"How many Tier 1 Distributors do we currently have in EMEA?"** *(Tests Tableau Extraction 1: Volume > 250k AND >=3 categories AND Avg Days to Pay < 30).*
10. **"List the top 10 Certified Field Testers by Total Lifetime Value (CLV)."** *(Tests Tableau Extraction 2: Spend > 1000 AND >=3 categories AND Reviews >= 2 AND Returns == 0. Also tests 'CLV' glossary term).*
11. **"What was our Blended D2C Customer Acquisition Cost (CAC) in Q1 of 2025?"** *(Tests Legacy SQL Extraction 1: MKTG OPEX / Net New D2C Customers).*
12. **"Show me the Inventory Turn Ratio for Fiscal Year 2025."** *(Tests Legacy SQL Extraction 2: Total COGS / Average Inventory Value).*

### Category 4: SSRS Extractions & "The Maze" (Type 2 Analytical Examples)
*Goal: Tests if the CE successfully extracted the complex JOIN logic from the `.rdl` (SSRS) files. If they rely purely on the Dataplex LLM graph, these will fail due to string manipulation and inequality bounds.*
13. **"Show me the total Amount Due for Aging Invoices broken down by Region."** *(Tests SSRS Extraction 1: Demands the `CONCAT('INV-', hdr.ORD_NO_SYS) = inv.INV_NUM_X` string join).*
14. **"What was our True Gross Margin for Tents in Q3 of 2025?"** *(Tests SSRS Extraction 2: Demands the Slowly Changing Dimension logic `CAL_DT >= EFF_DT AND CAL_DT <= END_DT`).*
15. **"Compare the DSO of Tier 1 Distributors versus regular Wholesale Distributors."** *(The ultimate combo: Combines Tableau 1 + SSRS 1 + Finance Glossary 'DSO').*
16. **"Which Product Category had the highest Net-New ARR last year?"** *(Tests the complex SaaS metric 'Net-New ARR' from the Finance Glossary against the core sales maze).*

### Category 5: Qualitative Data (Director's Memo Integration)
*Goal: Tests if the CE successfully used BQ ML to parse the Director's PDF into `dim_business_events` and instructed CA to join it when asked for explanations.*
17. **"Why did Wholesale revenue for Mountain Bikes spike so drastically in April 2025?"** *(Agent must append qualitative context: "Revenue spiked due to a major competitor's safety recall, causing distributors to urgently restock.")*
18. **"Explain the dip in our Gross Margin during Q3 of Calendar Year 2025 despite steady Net Revenue."** *(Agent must append qualitative context: "Gross Margin dipped due to a global supply chain disruption that skyrocketed the cost of raw aluminum.")*

### Category 6: Security & Governance (Privacy Policy Integration)
*Goal: Tests Gemini Enterprise pass-through authentication and the CE's ability to apply BigQuery Policy Tags and Row-Level Security based on the Privacy PDF.*
19. **"List the full names, email addresses, and phone numbers of our top 50 D2C customers."** *(Agent returns the list, but `EML_ADDR_TXT` and `PHONE_NUM_V` are perfectly masked as per the policy).*
20. **"Show me a detailed breakdown of Wholesale Net Revenue by Distributor for the APAC region."** *(If the automated test runs this as a 'NorthAm' credentialed user, RLS completely blocks the results).*

***

### Ready to transition to the Lab Guide/Evalset?
These 20 prompts wrap a perfect bow around the entire data generation and artifact phase. We have built an airtight, highly realistic enterprise scenario. 

Would you like to move on to generating the **Automated Evalset JSON** format, or would you like to start outlining the **Step-by-Step Lab Guide** that the students will actually read?