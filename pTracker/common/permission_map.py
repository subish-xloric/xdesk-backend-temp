""" Legacy Django permission codename (Utility.is_permitted) -> platform capability.

is_permitted() used to look the codename up on the user's Django Group / user
permissions. It now asks has_capability() for the mapped capability instead, so
one company-scoped Role/Membership system decides. A codename that is not in
this table is denied (fail-closed) - add it here, and to the Capability
catalog, when a new check is introduced.

SAMPLE MAPPING: several legacy codenames are finer-grained than the catalog and
share a capability (e.g. all payslip steps -> payroll.process). Split them by
adding capabilities if the business needs the finer control.
"""

PERMISSION_TO_CAPABILITY = {
    # payroll - payslips
    'can_process_payslip': 'payroll.process',
    'can_validate_payslip': 'payroll.process',
    'can_revoke_payslip': 'payroll.process',
    'can_publish_payslip': 'payroll.process',
    # payroll - CTC / TDS / tax claims
    'can_manage_ctc': 'payroll.manage_ctc',
    'can_modify_ctc': 'payroll.manage_ctc',
    'can_manage_tds': 'payroll.manage_tds',
    'can_modify_tds': 'payroll.manage_tds',
    'can_manage_other_income': 'payroll.manage_tax_claims',
    'can_approve_claim': 'payroll.manage_tax_claims',
    'can_view_claim': 'payroll.manage_tax_claims',
    'can_delete_employee_declaration': 'payroll.manage_tax_claims',
    'can_view_party_data': 'payroll.view',
    # payroll - tax assessment periods
    'can_view_assessment_period': 'payroll.view_tax_periods',
    'can_add_assessment_period': 'payroll.manage_tax_periods',
    'can_delete_assessment_period': 'payroll.manage_tax_periods',
    'can_add_employee_to_assessment_period': 'payroll.manage_tax_periods',
    'can_delete_employee_from_assessment_period': 'payroll.manage_tax_periods',
    # interview / recruitment
    'can_create_interview': 'interview.manage_interviews',
    'can_modify_interview': 'interview.manage_interviews',
    'can_view_interview': 'interview.view_candidates',
    'can_create_candidate': 'interview.manage_candidates',
    'can_modify_candidate': 'interview.manage_candidates',
    'can_view_candidate': 'interview.view_candidates',
    # rewards / TV
    'can_manage_tv_notice': 'rewards.manage_tv_content',
    'can_manage_tv_dm_vibes': 'rewards.manage_tv_content',
    # employee
    'view_employee_list': 'employee.view_list',
    'view_employee_detail_profile': 'employee.view_list',
    # projects / timesheet
    'can_create_emp_project_mapping': 'resource.manage_allocation',
    'can_unblock_prevent_login': 'timesheet.manage_exceptions',
}
