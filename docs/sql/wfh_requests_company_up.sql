-- wfh_requests gets company_id (the employee's platform company), backfilled from
-- user_profile. Run after legacy_company_ids_to_platform.sql.
ALTER TABLE wfh_requests
    ADD COLUMN company_id INT NULL,
    ADD INDEX idx_wfh_requests_company_emp (company_id, emp_id);

UPDATE wfh_requests w JOIN user_profile up ON up.user_id = w.emp_id
    SET w.company_id = up.company_id WHERE w.company_id IS NULL;
