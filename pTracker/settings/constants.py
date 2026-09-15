
PUNCH_IN_CONFIG = {
    "punctual": {
        "start_time": "00:01:01",
        "end_time":"09:00:59",
        "color":"AAE89C"
    },
    "moderate": {
        "start_time": "09:01:00",
        "end_time":"09:30:59",
        "color":"F9C333"
    },

    "aggressive": {
        "start_time": "09:31:00",
        "end_time":"23:59:59",
        "color":"F96F4A"
    }
}



COMPANY = {}
COMPANY['DM'] = {'ID': 2}
COMPANY['EM'] = {'ID': 3}

UPLOAD_PATH = {}
UPLOAD_PATH['PUNCH_IN_REPORT'] = "/var/www/dm_ptracker/reports/daily_punch_in/"
UPLOAD_PATH['DAILY_WORK_HOUR_REPORT'] = "/var/www/dm_ptracker/reports/daily_work_hours/"
UPLOAD_PATH['DAILY_ATT_REPORT'] = "/var/www/dm_ptracker/reports/attendance/daily/"
UPLOAD_PATH['MONTHLY_ATT_REPORT'] = "/var/www/dm_ptracker/reports/attendance/monthly/"
UPLOAD_PATH['WEEKLY_ATT_REPORT'] = "/var/www/dm_ptracker/reports/attendance/weekly/"

CELERY_QUEUE = {
    'daily_report': 'dailyReport',
    'monthly_report': 'monthlyReport',
    'mail_sender': 'mailSender',
    'appraisal_form': 'appraisalForm',
    'offboarding': 'offBoarding',
}

THRESHOLD = {
    'LATE': 30,
    'WORK_HOUR': 5,
    'ON_TIME' : -25
}


USER_ROLES = {
    'DIRECTOR':1,
    'HR':2,
    'MANAGER':3,
    'LEAD':4,
    'DEVELOPER':5
}


FUTURE_DAYS = 4
PAST_DAYS = 3
UPCOMING_DAYS = 7
FUTURE_MONTHS = 6
BIRTHDAY_WISH_IMAGE = 50 #no of images
WORK_ANNIVERSARY_IMAGE = 10 #no of images

COUNTRY = {91: 'India'}

STATES = {18: 'Kerala', 19:'Tamil Nadu'}

DISTRICTS = {
    1: 'Alappuzha',
    2: 'Ernakulam',
    3: 'Idukki',
    4: 'Kannur',
    5: 'Kasaragod',
    6: 'Kollam',
    7: 'Kottayam',
    8: 'Kozhikode',
    9: 'Malappuram',
    10: 'Palakkad',
    11: 'Pathanamthitta',
    12: 'Thiruvananthapuram',
    13: 'Thrissur',
    14: 'Wayanad',
    20: 'Tiruchirapalli',
    21: 'Kanyakumari',
    23: 'Thuttukudi'
}
#b = [(k, v) for k, v in a.items()]

EMPLOYMENT_STATUS = {1: 'Probation', 2: 'Confirmed', 3: 'Internship', 4: 'Resigned'}

ERROR_MSG = {
    'application_error': 'Applicaton execution failed, {0}. LogID: {1}',
    "access_denied": "Access Denied, You Don’t Have Permission To Access on This.",
    "no_permission": "Sorry, You Don't Have Permission To Perform This Action!!!"
    }

ORGANIZATION = {2:'DigitalMesh', 3: 'EM Softtech'}

WFH_REQUEST_STATUS = {1: "Requested", 2: "Approved", 3: "Cancelled", 4: "Rejected"}

UPCOMING_MONTH=180

PROBATION_LEAVE = 5.0
MAXIMUM_LEAVE_DURATION = 365   #in days

LEAVE_REQUEST_STATUS = {"Requested": 1, "Approved": 2,"Cancelled": 3,"Rejected": 4,"Edited": 5}

LEAVE_DAY_TYPE = {"Fullday" : 1,"Halfday(fornoon)" : 2,"Halfday(afternoon)" :3}

LEAVE_HOURS = {"Fullday" : 8,"Halfday" : 4}

LEAVE_LENGTH = {"Fullday" : 1 , "Halfday" : .5}
LEAVE_ACTION_LOG = {
    1: "Leave request created by {0} at {1}",
    2: "Leave request approved by {0} at {1}",
    3: "Leave request cancelled by {0} at {1}",
    4: "Leave request rejected by {0} at {1}",
    5: "Leave request edited by {0} at {1} ",
    6: "Leave debited by {0} at {1}"
}


