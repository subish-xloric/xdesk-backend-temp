-- =============================================================================
-- Attendance V2 - ROLLBACK (DOWN)
-- Removes everything added by attendance_v2_up.sql. DESTROYS all Attendance V2
-- data (punches, sessions, daily attendance, shifts, devices, collectors,
-- audit log). Take a backup first. Legacy attendance is unaffected.
--
-- Django equivalent:
--     python manage.py migrate attendance_v2_access zero
--     python manage.py migrate platform_access 0013_seed_rewards_view_scope
-- (also remove 'pTracker.dataaccess.attendance_v2_access' from INSTALLED_APPS
--  and the api/attendance/v2/ route if rolling back the code).
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- children first
DROP TABLE IF EXISTS `attv2_session`;
DROP TABLE IF EXISTS `attv2_daily_attendance`;
DROP TABLE IF EXISTS `attv2_event`;
DROP TABLE IF EXISTS `attv2_raw_punch`;
DROP TABLE IF EXISTS `attv2_sync_log`;
DROP TABLE IF EXISTS `attv2_collector_devices`;
DROP TABLE IF EXISTS `attv2_collector`;
DROP TABLE IF EXISTS `attv2_device`;
DROP TABLE IF EXISTS `attv2_location`;
DROP TABLE IF EXISTS `attv2_shift_assignment`;
DROP TABLE IF EXISTS `attv2_shift_schedule`;
DROP TABLE IF EXISTS `attv2_shift`;
DROP TABLE IF EXISTS `attv2_settings`;
DROP TABLE IF EXISTS `attv2_audit_log`;

SET FOREIGN_KEY_CHECKS = 1;

-- capability grants and catalog rows
DELETE FROM `platform_membership_extra_capabilities`
 WHERE `capability_id` IN ('attendance.manage_devices', 'attendance.manage_shifts', 'attendance.correct');
DELETE FROM `platform_role_capabilities`
 WHERE `capability_id` IN ('attendance.manage_devices', 'attendance.manage_shifts', 'attendance.correct');
DELETE FROM `platform_capability`
 WHERE `code` IN ('attendance.manage_devices', 'attendance.manage_shifts', 'attendance.correct');

-- migration bookkeeping
DELETE FROM `django_migrations` WHERE `app` = 'attendance_v2_access';
DELETE FROM `django_migrations` WHERE `app` = 'platform_access' AND `name` = '0014_seed_attendance_v2_capabilities';
