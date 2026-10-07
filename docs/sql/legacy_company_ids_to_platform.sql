-- Move the remaining legacy company ids (2 = Digital Mesh, 3 = EM Soft) to the
-- platform_company ids (4, 5), and give platform_company the real legal names and
-- addresses that used to be hard-coded (settings DM_ADDRESS / EM_ADDRESS).
-- Check the ids against platform_company.legacy_company_id before running elsewhere.

START TRANSACTION;

UPDATE platform_company SET
    legal_name = 'Digital Mesh Softech India (P) Limited',
    registered_address = 'Unit 1: 43-A, E Block, 2nd Floor,\nCochin Special Economic Zone, Kakkanad, Kochi – 682 037, Kerala, India.\nTel: +91-484-4060200, Fax: +91-484-4060201'
WHERE id = 4;

UPDATE platform_company SET
    legal_name = 'EM Softech LLP',
    registered_address = 'Unit 1:Plot No.43/ A, D Block, 2nd floor,\nCochin Special Economic Zone(CSEZ), Kakkanad, Kochi-682037, Kerala, India.\nTel:+91-484-2413280'
WHERE id = 5;

UPDATE holidays                    SET company_id = CASE company_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE company_id IN (2, 3);
UPDATE additional_working_days     SET company_id = CASE company_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE company_id IN (2, 3);
UPDATE admin_employee              SET company_id = CASE company_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE company_id IN (2, 3);
UPDATE attendance_exclude_employee SET company_id = CASE company_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE company_id IN (2, 3);
UPDATE audit_logs                  SET organization_id = CASE organization_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE organization_id IN (2, 3);
UPDATE project                     SET company_id = CASE company_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE company_id IN (2, 3);
UPDATE user_profile                SET company_id = CASE company_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE company_id IN (2, 3);

-- Tables that were empty on dev but carry a company/organization id - remap them too.
UPDATE leave_quota                     SET company_id = CASE company_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE company_id IN (2, 3);
UPDATE leave_requests                  SET company_id = CASE company_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE company_id IN (2, 3);
UPDATE leaves                          SET company_id = CASE company_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE company_id IN (2, 3);
UPDATE compensatory_leave_request      SET company_id = CASE company_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE company_id IN (2, 3);
UPDATE daily_attendance                SET company_id = CASE company_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE company_id IN (2, 3);
UPDATE appraisal_form                  SET organization_id = CASE organization_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE organization_id IN (2, 3);
UPDATE off_boarding_exit_form          SET organization_id = CASE organization_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE organization_id IN (2, 3);
UPDATE off_boarding_exit_interview_form SET organization_id = CASE organization_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE organization_id IN (2, 3);
UPDATE off_boarding_request            SET organization_id = CASE organization_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE organization_id IN (2, 3);
UPDATE onboarding_candidate            SET organization_id = CASE organization_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE organization_id IN (2, 3);
UPDATE employee_pay_header             SET organization = CASE organization WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE organization IN (2, 3);
UPDATE tax_batch                       SET org_id = CASE org_id WHEN 2 THEN 4 WHEN 3 THEN 5 END WHERE org_id IN (2, 3);

COMMIT;
