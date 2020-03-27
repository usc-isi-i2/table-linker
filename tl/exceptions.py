import sys


class TLException(BaseException):
    return_code = -1

    def __init__(self):
        pass


class TLExceptionHandler(object):
    def __call__(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BaseException as e:
            type, exc_val, exc_tb = sys.exc_info()
            return self.handle_exception(e, type, exc_val, exc_tb)

    def handle_exception(self, e, type, exc_val, exc_tb):
        if isinstance(e, TLException):
            return e.return_code
        return TLException.return_code


class RequiredInputParameterMissingException(Exception):
    pass


def tl_exception_handler(func, *args, **kwargs):
    exception_handler = TLExceptionHandler()
    return_code = exception_handler(func, *args, **kwargs)
    return return_code
