-- Company-scoped lookup tables: job_title, leave_type, project_activity get a
-- company_id, and job status moves from settings.EMPLOYMENT_STATUS into a new
-- employment_status table. Rows the code depends on carry a fixed `code`
-- (leave_type: general/official/comp_off/lop/maternity; employment_status:
-- probation/confirmed/internship/resigned) so behaviour no longer relies on ids.
--
-- Existing rows become Digital Mesh's (platform company 4); EM Soft (5) gets a
-- copy of each, and every EM reference (user_profile, pending profile changes,
-- leave tables, timesheet items) is remapped to the copy. copied_from_id records
-- which row a copy came from - company_lookups_down.sql relies on it.
--
-- Run after legacy_company_ids_to_platform.sql. Check the 4/5 ids against
-- platform_company before running elsewhere. DDL auto-commits in MySQL, so the
-- schema part is not transactional; the data part is.

-- ---------------------------------------------------------------- schema
ALTER TABLE job_title
    ADD COLUMN company_id INT NULL,
    ADD COLUMN copied_from_id INT NULL,
    ADD INDEX idx_job_title_company (company_id);

ALTER TABLE project_activity
    ADD COLUMN company_id INT NULL,
    ADD COLUMN copied_from_id INT NULL,
    ADD INDEX idx_project_activity_company (company_id);

ALTER TABLE leave_type
    ADD COLUMN company_id INT NULL,
    ADD COLUMN code VARCHAR(30) NULL,
    ADD COLUMN copied_from_id INT NULL,
    ADD INDEX idx_leave_type_company (company_id),
    ADD UNIQUE KEY uq_leave_type_company_code (company_id, code);

CREATE TABLE employment_status (
    id INT NOT NULL AUTO_INCREMENT,
    company_id INT NOT NULL,
    name VARCHAR(50) NOT NULL,
    code VARCHAR(30) NULL,
    sort_order INT NOT NULL DEFAULT 0,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    copied_from_id INT NULL,
    PRIMARY KEY (id),
    KEY idx_employment_status_company (company_id),
    UNIQUE KEY uq_employment_status_company_code (company_id, code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- job_status now holds employment_status.id, which grows past tinyint's 127.
ALTER TABLE user_profile MODIFY job_status INT NULL;

-- ------------------------------------------------------------------ data
START TRANSACTION;

-- Existing rows -> Digital Mesh
UPDATE job_title        SET company_id = 4 WHERE company_id IS NULL;
UPDATE project_activity SET company_id = 4 WHERE company_id IS NULL;
UPDATE leave_type       SET company_id = 4 WHERE company_id IS NULL;
UPDATE leave_type SET code = CASE leave_type_id
        WHEN 1 THEN 'general' WHEN 2 THEN 'official' WHEN 3 THEN 'comp_off'
        WHEN 4 THEN 'lop' WHEN 5 THEN 'maternity' END
    WHERE company_id = 4 AND leave_type_id IN (1, 2, 3, 4, 5);

-- Same ids as the old settings.EMPLOYMENT_STATUS, so user_profile.job_status stays valid
INSERT INTO employment_status (id, company_id, name, code, sort_order) VALUES
    (1, 4, 'Probation', 'probation', 1),
    (2, 4, 'Confirmed', 'confirmed', 2),
    (3, 4, 'Internship', 'internship', 3),
    (4, 4, 'Resigned', 'resigned', 4);

-- Copies for EM Soft
INSERT INTO job_title (job_title, job_description, note, is_deleted, company_id, copied_from_id)
    SELECT job_title, job_description, note, is_deleted, 5, id FROM job_title WHERE company_id = 4;
INSERT INTO project_activity (name, description, is_deleted, company_id, copied_from_id)
    SELECT name, description, is_deleted, 5, activity_id FROM project_activity WHERE company_id = 4;
INSERT INTO leave_type (leave_type_name, available_flag, default_no_of_leaves, company_id, code, copied_from_id)
    SELECT leave_type_name, available_flag, default_no_of_leaves, 5, code, leave_type_id FROM leave_type WHERE company_id = 4;
INSERT INTO employment_status (company_id, name, code, sort_order, is_deleted, copied_from_id)
    SELECT 5, name, code, sort_order, is_deleted, id FROM employment_status WHERE company_id = 4;

-- Point EM Soft's references at EM Soft's copies
UPDATE user_profile up
    JOIN job_title jt ON jt.copied_from_id = up.job_title AND jt.company_id = 5
    SET up.job_title = jt.id WHERE up.company_id = 5;
UPDATE user_profile up
    JOIN employment_status es ON es.copied_from_id = up.job_status AND es.company_id = 5
    SET up.job_status = es.id WHERE up.company_id = 5;

UPDATE user_profile_provisional pp
    JOIN user_profile up ON up.user_id = pp.emp_id
    JOIN job_title jt ON jt.copied_from_id = pp.value AND jt.company_id = 5
    SET pp.value = jt.id WHERE up.company_id = 5 AND pp.field = 'job_title';
UPDATE user_profile_provisional pp
    JOIN user_profile up ON up.user_id = pp.emp_id
    JOIN employment_status es ON es.copied_from_id = pp.value AND es.company_id = 5
    SET pp.value = es.id WHERE up.company_id = 5 AND pp.field = 'job_status';

UPDATE leave_quota t JOIN user_profile up ON up.user_id = t.employee_id
    JOIN leave_type lt ON lt.copied_from_id = t.leave_type_id AND lt.company_id = 5
    SET t.leave_type_id = lt.leave_type_id WHERE up.company_id = 5;
UPDATE leave_requests t JOIN user_profile up ON up.user_id = t.employee_id
    JOIN leave_type lt ON lt.copied_from_id = t.type_id AND lt.company_id = 5
    SET t.type_id = lt.leave_type_id WHERE up.company_id = 5;
UPDATE leaves t JOIN user_profile up ON up.user_id = t.employee_id
    JOIN leave_type lt ON lt.copied_from_id = t.type_id AND lt.company_id = 5
    SET t.type_id = lt.leave_type_id WHERE up.company_id = 5;
UPDATE compensatory_leave_request t JOIN user_profile up ON up.user_id = t.employee_id
    JOIN leave_type lt ON lt.copied_from_id = t.leave_type_id AND lt.company_id = 5
    SET t.leave_type_id = lt.leave_type_id WHERE up.company_id = 5;

UPDATE timesheet_item t JOIN user_profile up ON up.user_id = t.user_id
    JOIN project_activity pa ON pa.copied_from_id = t.activity_id AND pa.company_id = 5
    SET t.activity_id = pa.activity_id WHERE up.company_id = 5;
UPDATE timesheet_item_archive t JOIN user_profile up ON up.user_id = t.user_id
    JOIN project_activity pa ON pa.copied_from_id = t.activity_id AND pa.company_id = 5
    SET t.activity_id = pa.activity_id WHERE up.company_id = 5;

COMMIT;
