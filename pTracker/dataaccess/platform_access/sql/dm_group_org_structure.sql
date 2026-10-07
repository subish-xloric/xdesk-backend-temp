-- DM Group org structure: 1 tenant, 2 companies, 3 branches, 9 roles.
-- Generated from the actual rows created by
-- `python manage.py seed_dm_group_org_structure` on 2026-09-16.
-- Reference only - re-running this file directly will fail on the unique
-- constraints (tenant.slug, company.legacy_company_id) if the rows already
-- exist; use the management command for a safe, idempotent re-run instead.

-- Tenant
INSERT INTO platform_tenant (id, slug, name, status, created_at, updated_at)
VALUES (3, 'digitalmesh-group', 'DM Group', 'active', NOW(), NOW());

-- Companies (legacy_company_id bridges to settings.COMPANY['DM']/['EM'])
INSERT INTO platform_company
    (id, tenant_id, parent_company_id, legal_name, short_name, legacy_company_id,
     registered_address, contact_email, is_active, created_at, updated_at)
VALUES
    (4, 3, NULL, 'Digital Mesh', 'Digital Mesh', 2, NULL, NULL, 1, NOW(), NOW()),
    (5, 3, NULL, 'EM Soft',      'EM Soft',      3, NULL, NULL, 1, NOW(), NOW());

-- Branches
INSERT INTO platform_branch
    (id, company_id, name, code, kind, timezone, address, is_active, created_at, updated_at)
VALUES
    (2, 4, 'CSEZ Cochin',         'CC',  'office', 'Asia/Kolkata', NULL, 1, NOW(), NOW()),
    (3, 4, 'Tech Park Edapilly',  'TPE', 'office', 'Asia/Kolkata', NULL, 1, NOW(), NOW()),
    (4, 5, 'Head Office',         'HO',  'office', 'Asia/Kolkata', NULL, 1, NOW(), NOW());

-- Roles (company-scoped - Digital Mesh and EM Soft have independent role sets)
INSERT INTO platform_role (id, company_id, name, description, is_active, created_at, updated_at)
VALUES
    -- Digital Mesh (company_id=4)
    (7,  4, 'Director',    NULL, 1, NOW(), NOW()),
    (8,  4, 'HR',          NULL, 1, NOW(), NOW()),
    (9,  4, 'Office Head', NULL, 1, NOW(), NOW()),
    (10, 4, 'Lead',        NULL, 1, NOW(), NOW()),
    (11, 4, 'Developer',   NULL, 1, NOW(), NOW()),
    -- EM Soft (company_id=5)
    (12, 5, 'CEO',         NULL, 1, NOW(), NOW()),
    (13, 5, 'HR Manager',  NULL, 1, NOW(), NOW()),
    (14, 5, 'Auditor',     NULL, 1, NOW(), NOW()),
    (15, 5, 'Account',     NULL, 1, NOW(), NOW());
