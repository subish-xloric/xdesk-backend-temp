import sys
import traceback

class ExceptionHandler:
    """
    This class holds the method(s) get the message and stack trace of the exception
    """
    def exception(self):
        cla, exc, trbk = sys.exc_info()
        exc_name = cla.__name__
        try:
            exc_args = exc.__dict__["args"]
        except KeyError:
            exc_args = "<no args>"
        exc_tb = traceback.format_tb(trbk, 8)
        message = '%s %s %s' % (exc_name, exc_args, exc_tb)
        return message
