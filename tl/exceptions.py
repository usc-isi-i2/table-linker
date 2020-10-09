import sys
import warnings


class TLException(BaseException):
    return_code = -1
    message = "TLException found\n"

    def __init__(self, message):
        self.message = message


class TLArgumentParseException(TLException):
    return_code = 2


class TLExceptionHandler(object):
    def __call__(self, func, *args, **kwargs):
        try:
            return_code = func(*args, **kwargs) or 0
            if return_code != 0:
                warnings.warn('Please raise exception instead of returning non-zero value')
            return return_code
        except BaseException as e:
            type, exc_val, exc_tb = sys.exc_info()
            return self.handle_exception(e, type, exc_val, exc_tb)

    def handle_exception(self, e, etype, exc_val, exc_tb):
        if isinstance(e, TLException):
            sys.stderr.write(e.message)
            return e.return_code

        warnings.warn('Please raise TLException instead of {}'.format(etype))
        sys.stderr.write(TLException.message)
        return TLException.return_code


class RequiredInputParameterMissingException(Exception):
    pass


class RequiredColumnMissingException(Exception):
    pass


class UnsupportTypeError(Exception):
    pass


class FileNotExistError(Exception):
    pass


class ZeroScoreError(Exception):
    pass


class UploadError(Exception):
    pass


def tl_exception_handler(func, *args, **kwargs):
    exception_handler = TLExceptionHandler()
    return_code = exception_handler(func, *args, **kwargs)
    return return_code
