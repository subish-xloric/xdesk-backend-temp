-- Reverts company_lookups_up.sql: points every reference back at the original
-- (copied_from_id) row, removes rows created per company, and drops the new
-- columns and the employment_status table.
-- Rows a company added later through the admin APIs (copied_from_id IS NULL and
-- company_id <> 4) are deleted; references to them are NOT remapped - check first:
--   SELECT company_id, COUNT(*) FROM job_title WHERE copied_from_id IS NULL AND company_id <> 4 GROUP BY company_id;
-- (same for project_activity, leave_type, employment_status).

START TRANSACTION;

UPDATE user_profile up JOIN job_title jt ON jt.id = up.job_title AND jt.copied_from_id IS NOT NULL
    SET up.job_title = jt.copied_from_id;
UPDATE user_profile up JOIN employment_status es ON es.id = up.job_status AND es.copied_from_id IS NOT NULL
    SET up.job_status = es.copied_from_id;
UPDATE user_profile_provisional pp JOIN job_title jt ON jt.id = pp.value AND jt.copied_from_id IS NOT NULL
    SET pp.value = jt.copied_from_id WHERE pp.field = 'job_title';
UPDATE user_profile_provisional pp JOIN employment_status es ON es.id = pp.value AND es.copied_from_id IS NOT NULL
    SET pp.value = es.copied_from_id WHERE pp.field = 'job_status';

UPDATE leave_quota t JOIN leave_type lt ON lt.leave_type_id = t.leave_type_id AND lt.copied_from_id IS NOT NULL
    SET t.leave_type_id = lt.copied_from_id;
UPDATE leave_requests t JOIN leave_type lt ON lt.leave_type_id = t.type_id AND lt.copied_from_id IS NOT NULL
    SET t.type_id = lt.copied_from_id;
UPDATE leaves t JOIN leave_type lt ON lt.leave_type_id = t.type_id AND lt.copied_from_id IS NOT NULL
    SET t.type_id = lt.copied_from_id;
UPDATE compensatory_leave_request t JOIN leave_type lt ON lt.leave_type_id = t.leave_type_id AND lt.copied_from_id IS NOT NULL
    SET t.leave_type_id = lt.copied_from_id;

UPDATE timesheet_item t JOIN project_activity pa ON pa.activity_id = t.activity_id AND pa.copied_from_id IS NOT NULL
    SET t.activity_id = pa.copied_from_id;
UPDATE timesheet_item_archive t JOIN project_activity pa ON pa.activity_id = t.activity_id AND pa.copied_from_id IS NOT NULL
    SET t.activity_id = pa.copied_from_id;

DELETE FROM job_title        WHERE company_id <> 4;
DELETE FROM project_activity WHERE company_id <> 4;
DELETE FROM leave_type       WHERE company_id <> 4;

COMMIT;

DROP TABLE employment_status;
ALTER TABLE user_profile MODIFY job_status TINYINT NULL;
ALTER TABLE leave_type
    DROP INDEX uq_leave_type_company_code,
    DROP INDEX idx_leave_type_company,
    DROP COLUMN copied_from_id,
    DROP COLUMN code,
    DROP COLUMN company_id;
ALTER TABLE project_activity
    DROP INDEX idx_project_activity_company,
    DROP COLUMN copied_from_id,
    DROP COLUMN company_id;
ALTER TABLE job_title
    DROP INDEX idx_job_title_company,
    DROP COLUMN copied_from_id,
    DROP COLUMN company_id;
