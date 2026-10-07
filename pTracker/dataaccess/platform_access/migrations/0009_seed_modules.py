from django.db import migrations

# code, display name, description. Codes match Capability.module strings.
MODULES = [
    ('employee', 'User Management', 'Employee directory, profiles and user administration'),
    ('attendance', 'Attendance', 'Attendance, punch records and work-from-home'),
    ('leave', 'Leave Management', 'Leave requests, quotas and compensatory leave'),
    ('timesheet', 'Timesheet', 'Timesheets, approvals and timesheet reports'),
    ('project', 'Projects & Resources', 'Projects, modules and employee-project allocation'),
    ('ticket', 'Ticketing System', 'Issue tracking and the external ticket API'),
    ('asset', 'Asset Management', 'Asset categories, vendors and purchase orders'),
    ('appraisal', 'Appraisal', 'Appraisal cycles, forms and performance letters'),
    ('assessment', 'Assessment', 'Skill and technical assessments'),
    ('induction', 'Induction', 'New-joiner induction'),
    ('onboarding', 'Onboarding', 'Onboarding candidates and conversion to employees'),
    ('offboard', 'Offboarding', 'Resignation, exit forms and termination'),
    ('interview', 'Recruitment', 'Career openings, candidates and interviews'),
    ('payroll', 'Finance & Tax', 'Payslips, CTC, TDS and tax declarations'),
    ('rewards', 'Rewards & TV', 'Reward nominations and TV notice board'),
    ('wiki', 'Wiki', 'Internal knowledge base'),
]

# module -> modules it depends on (from cross-module imports found in the code)
REQUIRES = {
    'timesheet': ['project', 'attendance', 'leave'],
    'attendance': ['leave'],
    'leave': ['attendance'],
    'ticket': ['project'],
}

# Asset capabilities were identified in the audit but left out of 0007.
ASSET_CAPABILITIES = [
    ('asset.manage_categories', 'asset', 'Create and delete asset categories'),
    ('asset.manage_vendors', 'asset', 'Create and delete asset vendors'),
    ('asset.manage_purchase_orders', 'asset', 'Create and approve purchase orders'),
]


def seed(apps, schema_editor):
    Module = apps.get_model('platform_access', 'Module')
    Capability = apps.get_model('platform_access', 'Capability')

    for code, name, description in MODULES:
        Module.objects.get_or_create(code=code, defaults={'name': name, 'description': description})

    for code, required in REQUIRES.items():
        Module.objects.get(pk=code).requires.set(Module.objects.filter(code__in=required))

    for code, module, description in ASSET_CAPABILITIES:
        Capability.objects.get_or_create(code=code, defaults={'module': module, 'description': description})


def unseed(apps, schema_editor):
    Module = apps.get_model('platform_access', 'Module')
    Capability = apps.get_model('platform_access', 'Capability')
    Module.objects.filter(code__in=[m[0] for m in MODULES]).delete()
    Capability.objects.filter(code__in=[c[0] for c in ASSET_CAPABILITIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('platform_access', '0008_module_and_company_module'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
