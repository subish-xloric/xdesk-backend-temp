-- Reverts wfh_requests_company_up.sql.
ALTER TABLE wfh_requests
    DROP INDEX idx_wfh_requests_company_emp,
    DROP COLUMN company_id;
