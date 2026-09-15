from django.conf import settings
from django.db import connections
from django.db import transaction

import pyodbc


class Connection:

    def __init__(self, db_name='default'):
        db_dtls = settings.DATABASES[db_name]
        self.__host = db_dtls['HOST']
        self.__user = db_dtls['USER']
        self.__passwd = db_dtls['PASSWORD']
        self.__db = db_dtls['NAME']
        self.db_name = db_name
        self.__engine = db_dtls['ENGINE']

    def sql_server_cursor(self):
        con = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=' + self.__host + ';'
            'DATABASE=' + self.__db + ';'
            'UID=' + self.__user + ';'
            'PWD=' + self.__passwd
        )
        return con.cursor()

    def mysql_cursor(self):
        return connections[self.db_name].cursor()


    def mssql_write(self, sql, **options):
        error = None
        result_set = None
        try:
            with transaction.atomic(using=self.db_name):
                con = pyodbc.connect(
                    'DRIVER={ODBC Driver 17 for SQL Server};'
                    'SERVER=' + self.__host + ';'
                    'DATABASE=' + self.__db + ';'
                    'UID=' + self.__user + ';'
                    'PWD=' + self.__passwd
                )
                cursor = con.cursor()

                if ('params' in options
                        and options['params'] is not None
                        and isinstance(options['params'], list)):
                    cursor.execute(sql, options['params'])
                else:
                    cursor.execute(sql)

                con.commit()
                result_set = row = cursor.fetchone()
                cursor.close()
        except Exception as err:
            error = err
        return result_set, error


    def execute(self, sql, is_select=1, fetch_all=1, **options):
        error = None
        result_set = None
        try:
            with transaction.atomic(using=self.db_name):
                if self.__engine == 'mssql':
                    cursor = self.sql_server_cursor()
                else:
                    cursor = self.mysql_cursor()

                if ('params' in options
                        and options['params'] is not None
                        and isinstance(options['params'], list)):
                    cursor.execute(sql, options['params'])
                else:
                    cursor.execute(sql)

                if is_select == 1 and fetch_all == 1:
                    result_set = cursor.fetchall()
                elif is_select == 1 and fetch_all == 0:
                    result_set = cursor.fetchone()
                cursor.close()
        except Exception as err:
            error = err
        return result_set, error