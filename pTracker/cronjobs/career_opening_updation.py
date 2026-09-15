from celery import shared_task as task
from django.conf import settings
from pTracker.celery import app
from pTracker.common.utility import Utility
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.interview_da import InterviewDA

@app.task(bind=True)
def career_opening_updataion(self, career_id=0):
        objCareer = InterviewDA()
        data = {}
        openingLst = []

        try:
            if not career_id :
                result = objCareer.get_career_opened()
                for eachCareer in result:
                    openingLst.append(eachCareer.career_opening_id)
                candidates = objCareer.get_candidate_by_opening_id(openingLst)
            else:
                candidates = objCareer.get_candidate_by_opening_id(career_id)

            for candidate in candidates:
                if candidate.career_opening_id in data:
                    data[candidate.career_opening_id]["candidate_list"].append(candidate.candidate_id)
                    # data[candidate.career_opening_id]["total_interviews"] += 1
                else:
                    data[candidate.career_opening_id] = {
                        "total_interviews" : 1,
                        "no_of_acquired" : 0,
                        "no_of_short_listed" : 0,
                        "no_of_hold" : 0,
                        "candidate_list":[candidate.candidate_id]
                    }
                if candidate.candidate_status == 4:
                    data[candidate.career_opening_id]["no_of_hold"] += 1
                if candidate.candidate_status == 6:
                    data[candidate.career_opening_id]["no_of_acquired"] += 1
                if candidate.candidate_status in (5,7):
                    data[candidate.career_opening_id]["no_of_short_listed"] += 1
            if data:
                for career_opening_id, value in data.items():
                    temp_data = {}
                    # temp_data['total_interviews'] = data[career_opening_id]['total_interviews']
                    temp_data['total_interviews'] = len(data[career_opening_id]['candidate_list'])
                    temp_data['no_of_acquired'] = data[career_opening_id]['no_of_acquired']
                    temp_data['no_of_short_listed'] = data[career_opening_id]['no_of_short_listed']
                    objCareer.update_career_opening(career_opening_id,temp_data)
                    del temp_data

        except Exception as e:
            msg = "Error in the job career_opening_updataion, Error is : {0} ".format(str(e))
            Utility().log(msg)
