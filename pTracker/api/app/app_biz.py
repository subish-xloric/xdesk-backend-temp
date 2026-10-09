from django.conf import settings


class AppBL():

    def get_version_status(self, app_version, device_type):
        """ Latest app version for the device (anything but Android is treated
        as iOS) and whether the caller's App-Version is behind it. A missing or
        unparseable App-Version never reports an update. """
        platform = 'ANDROID' if device_type.upper() == 'ANDROID' else 'IOS'
        config = settings.APP_VERSIONS[platform]
        latest_version = config['latest_version']

        current = self.__parse_version(app_version)
        latest = self.__parse_version(latest_version)
        minimum = self.__parse_version(config['min_version'])

        is_update_available = bool(current and latest and current < latest)
        is_force_update = bool(current and minimum and current < minimum)

        return {
            "isUpdateAvailable": is_update_available,
            "isForceUpdate": is_force_update,
            "releaseNote": config['release_note'],
            "newVersion": latest_version,
        }

    def __parse_version(self, version):
        """ "1.2.10" -> (1, 2, 10), padded to three parts so "1.2" == "1.2.0";
        None when empty or not purely numeric. """
        parts = (version or '').strip().split('.')
        if not all(part.isdigit() for part in parts):
            return None
        numbers = [int(part) for part in parts]
        return tuple(numbers + [0] * (3 - len(numbers)))
