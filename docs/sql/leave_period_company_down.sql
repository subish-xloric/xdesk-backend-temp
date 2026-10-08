-- Reverts leave_period_company_up.sql: EM references back to the original
-- (copied_from_id) period, copies removed, columns dropped, AUTO_INCREMENT removed.
-- Periods created per company afterwards (copied_from_id IS NULL, company_id <> 4)
-- are deleted too; references to them are NOT remapped - check first:
--   SELECT * FROM leave_period WHERE copied_from_id IS NULL AND company_id <> 4;

START TRANSACTION;

UPDATE leave_quota t JOIN leave_period lp ON lp.leave_period_id = t.leave_period_id AND lp.copied_from_id IS NOT NULL
    SET t.leave_period_id = lp.copied_from_id;
UPDATE leave_requests t JOIN leave_period lp ON lp.leave_period_id = t.leave_period_id AND lp.copied_from_id IS NOT NULL
    SET t.leave_period_id = lp.copied_from_id;
UPDATE leaves t JOIN leave_period lp ON lp.leave_period_id = t.leave_period_id AND lp.copied_from_id IS NOT NULL
    SET t.leave_period_id = lp.copied_from_id;
UPDATE compensatory_leave_request t JOIN leave_period lp ON lp.leave_period_id = t.leave_period_id AND lp.copied_from_id IS NOT NULL
    SET t.leave_period_id = lp.copied_from_id;

DELETE FROM leave_period WHERE company_id <> 4;

COMMIT;

ALTER TABLE leave_period
    DROP INDEX idx_leave_period_company_dates,
    DROP COLUMN copied_from_id,
    DROP COLUMN company_id,
    MODIFY leave_period_id INT NOT NULL;
