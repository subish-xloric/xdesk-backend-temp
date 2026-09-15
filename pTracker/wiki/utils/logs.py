from pTracker.wiki.data_access.master.logs_da import LogsDA


class Logs:

    def __log_handler(self, message, log_type):
        return LogsDA().create(message, log_type)

    def debug(self, message):
        return self.__log_handler(message, 'Debug')

    def info(self, message):
        return self.__log_handler(message, 'Info')

    def warning(self, message):
        return self.__log_handler(message, 'Warning')

    def error(self, message):
        return self.__log_handler(message, 'Error')

    def celery_error(self, message):
        return self.__log_handler(message, 'CeleryError')
