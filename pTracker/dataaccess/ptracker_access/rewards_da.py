from  datetime import datetime, date, timedelta
from types import SimpleNamespace

from django.conf import settings
from django.db.models import query
from django.db.models import Q


from pTracker.dataaccess.ptracker_access.rewards_models import RewardType
from pTracker.dataaccess.ptracker_access.rewards_models import Reward
from pTracker.dataaccess.ptracker_access.rewards_models import RewardApprover
from pTracker.dataaccess.ptracker_access.rewards_models import RewardComments
from pTracker.dataaccess.ptracker_access.rewards_models import Criteria
from pTracker.dataaccess.ptracker_access.rewards_models import RewardCriteria
from pTracker.dataaccess.ptracker_access.rewards_models import TvNotification
from pTracker.dataaccess.ptracker_access.rewards_models import TvNotificationDetails




def new_dto():
    dto = SimpleNamespace()
    return dto

class RewardsDA():

    def __init__(self):
        pass

    def create_reward(self, reward_dict):
        return Reward.objects.create(**reward_dict)

    def update_reward(self,reward_id, reward_dict):
        return Reward.objects.filter(id =reward_id).update(**reward_dict)

    def create_reward_approver(self, reward_approver_dict):
        return RewardApprover.objects.create(**reward_approver_dict)

    def update_reward_approver(self,user_id,reward_id,reward_approver_dict):
        return RewardApprover.objects.filter(reward_id= reward_id,approver_id = user_id ).update(**reward_approver_dict)

    def get_reward_type_by_id(self, id):
        return RewardType.objects.filter(id=id,is_deleted = 0).first()

    def get_reward_by_id(self, reward_id):
        return Reward.objects.filter(id=reward_id, is_deleted = 0).first()

    def get_reward_approvers(self,reward_id):
        return RewardApprover.objects.filter(reward_id = reward_id)

    def get_reward_approvers_by_approver(self,approver):
        return RewardApprover.objects.filter(approver_id = approver)

    def get_all_reward_types(self, type_id=0):
        result = RewardType.objects.filter(is_deleted=0)
        if type_id:
            result = result.filter(id=type_id)
        return result

    def get_all_rewards(self, status=0, start_date=0, end_date=0, reward_type=0, emp_id=0):
        result = Reward.objects.filter(is_deleted=0).order_by('-id')
        if status:
            result = result.filter(status=status)
        if reward_type:
            result = result.filter(reward_type__id=reward_type)
        if isinstance(emp_id, list) and emp_id:
            result = result.filter(receiving_emp_id__in=emp_id)
        elif emp_id:
            result = result.filter(receiving_emp_id=emp_id)
        return result

    def get_all_my_rewards(self, emp_id, start_date=0, end_date=0, status=0):
        rewards = Reward.objects.filter(is_deleted=0, receiving_emp_id=emp_id).order_by('-id')
        if start_date:
            rewards = rewards.filter(created_date__date__gte=start_date)
        if end_date:
            rewards = rewards.filter(created_date__date__lte=end_date)
        if status:
            rewards = rewards.filter(status=status)
        return rewards

    def get_all_rewards_by_team_member_ids(self, team_members =[], reward_ids=[]):
        return Reward.objects.filter(is_deleted=0).\
            filter(Q(nominated_by__in=team_members)|Q(id__in=reward_ids)).order_by('-id')

    def create_reward_comment(self, data_dict={}):
        return RewardComments.objects.create(**data_dict)

    def get_reward_comments(self, reward_id):
        return RewardComments.objects.filter(reward_id=reward_id).order_by('-id')

    def get_master_criterias(self, type_id):
        return Criteria.objects.filter(reward_type_id=type_id)

    def create_reward_criterias(self, criteria_dict):
        return RewardCriteria.objects.create(**criteria_dict)

    def get_rewards_by_approver_id(self, approver_id):
        return RewardApprover.objects.filter(approver_id=approver_id)

    def get_reward_criteria(self, reward_id):
        return RewardCriteria.objects.filter(reward__id=reward_id)

    def get_notifications(self, notification_date):
        notifications = TvNotification.objects.filter(start_date__lte=notification_date, end_date__gte=notification_date, is_deleted=0)
        return notifications

    def get_notification_details(self, notification_id):
        notifications = TvNotificationDetails.objects.filter(notification__id=notification_id)
        return notifications

    def create_tv_notifications(self, notify_dict):
        return TvNotification.objects.create(**notify_dict)

    def create_tv_notification_details(self, notify_dict):
        return TvNotificationDetails.objects.create(**notify_dict)

    def get_notifications_by_type(self, year, type=None):
        notifications = TvNotification.objects.filter(start_date__year=year, is_deleted=0,type=type).order_by('-id')
        return notifications

    def get_notifications_by_start_date(self, start_date, type=None):
        notifications = TvNotification.objects.filter(start_date__gte=start_date, is_deleted=0,type=type).order_by('-id')
        return notifications

    def update_notices(self, notice_id, data_dict={}):
        notifications = TvNotification.objects.filter(id=notice_id).update(**data_dict)
        return notifications

    def get_notice_by_id(self, notice_id):
        return TvNotification.objects.filter(id=notice_id).last()

    def delete_details_by_notification_id(self, notice_id):
        return TvNotificationDetails.objects.filter(notification__id=notice_id).delete()

    def get_notifications_by_type_list(self, year, type=[]):
        notifications = TvNotification.objects.filter(start_date__year=year, is_deleted=0,type__in=type).order_by('-id')
        return notifications

