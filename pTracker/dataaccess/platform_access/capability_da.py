from pTracker.dataaccess.platform_access.capability_models import Capability


class CapabilityDA():

    def get_all(self):
        return Capability.objects.all().order_by('module', 'code')

    def get_by_codes(self, codes):
        return Capability.objects.filter(code__in=codes)
