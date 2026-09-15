from datetime import date, timedelta
from types import SimpleNamespace

from celery import shared_task as task
from django.conf import settings

from pTracker.celery import app
from pTracker.common.utility import Utility
from pTracker.api.timesheet.timesheet_report_biz import TimesheetReportBL
from pTracker.notification_center.email_engine import Email
from pTracker.user_management.employee import Employee

def new_dto():
    dto = SimpleNamespace()
    return dto

@app.task(bind=True)
def create_monthly_missing_time_sheet_report(self):

    try:
        end_date = date.today().replace(day=1) - timedelta(days=1)
        start_date = date.today().replace(day=1) - timedelta(days=end_date.day)
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")
        print('start_date', start_date)
        print('end_date', end_date)
        result = TimesheetReportBL().get_timesheet_summary(2, start_date, end_date, 0)

        red_list = []
        blue_list = []
        green_list = []

        for each_item in result:
            if each_item.get('missing_per', 0) >= 25:
                red_list.append(each_item)
            elif each_item.get('missing_per', 0) >= 10:
                blue_list.append(each_item)
            else:
                green_list.append(each_item)

        if red_list:
            red_list = sorted(red_list, key = lambda i: (i['missing_cnt'], i['user']))
            red_list.reverse()
        if blue_list:
            blue_list = sorted(blue_list, key = lambda i: (i['missing_cnt'], i['user']))
            blue_list.reverse()
        if green_list:
            green_list = sorted(green_list, key = lambda i: (i['missing_cnt'], i['user']))
            green_list.reverse()

        html = generate_html(red_list, blue_list, green_list)

        end_date = date.today().replace(day=1) - timedelta(days=1)
        end_date = end_date.strftime("%B %Y")

        subject = "Time Sheet Missing Report, {0}  ".format(end_date)
        mail_dto = new_dto()
        mail_dto.subject = subject
        mail_dto.from_address = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto.body = html
        mail_dto.to_addresses = Employee().get_missing_time_sheet_email_recipient()
        mail_dto.smtp_username = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto.smtp_password = settings.EMAIL_ADDRESS['do_not_reply']['password']
        print('start_date', mail_dto.smtp_username)
        print('end_date', mail_dto.smtp_password)
        Email().send_html_mail(mail_dto)

    except Exception as e:
        msg = "Error in the job create_monthly_missing_time_sheet_report, Error is : {0} ".format(str(e))
        print( 'msg', msg)
        Utility().log(msg)


def generate_html(red_list, blue_list, green_list):

    try:
        html = get_html_header()
        if red_list:
            html = html + get_red_table()
            row_html = get_data_raw(red_list)
            html = html + row_html + """</div>"""

        if blue_list:
            html = html + get_blue_table()
            row_html = get_data_raw(blue_list)
            html = html + row_html + """</div>"""

        if green_list:
            html = html + get_green_table()
            row_html = get_data_raw(green_list)
            html = html + row_html + """</div>"""

        html = html + """</div></body></html>"""
        return html

    except Exception as e:
        msg = "Error in the job generate_html, Error is : {0} ".format(str(e))
        Utility().log(msg)

def get_html_header():
    html = """
    <html lang="en">
    <head>
    <style>
    body {
    font-family: "Helvetica Neue", Helvetica, Arial;
    font-size: 14px;
    line-height: 20px;
    font-weight: 400;
    color: #3b3b3b;
    -webkit-font-smoothing: antialiased;
    font-smoothing: antialiased;
    background: #2b2b2b;
    }
    @media screen and (max-width: 580px) {
    body {
        font-size: 16px;
        line-height: 22px;
    }
    }

    .wrapper {
    margin: 0 auto;
    padding: 40px;
    max-width: 800px;
    }

    .table {
    margin: 0 0 40px 0;
    width: 100%;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    display: table;
    }
    @media screen and (max-width: 580px) {
    .table {
        display: block;
    }
    }

    .row {
    display: table-row;
    background: #f6f6f6;
    }
    .row:nth-of-type(odd) {
    background: #e9e9e9;
    }
    .row.header {
    font-weight: 900;
    color: #ffffff;
    background: #ea6153;
    }
    .row.green {
    background: #27ae60;
    }
    .row.blue {
    background: #2980b9;
    }
    @media screen and (max-width: 580px) {
    .row {
        padding: 14px 0 7px;
        display: block;
    }
    .row.header {
        padding: 0;
        height: 6px;
    }
    .row.header .cell {
        display: none;
    }
    .row .cell {
        margin-bottom: 10px;
    }
    .row .cell:before {
        margin-bottom: 3px;
        content: attr(data-title);
        min-width: 98px;
        font-size: 10px;
        line-height: 10px;
        font-weight: bold;
        text-transform: uppercase;
        color: #969696;
        display: block;
    }
    }

    .cell {
    padding: 6px 12px;
    display: table-cell;
    }
    @media screen and (max-width: 580px) {
    .cell {
        padding: 2px 16px;
        display: block;
    }
    }
    </style>
    </head>

    <body translate="no">
    <div class="wrapper">
    """
    return html

def get_row_header():
    html = """
    <div class="cell">
        Name
      </div>
      <div class="cell">
        Missing %
      </div>
      <div class="cell">
        #Missing
      </div>
      <div class="cell">
        #Submitted
      </div>
      <div class="cell">
        Approved %
      </div>
    """
    return html

def get_red_table():
    html = """<div class="table"><div class="row header">"""
    header = get_row_header()
    html = html + header + """</div>"""
    return html

def get_blue_table():
    html = """<div class="table"><div class="row header blue">"""
    header = get_row_header()
    html = html + header + """</div>"""
    return html

def get_green_table():
    html = """<div class="table"><div class="row header green">"""
    header = get_row_header()
    html = html + header + """</div>"""
    return html

def get_data_raw(data_list):
    row_html = ''
    for each_item in data_list:
        name = each_item["user"]
        missing_per = each_item["missing_per"]
        submitted_cnt = each_item["submitted_cnt"]
        missing_cnt = each_item["missing_cnt"]
        approved_per = each_item["approved_per"]
        temp_html = """
        <div class="row">
        <div class="cell">{0}</div>
        <div class="cell">{1}</div>
        <div class="cell">{3}</div>
        <div class="cell">{2}</div>
        <div class="cell">{4}</div>
        </div>""".format(name, missing_per, submitted_cnt, missing_cnt, approved_per)

        row_html = row_html + temp_html
        del temp_html
    return row_html