MAXIMUM_COMP_LEAVE_DURATION = 5 #in days
MAXIMUM_MATERNITY_LEAVE_DURATION = 365
COMP_LEAVE_ACTION_LOG = {
    1: "Compensatory leave request created by {0} at {1}",
    2: "Compensatory leave request approved by {0} at {1}",
    3: "Compensatory leave request cancelled by {0} at {1}",
    4: "Compensatory leave request rejected by {0} at {1}",
    5: "Compensatory leave request edited by {0} at {1} "
}

TEAM_EMAIL = 'team@mydomain.com'
EM_TEAM_EMAIL = "team@mydomain.com"

LEAVE_DEFAULT_NOTIFOCATION_EMAIL = 'leave@mydomain.com'

INTERVIEW_DEFAULT_MAIL = 'interview@mydomain.com'

HR_EMAIL = 'radhi.menon@mydomain.com'

PROBATION_LOP_LEAVE = 10
PROBATION_GENERAL_LEAVE = 5

OFF_BOARD_REQUEST_STATUS = {
    "Pending": 1,
    "Accepted": 2,
    "Cancelled": 3,
    "Rejected": 4,
    "Initiated": 5,
    "Completed": 6
}

DEAFULT_NOTICE_PERIOD_LENGHT = 45

OFF_BOARD_ACTION_LOG = {
    1: "Resignation request created by {0} at {1}",
    2: "Resignation request approved by {0} at {1}",
    3: "Resignation request cancelled by {0} at {1}",
    4: "Resignation request rejected by {0} at {1}",
    5: "Resignation request completed by {0} at {1} "
}

AUDIT_LOG_EVENT_DETAILS = {
    0: "User with email {0} has failed login attempt.",
    1: "User with username {0} has logged in."
}

DEFAULT_EXPIRE_TIME = 1440

ADMIN_DEPT = {
            "dept_id": '1',
            "name":"Admin Department",
            "emp_name":"Manju KG",
            "res_emp_id" : '22',
            'email' : 'manju.kg@mydomain.com',
            "checklist":[{"id":'1',"name":"Books/Journals/Magazines from library","value":0},{"id":'2',"name":"Lunch Coupons amount","value":0}],
            "signed" : 0,
            "signed_date" : "",
            "sign" : ''
}

OPERATIONS_DEPT = {
            "dept_id": '2',
            "name":"Manager Operations",
            "emp_name":"Ajithkumar S",
            "res_emp_id" : '7',
            "email" : 'ajiths@mydomain.com',
            "checklist":[{"id":'1',"name":"KT Completed","value":0}],
            "signed" : 0,
            "signed_date" : "",
            "sign" : ''
}

QA_DEPT = {
            "dept_id": '4',
            "name":"QA Department",
            "emp_name":"Jibin Joy",
            "res_emp_id" : '27',
            "email" : 'jibin.joy@mydomain.com',
            "checklist":[{"id":'1',"name":"QA Tasks Completed","value":0}],
            "signed" : 0,
            "signed_date" : "",
            "sign" : ''
}

SAG_DEPT = {
            "dept_id": '5',
            "name":"SAG Department",
            "emp_name":"Ratheesh M R",
            "email" : 'ratheesh@mydomain.com',
            "res_emp_id" : '8',
            "checklist":[
                {"id":'1',"name":"Disable Domain account","value":0},
                {"id":'2',"name":"Disable e-mail id","value":0},
                {"id":'3',"name":"Disable SVN account","value":0},
                {"id":'4',"name":"Return Laptop and all assets","value":0},
                {"id":'5',"name":"Delete email distribution list","value":0},
                {"id":'6',"name":"Disable eSSL access","value":0}
                ],
            "signed" : 0,
            "signed_date" : "",
            "sign" : ''
}

ACCOUNTS_DEPT = {
            "dept_id": '6',
            "name":"Accounts Department",
            "emp_name":"Renjith M B",
            "email" : 'renjith@mydomain.com',
            "res_emp_id" : '4',
            "checklist":[{"id":'1',"name":"Documents regarding tax","value":0}],
            "signed" : 0,
            "signed_date" : "",
            "sign" : ''
}

HR_DEPT = {
            "dept_id": '7',
            "name":"HR Department",
            "emp_name":"Radhi Menon",
            "res_emp_id" : '20',
            "email" : 'radhi.menon@mydomain.com',
            "checklist":[{"id":'1',"name":"Check List","value":0},{"id":'2',"name":"Acces Card","value":0},{"id":'3',"name":"Disable in DM Desk","value":0},{"id":'4',"name":"CSEZ Card","value":0},{"id":'5',"name":"Visting Cards","value":0},{"id":'6',"name":"Exit interview Completed","value":0}],
            "signed" : 0,
            "signed_date" : "",
            "sign" : ''
}



