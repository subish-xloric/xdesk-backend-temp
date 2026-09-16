from pTracker.dataaccess.platform_access.platform_user_models import PlatformUser


class PlatformUserDA():

    def get_by_email(self, email):
        return PlatformUser.objects.filter(email__iexact=email, is_active=True).first()

    def get_by_id(self, user_id):
        return PlatformUser.objects.filter(pk=user_id).first()
