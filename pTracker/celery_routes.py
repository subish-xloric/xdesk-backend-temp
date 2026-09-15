from pTracker.settings.constants import CELERY_QUEUE


CELERY_ROUTES_DICT = {
    'tasks.create_daily_punch_in_report': {'queue': CELERY_QUEUE['daily_report']},
    'tasks.create_daily_work_hours_report': {'queue': CELERY_QUEUE['daily_report']},
    'tasks.create_daily_att_report': {'queue': CELERY_QUEUE['daily_report']},
    'tasks.create_weekly_summary_report': {'queue': CELERY_QUEUE['daily_report']},
    'tasks.create_monthly_att_report': {'queue': CELERY_QUEUE['daily_report']},
    'tasks.create_monthly_missing_time_sheet_report': {'queue': CELERY_QUEUE['daily_report']},

    'tasks.send_daily_work_hours_report': {'queue': CELERY_QUEUE['mail_sender']},
    'tasks.send_daily_att_report': {'queue': CELERY_QUEUE['mail_sender']},
    'tasks.send_daily_punch_in_report': {'queue': CELERY_QUEUE['mail_sender']},
    'tasks.send_weekly_report': {'queue': CELERY_QUEUE['mail_sender']},
    'tasks.send_monthly_att_report': {'queue': CELERY_QUEUE['mail_sender']},
    'tasks.send_email_notification': {'queue': CELERY_QUEUE['mail_sender']},

    'tasks.send_birthday_wish_email': {'queue': CELERY_QUEUE['mail_sender']},
    'tasks.send_work_anniversary_email': {'queue': CELERY_QUEUE['mail_sender']},

    'tasks.generate_appraisal_forms': {'queue': CELERY_QUEUE['appraisal_form']},
    'tasks.offboard_final_process': {'queue': CELERY_QUEUE['offboarding']},
    'tasks.career_opening_updataion': {'queue': CELERY_QUEUE['daily_report']},

    'tasks.collect_missing_details': {'queue': CELERY_QUEUE['mail_sender']},
    'tasks.create_birthday_events': {'queue': CELERY_QUEUE['daily_report']},
    'tasks.send_interview_notifications': {'queue': CELERY_QUEUE['mail_sender']}, 
}

