-- Leave periods become per company: leave_period gets company_id, and
-- leave_period_id becomes AUTO_INCREMENT so periods can be created per company.
--
-- Existing (global) periods become Digital Mesh's (platform company 4); EM Soft (5)
-- gets a copy of each, and EM employees' references (leave_quota, leave_requests,
-- leaves, compensatory_leave_request) are remapped to the copy. copied_from_id
-- records the source row - leave_period_company_down.sql relies on it.
-- Run after legacy_company_ids_to_platform.sql. DDL auto-commits in MySQL.

-- ---------------------------------------------------------------- schema
ALTER TABLE leave_period
    MODIFY leave_period_id INT NOT NULL AUTO_INCREMENT,
    ADD COLUMN company_id INT NULL,
    ADD COLUMN copied_from_id INT NULL,
    ADD INDEX idx_leave_period_company_dates (company_id, leave_period_start_date, leave_period_end_date);

-- ------------------------------------------------------------------ data
START TRANSACTION;

UPDATE leave_period SET company_id = 4 WHERE company_id IS NULL;

INSERT INTO leave_period (leave_period_start_date, leave_period_end_date, company_id, copied_from_id)
    SELECT leave_period_start_date, leave_period_end_date, 5, leave_period_id FROM leave_period WHERE company_id = 4;

UPDATE leave_quota t JOIN user_profile up ON up.user_id = t.employee_id
    JOIN leave_period lp ON lp.copied_from_id = t.leave_period_id AND lp.company_id = 5
    SET t.leave_period_id = lp.leave_period_id WHERE up.company_id = 5;
UPDATE leave_requests t JOIN user_profile up ON up.user_id = t.employee_id
    JOIN leave_period lp ON lp.copied_from_id = t.leave_period_id AND lp.company_id = 5
    SET t.leave_period_id = lp.leave_period_id WHERE up.company_id = 5;
UPDATE leaves t JOIN user_profile up ON up.user_id = t.employee_id
    JOIN leave_period lp ON lp.copied_from_id = t.leave_period_id AND lp.company_id = 5
    SET t.leave_period_id = lp.leave_period_id WHERE up.company_id = 5;
UPDATE compensatory_leave_request t JOIN user_profile up ON up.user_id = t.employee_id
    JOIN leave_period lp ON lp.copied_from_id = t.leave_period_id AND lp.company_id = 5
    SET t.leave_period_id = lp.leave_period_id WHERE up.company_id = 5;

COMMIT;
