from celery.schedules import crontab

# from CorePlatform.CeleryQueue import *

# '''A list of integers from 0-6, where Sunday = 0 and Saturday = 6,'''

from pTracker.settings.constants import CELERY_QUEUE

PRO_SCHEDULE = {
    'daily_punch_in_report': {
        'task': 'pTracker.cronjobs.daily_punch_in_report.create_daily_punch_in_report',
        'schedule': crontab(hour=11, minute=1, day_of_week='1-5'),
        'options': {'queue': CELERY_QUEUE['daily_report']},
        'args': (),
    },

    'daily_work_hours_report': {
        'task': 'pTracker.cronjobs.daily_work_hours_report.create_daily_work_hours_report',
        'schedule': crontab(hour=8, minute=30, day_of_week='1-5'),
        'options': {'queue': CELERY_QUEUE['daily_report']},
        'args': (),
    },

    'daily_att_report': {
        'task': 'pTracker.cronjobs.att_reports.create_daily_att_report',
        'schedule': crontab(hour=8, minute=32, day_of_week='1-5'),
        'options': {'queue': CELERY_QUEUE['daily_report']},
        'args': (),
    },

    'weekly_summary_report': {
        'task': 'pTracker.cronjobs.weekly_summary_report.create_weekly_summary_report',
        'schedule': crontab(hour=8, minute=34, day_of_week='1'),
        'options': {'queue': CELERY_QUEUE['daily_report']},
        'args': (),
    },

    'monthly_att_report': {
        'task': 'pTracker.cronjobs.att_reports.create_monthly_att_report',
        'schedule': crontab(hour=8, minute=36, day_of_month='2'),
        'options': {'queue': CELERY_QUEUE['daily_report']},
        'args': (),
    },

    # 'monthly_missing_time_sheet_report': {
    #     'task': 'pTracker.cronjobs.montly_missing_time_sheet.create_monthly_missing_time_sheet_report',
    #     'schedule': crontab(hour=10, minute=30, day_of_month='1'),
    #     'options': {'queue': CELERY_QUEUE['daily_report']},
    #     'args': (),
    # },

    'send_birthday_wish_email': {
        'task': 'pTracker.cronjobs.email_sender.send_birthday_wish_email',
        'schedule': crontab(hour=8, minute=15, day_of_week='0-6'),
        'options': {'queue': CELERY_QUEUE['mail_sender']},
        'args': (),
    },

    #  'send_work_anniversary_email': {
    #     'task': 'pTracker.cronjobs.email_sender.send_work_anniversary_email',
    #     'schedule': crontab(hour=5, minute=36, day_of_week='0-6'),
    #     'options': {'queue': CELERY_QUEUE['mail_sender']},
    #     'args': (),
    # },

    'terminate_employee': {
        'task': 'pTracker.cronjobs.offboarding_final_process.terminate_employee_check',
        'schedule': crontab(hour=1, minute=0, day_of_week='0-6'),
        'options': {'queue': CELERY_QUEUE['daily_report']},
        'args': (),
    },

    'career_opening_updataion': {
        'task': 'pTracker.cronjobs.career_opening_updation.career_opening_updataion',
        'schedule': crontab(hour='*/2', minute=0, day_of_week='0-6'),
        'options': {'queue': CELERY_QUEUE['daily_report']},
        'args': (),
    },

    'create_birthday_events': {
        'task': 'pTracker.cronjobs.tv_notification.create_birthday_events',
        'schedule': crontab(hour=6, minute=30),
        'options': {'queue': CELERY_QUEUE['daily_report']},
        'args': (),
    },

    'send_interview_notifications': { 
        'task': 'pTracker.cronjobs.interview_notifications.send_interview_notifications',
        'schedule': crontab(minute='*/15', hour='*', day_of_week='*'),
        'options': {'queue': 'TEEEEE'},
        'args': (),
    },

}