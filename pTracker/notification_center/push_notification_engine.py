from pyfcm import FCMNotification

from django.conf import settings

class PushNotification():

    def __init__(self):
        self.api_key = settings.FCM_API_KEY

    def notify_single_device(self, title, msg, registration_id, sound="", extra_kwargs={}):
        return None
        push_service = FCMNotification(api_key=self.api_key)
        registration_id = registration_id
        message_title = title
        message_body = msg
        data = extra_kwargs
        collapse_key = "type_c"
        result = push_service.notify_single_device(registration_id=registration_id,\
            message_title=message_title,collapse_key=collapse_key,\
            message_body=message_body, sound=sound, data_message=data)
        return result

    def notify_multiple_device(self, title, msg, registration_ids):
        return None

        push_service = FCMNotification(api_key=self.api_key)
        registration_id = registration_ids
        message_title = title
        message_body = msg
        result = push_service.notify_multiple_devices(registration_ids=registration_ids, message_title=message_title, message_body=message_body)
        return result


