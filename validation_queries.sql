-- Run with:  sqlite3 output/customers.db < validation_queries.sql
-- 1. Reconciliation: raw rows = duplicates removed + rejected + loaded
SELECT raw_rows, duplicates_removed, rejected_rows, loaded_rows,
       raw_rows - duplicates_removed - rejected_rows AS expected_loaded,
       CASE WHEN raw_rows - duplicates_removed - rejected_rows = loaded_rows THEN 'PASS' ELSE 'FAIL' END AS reconciliation
FROM etl_run_log;

-- 2. No duplicate customer IDs in the clean table (should return 0 rows)
SELECT customer_id, COUNT(*) AS n FROM clean_customers GROUP BY customer_id HAVING n > 1;

-- 3. No impossible values in the clean table (all counts should be 0)
SELECT
  SUM(loan_amount_ghs <= 0)                            AS non_positive_amounts,
  SUM(date_of_birth > '2008-10-20')                    AS under_18,
  SUM(loan_date > '2026-10-20')                        AS future_loan_dates,
  SUM(phone NOT LIKE '+233_________')                  AS bad_phones,
  SUM(credit_score < 300 OR credit_score > 850)        AS bad_scores
FROM clean_customers;

-- 4. Consistent categories (should show only 3 statuses and 7 regions)
SELECT status, COUNT(*) FROM clean_customers GROUP BY status;
SELECT region, COUNT(*) FROM clean_customers GROUP BY region;

-- 5. Data quality summary by region
SELECT region, COUNT(*) AS customers,
       ROUND(AVG(loan_amount_ghs),2) AS avg_loan_ghs,
       SUM(quality_flag <> '') AS flagged_records
FROM clean_customers GROUP BY region ORDER BY customers DESC;

-- 6. Why records were rejected
SELECT reject_reason, COUNT(*) AS n FROM rejected_records GROUP BY reject_reason ORDER BY n DESC LIMIT 10;