OFF_BOARD_FORM_ACTION_LOG = {
    1: "Offboarding exit form created by {0} at {1}",
    2: "Offboarding exit form signed by {0} at {1}",
    3: "Offboarding process initiated by {0} at {1}"
}

EMP_LEAD_MAPPING_LOG = {
    1: "Assigned to {0}'s team on {1}",
    2: "Relieved from {0}'s team on {1}",
}

EMP_PROJECT_MAPPING_LOG = {
    1: "Assigned to {0} on {1}",
    2: "Relieved from {0} on {1}",
}

OFFBOARDING_DOC_TYPES = {
    1: "Experience Certificate",
    2: "Relieving Letter",
    3: "Grativity Document"
}




OFF_BOARD_INTERVIEW_FORM_STATUS = {"created": 1, }


OFF_BOARD_INTERVIEW_FORM_ACTION_LOG = {
    1: "Offboarding exit interview form created by {0} at {1}",
    2: "Offboarding exit interview form signed by {0} at {1}",
}

HR_EMP_ID = '20'

CEO_EMP_ID = ''

CTO_EMP_ID = ''

EXIT_INTERVIEW_NOTE = "Your departure from {0} will indeed be a great loss to us. We would,however take this opportunity to understand from you the good practices we have and also gaps in our existing systems and processes and try to further improve upon them.Your feedback is extremely important to us and we would be grateful for your feedback and frank comments on the issues as mentioned hereunder"

HR_NAME = "Radhi Menon"

DEFAULT_PAGE_LIMIT = 10
MOBILE_LEAVE_REQUEST_STATUS = {1: "REQUESTED", 2: "APPROVED", 3: "CANCELLED", 4: "REJECTED"}

FCM_API_KEY = "AAAAsXaj2PY:APA91bHhdzPXU3SeeqYpDJ-yCHO6xQ5K6OwsKp-cj-LBK8-yuv6CrnUrSBCcQD2xvaJX6dwS_F7bKofFO8JUS9cnQXF29hwfGcD3LU7afy-lNIfEMUDGPHQMTw8_u5AwuSfrI0tlVi3y"

JSON_TEMPLATE_PATH = 'pTracker/json_templates/'

APPRAISAL_STATUS = {
    "APPRAISAL_ISSUED": 1,
    "APPRAISEE_SUBMITTED": 2,
    "APPRAISER_SUBMITTED": 3,
    "REVIEWER_SUBMITTED": 4
}

APPRAISAL_LOG = {
    1: "Appraisal issued by {0} at {1}",
    2: "Appraisal form submitted by {0} at {1}",
    3: "Appraisal form saved by {0} at {1}"
}

PERSONAL_APPRAISAL_RATINGS = {
    1: "Exceptional Contributor",
    2: "Significant Contributor",
    3: "Contributor",
    4: "Partial Contributor"
}

APPRAISAL_EXCLUDED_EMPLOYESS = [2, 3, '2', '3']

OFF_BOARDING_CC_MAILS = ["hr@mydomain.com", "ajith.s@mydomain.com"]


SEO_EMPLOYESS = [113,'113',152,'152', 209, '209',219,'219']

PROCESS_ASSOCIATE_EMPLOYEES = [74,'74',39,'39',40,'40',4,9,10,20,22,217]

APPRAISAL_RATING_PERCENTAGE = {1: 20, 2: 15, 3: 10, 4: 5}

APPRAISAL_RESPONSE_ATTRIBUTES = {
    1 : {"parent": 'self_assessment_form', "attribute": "What are your views/suggestions regarding your supervisors & the organization?"},
    2 : {"parent": 'self_assessment_form', "attribute" :"Concerns, if any"},
    3 : {"parent": 'justification_for_rating', "attribute": "value"},
    4 : {"parent": 'recommendation_to_management', "attribute": "value"},
    5 : {"parent": 'training_need_identification', "attribute": "content_b"}
}

WFH_REQUEST_STATUS_V1 = {"Requested": 1,"Approved": 2,"Cancelled": 3,"Rejected": 4}

LEAVE_REQUEST_STATUS_V1 = {"Requested": 1,"Approved": 2,"Cancelled": 3,"Rejected": 4}

TERMINATION_ACTION_LOG = {
     1: "Termination process initiated by {0} at {1}",
     2: "Relieving process initiated by {0} at {1}",
}

OFFBOARDING_TYPE = {1: "Resigned", 2: "Relieved", 3: "Terminated"}

EM_HR_MAIL = "hr@mydomain.com"

