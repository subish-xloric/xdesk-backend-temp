from django.conf import settings

import pyodbc


""" DataBase connection Class """
class DBAccess:

    def __init__(self, dbName='default'):

        dbDtls = settings.DATABASES[dbName]

        self.__host = dbDtls['HOST']
        self.__user = dbDtls['USER']
        self.__passwd = dbDtls['PASSWORD']
        self.__db = dbDtls['NAME']
        self.dbName = dbName


    def connect(self):
        con = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=' + self.__host + ';'
            'DATABASE=' + self.__db + ';'
            'UID=' + self.__user + ';'
            'PWD=' + self.__passwd
        )
        cursor = con.cursor()
        return cursor

    def execute(self, sql, is_select=1, fetch_all=1):
        result_set = None
        error = None
        try:
            cursor = self.connect()
            cursor.execute(sql)
            if is_select == 1 and fetch_all == 1:
                result_set = cursor.fetchall()
            elif is_select == 1 and fetch_all == 0:
                result_set = cursor.fetchone()
            cursor.close()
        except Exception as e:
            error = str(e)
        finally:
            return result_set, error
