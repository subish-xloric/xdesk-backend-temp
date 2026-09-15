from datetime import timedelta, datetime

from pTracker.celery import app

from pTracker.dataaccess.ptracker_access.interview_da import InterviewDA
from pTracker.notification_center.push_notification_engine import PushNotification
from pTracker.dataaccess.ptracker_access.user_da import UserDA


@app.task(bind=True)
def send_interview_notifications(self):
    obj_da = InterviewDA()
    objUser = UserDA()
    push_obj = PushNotification()
    
    response = {'error' : '', 'success' : '', 'status' : 200}
    
    current_datetime = datetime.now()
    
    start_date_time = current_datetime + timedelta(seconds=900)
    end_date_time = current_datetime + timedelta(seconds=1800)
    
    interview_list = list()
    
    try:
        interviews = obj_da.get_interviews_of_a_time_period(start_date_time.strftime('%Y-%m-%d %H:%M:%S'),\
            end_date_time.strftime('%Y-%m-%d %H:%M:%S'))
                
        for interview in interviews:
            if "," in interview.interviewer:
                group_of_interviewers = interview.interviewer.split(",")
                interview_list.extend(list(map(lambda x: (x, interview.date_and_time), group_of_interviewers)))
                continue
            interview_list.append((interview.interviewer, interview.date_and_time))
        
        format_string = '%I:%M %p'
        
        for notify in interview_list:
            device_info = objUser.get_mobile_device_info_by_user_id(notify[0])
            user = objUser.get_user_by_id(notify[0])
            message = f"Hi {user.first_name}, You have an interview at {notify[1].strftime(format_string)}"
            if device_info:
                push_obj.notify_single_device(title="Notifications", msg=message, registration_id=device_info.device_identifier, sound=None, extra_kwargs=None)
            
        
        response['success'] = "Notifications send to all Interviewers"
        
    except Exception as e:
        response['error'] = e