DM_HR_MAIL = "hr@mydomain.com"

CANDIDATE_STATUS = {
    1: "Shortlisted for Interview",
    2: "Interview Scheduled",
    3: "Rejected",
    4: "On Hold",
    5: "Selected for Next Round",
    6: "Ready To Hire",
    7: "Hired",
    8: "Offer Rejected",
    #7: "Interview Scheduled." # This for second levels interviews

}

INTERVIEW_STATUS = {
    1 : "Scheduled",
    2 : "Completed",
    3 : "Cancelled"
}

HR_INTERVIEW_SKILLS = [
    (1,'Communication',1),
    (2,'Motivation and Enthusiasm',1),
    (3,'Time Management',1),
    (4,'Problem Solving',1),
    (5,'Flexibility',1),
    (6,'Dedication',1),
    (7,'CTC Budget',1),
    (8,'Immediate Joining',1)
]

FINAL_ROUND_INTERVIEW_SKILLS = [
    (1,'Professionalism',1),
    (2,'Communication',1),
    (3,'Showing Interest',1),
    (4,'Confidence',1),
    (5,'Respect',1)

]

MACHINE_TEST_SKILLS = [
    (1,'Correctness',1),
    (2,'Efficiency',1),
    (3,'Code Quality',1),
    (4,'Maintainability',1),
    (5,'Testing',1),
    (6,'Error Handling',1),
    (7,'Documentation',1),
    (8,'UI-UX',1)

]

COMPANY_NAME_FOR_INTERVIEW_MAIL = "Digital Mesh Softech India P Limited"

FINANCE_STATUS = {
    1 : "Pending",
    2 : "Under Process",
    3 : "Processed",
    4 : "N/A"
}

MONTHS = {
  4: "April",
  5: "May",
  6: "June",
  7: "July",
  8: "August",
  9: "September",
  10: "October",
  11: "November",
  12: "December",
  1: "January",
  2: "February",
  3: "March"
}

TAX_CONSTANTS = {
    'standard_deduction': 50000,
}

FIN_YEAR_MONTH_ORDER_LIST = [4,5,6,7,8,9,10,11,12,1,2,3]

FINANCE_PAY_SLIP_LOG = {
    2: "Pay Slips Processed by {0} at {1}",
    0: "Pay Slips Reverted by {0} at {1}, <br><b>Reason: {2}</b>",
    3: "Pay Slips Published by {0} at {1}",
}

CIS_STATUS = {
    1 : "Pending",
    2 : "Completed"
}

ASSESSMENT_LOG = {
    1: "Assessment Initiated by {0} at {1}",
    2: "Assessment Resceduled by {0} at {1}",
    3: "Assessment Updated by {0} at {1}",
    4: "Assessment Cancelled by {0} at {1}",
}

DEPARTMENTS = ["QA","Developer","SEO"]

PROJECT_ACC_MAP_STATUS = {
    1: "Mapped",
    2: "Un Mapped"
}
PERFORMANCE_DICT = {1: 'Poor', 2: 'Average', 3: 'Good', 4: 'Very Good', 5: 'Excellent'}
ASSESSMENT_STATUS = {
    1 : "Initiated",
    2 : "In Progress",
    3 : "Completed",
    4 : "Cancelled"
}

ACCOUNT_MAP_LOG = {
    1: "Account Mapped by {0} at {1}",
    2: "Account UnMapped by {0} at {1}",
    3: "Account Mapping Updated by {0} at {1}",
}

CONSTANT_EMAIL =  {
    'dm_account_renjith' : 'renjith@mydomain.com',
    'em_hr_email': 'hr@mydomain.com',
    'dm_hr_email': 'hr@mydomain.com',
    'reward_email': 'rewards@mydomain.com'
}

REWARD_STATUS = {
    1 : "Nominated",
    2 : "Under Review",
    3 : "Approved",
    4 : "Rejected"
}

TICKETS_PRIORITY_CHOICES = [
        ('Critical', 'Critical'),
        ('High', 'High'),
        ('Normal', 'Normal'),
        ('Low', 'Low'),
    ]

TICKETS_STATUS_CHOICES_OLD = [
    ('New', 'New'),
    ('Accepted', 'Accepted'),
    ('In Progress', 'In Progress'),
    ('Completed', 'Completed'),
    ('Invalid', 'Invalid'),
    ('To Test', 'To Test'),
    ('Deferred', 'Deferred'),
    ('ReadyPushPro', 'ReadyPushPro'),
]


