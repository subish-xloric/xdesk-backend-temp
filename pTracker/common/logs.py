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


# from sys import argv
# from fabric.api import run, env

# class RemoteDir:

#     def __init__(self) :
#         pass



#     def set_host_config(self, ip, user, password):
#         env.host_string = ip
#         env.user = user
#         env.password = password

#     def mkdir(self, folder_absolute_path):
#         """
#         creates new folder
#         """
#         run('mkdir {0}'.format(folder_absolute_path))


#     def create_folder(self):
#         #self.set_host_config('192.168.10.242', 'digitalmesh', 'password#1')
#         #self.mkdir('/home/digitalmesh/Downloads/python-securid-master/created-by-python')
#         from resume_parser import resumeparse

#         data = resumeparse.read_file('/home/subish/Downloads/ResumeSAFAAT.pdf')
#         print ('data', data)
