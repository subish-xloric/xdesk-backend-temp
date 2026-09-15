from pTracker.dataaccess.ptracker_access.models import DailyAttendance
from pTracker.common.utility import Utility

from pTracker.dataaccess.db import Connection


class AttendanceDA:

    def cretate_emp_access_log(self, dto):
        str_sql = """INSERT INTO Att
        (EmployeeCode, LogDate, Direction, DeviceSerialNo, DeviceSName)
        VALUES ('{0}','{1}','{2}','{3}','{4}')
        """.format(dto.emp_code, dto.log_date, dto.direction, dto.device_serial_no, dto.device_name)
        conn = Connection('essl_db')
        results, error = conn.mssql_write(str_sql)

    def get_emp_access_log(self, emp_code, str_date, end_date):
        str_sql = """SELECT EmployeeCode, LogDate, Direction, DeviceSerialNo
        FROM Att
        WHERE EmployeeCode = '{0}'
        AND LogDate >= '{1} 00:00:00' AND LogDate <= '{2} 23:59:59'
        ORDER BY LogDate""".format(emp_code, str_date, end_date)
        conn = Connection('essl_db')
        results, error = conn.execute(str_sql)
        if error:
            results = None
            Utility().log(error)
        return results

    def get_emp_last_access_log(self, emp_code, str_date):
        str_sql = """SELECT EmployeeCode, LogDate, Direction, DeviceSerialNo
        FROM Att
        WHERE EmployeeCode = '{0}'
        AND LogDate >= '{1} 00:00:00' AND LogDate <= '{1} 23:59:59'
        ORDER BY LogDate desc""".format(emp_code, str_date)
        conn = Connection('essl_db')

        results, error = conn.execute(str_sql)
        if results:
            return results[0]
        if error:
            results = None
            Utility().log(error)
        return results

    def get_emp_attendance_log(self, emp_code, str_date, end_date):
        str_sql = """SELECT attendance_date, work_hours, arrival
        FROM daily_attendance
        WHERE emp_code = {0}
        AND attendance_date >= '{1}' AND attendance_date <= '{2}'
        ORDER BY attendance_date""".format(emp_code, str_date, end_date)
        conn = Connection('default')
        results, error = conn.execute(str_sql)
        if error:
            results = None
            Utility().log(error)
        return results

    def get_wfh_employees(self, str_date):
        str_sql = """SELECT EmployeeCode
        FROM Att
        WHERE
        DeviceSName = 'Web IN'
        AND Direction='in'
        AND LogDate >= '{0} 00:00:00'
        AND LogDate <= '{0} 23:59:59' ORDER BY LogDate """.format(str_date)
        conn = Connection('essl_db')


        results, error = conn.execute(str_sql)

        return results

    def get_attendance_details_by_date(self, str_date, end_date):
        str_sql = """SELECT EmployeeCode, DeviceSName, LogDate
        FROM Att
        WHERE
        Direction='in'
        AND LogDate >= '{0} 00:00:00'
        AND LogDate <= '{1} 23:59:59' ORDER BY LogDate """.format(str_date, end_date)
        conn = Connection('essl_db')
        return conn.execute(str_sql)

    def get_logout_details_by_date(self, str_date, end_date):
        str_sql = """SELECT EmployeeCode, DeviceSName, LogDate
        FROM Att
        WHERE
        Direction='out'
        AND LogDate >= '{0} 00:00:00'
        AND LogDate <= '{1} 23:59:59' ORDER BY LogDate desc""".format(str_date, end_date)
        conn = Connection('essl_db')
        return conn.execute(str_sql)

    def get_punch_details_by_emp_code(self, emp_code, str_date, end_date):
        str_sql = """SELECT Direction, DeviceSName, LogDate
        FROM Att
        WHERE
        EmployeeCode='{0}'
        AND LogDate >= '{1} 00:00:00'
        AND LogDate <= '{2} 23:59:59' ORDER BY LogDate""".format(emp_code, str_date, end_date)
        conn = Connection('essl_db')
        return conn.execute(str_sql)

    def get_essl_attendance_by_emp_code(self, emp_code, str_date, end_date):
        str_sql = """ SELECT  distinct CONVERT(date, LogDate) LogDate
        FROM Att
        WHERE EmployeeCode = '{0}'
        AND LogDate >= '{1} 00:00:00'
        AND LogDate <= '{2} 23:59:59'
        ORDER BY LogDate DESC""".format(emp_code, str_date, end_date)
        conn = Connection('essl_db')
        return conn.execute(str_sql)