TICKETS_STATUS_CHOICES = [
    ('New', 'New'),
    ('Acknowledged', 'Acknowledged'),
    ('In Progress', 'In Progress'),
    ('Resolved', 'Resolved'),
    ('Released to QA', 'Released to QA'),
    ('Verified by QA', 'Verified by QA'),
    ('Reopen', 'Reopen'),
    ('ReadyPushPro', 'ReadyPushPro'),
    ('Completed', 'Completed'),
    ('Invalid', 'Invalid'),
    ('Deferred', 'Deferred'),]


TICKET_STATUS_OPEN = ['New', 'In Progress', 'Resolved', 'Released to QA', 'Verified by QA', 'Reopen', 'ReadyPushPro', 'Deferred', 'Acknowledged']

TICKET_STATUS_CLOSED = ['Completed', 'Invalid']

NEW_TICKET_STATUS = ['New']

STATUS_DEADLINE = ['In Progress','Resolved','Completed','Released to QA','Verified by QA','ReadyPushPro']

MSG_REQUIRED_STATUS = ['In Progress', 'Resolved', 'Released to QA', 'Verified by QA', 'Reopen', 'Invalid', 'Deferred']

REOPEN_REQUIRED_STATUS = ['Completed', 'Invalid', 'ReadyPushPro', 'Resolved', 'Released to QA', 'Verified by QA', 'Reopen']

NEW_REQUIRED_STATUS = ["Acknowledged", "In Progress", "Invalid", "Deferred"]

TICKETS_TYPE_CHOICES = [
    ('Bug', 'Bug'),
    ('Enhancement', 'Enhancement'),
    ('Feature', 'Feature'),
    ('Task', 'Task'),
]

TICKET_CATEGORIES = [
    ('Checklist', 'Checklist'),
    ('Design', 'Design'),
    ('Functionality', 'Functionality'),
    ('Security', 'Security'),
    ('Change Request', 'Change Request'),
    ('Other', 'Other'),
]

COMMON_PROJECTS = [17, 24] #17 SAG #16 HR Activities,  24 DM Activities

REGIME_TYPE_MAPPING = {
    1: "Old",
    2: "New",
}




#TODO
CODENAME = [

    {
        "codename": "Value of perquisites",
        "section": "section 17(2)",
    },

    {
        "codename": "Profits in lieu of salary",
        "section": "section 17(3)",
    },
    {
        "codename": "Salary received from other employer(s)",
        "section": "other_employer",
    },

    {
    "codename": "Death-cum-retirement gratuity",
    "section": "section 10(10)",
    },
    {
    "codename": "Leave Encashment 10(10AA)",
    "section": "10(10AA)",
    },
    {
    "codename": "Entertainment allowance",
    "section": "section 16(ii)",
    },

    {
        "codename": "Income under head other sources",
        "section": "192(2B)",
    },
    {
        "codename": "Income under bank SB",
        "section": "192(2B)",
    },
    {
        "codename": "Income under fixed deposites, NSC etc",
        "section": "192(2B)",
    },
    {
        "codename": "Other Provisions Chapter VI-A",
        "section": "Chapter VI-A",
    },

    {
    "codename": "Relief 89",
    "section": "89",
    },

    {
    "codename": "Commuted value of pension",
    "section": "section 10(10A)",
    },

]

CODENAME_EMP = [
    {
        "codename": "Value of perquisites",
        "section": "section 17(2)",
    },
    {
        "codename": "Profits in lieu of salary ",
        "section": "section 17(3)",
    },
    {
        "codename": "Salary received from other employer(s)",
        "section": "other_employer",
    },
    {
        "codename": "Income under head other sources",
        "section": "192(2B)",
    },
    {
        "codename": "Income under bank SB",
        "section": "192(2B)",
    },
    {
        "codename": "Income under fixed deposites, NSC etc",
        "section": "192(2B)",
    },
    {
        "codename": "Other Provisions Chapter VI-A",
        "section": "Chapter VI-A",
    },
]


EM_HR_MAIL = "hr@mydomain.com"

DM_HR_MAIL = "hr@mydomain.com"

REWARD_TITLES = ['Think Fresh', 'Well Done']


EM_ADDRESS = """EM Softech LLP<br>
            Unit 1:Plot No.43/ A, D Block, 2nd floor,<br>
            Cochin Special Economic Zone(CSEZ), Kakkanad, Kochi-682037, Kerala, India.<br>
            Tel:+91-484-2413280"""

DM_ADDRESS = """Digital Mesh Softech India (P) Limited <br>
            Unit 1: 43-A, E Block, 2nd Floor,<br>
            Cochin Special Economic Zone, Kakkanad, Kochi - 682 037, Kerala, India.<br>
            Tel: +91-484-4060200, Fax: +91-484-4060201"""