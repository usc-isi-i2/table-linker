import sys
import threading
import logging
_logger = logging.getLogger(__name__)


class Timeout(Exception):
    """function run timeout"""


class KThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.killed = False

    def start(self):
        """Start the thread."""
        self.__run_backup = self.run
        # Force the Thread to install our trace.
        self.run = self.__run
        threading.Thread.start(self)

    def __run(self):
        """Hacked run function, which installs the trace."""
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, why, arg):
        if why == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True


def timeout_call(timeout, func, args=(), kwargs=None, try_except=False):
    def new_func(oldfunc, result, oldfunc_args, oldfunc_kwargs):
            result.append(oldfunc(*oldfunc_args, **oldfunc_kwargs))

    result = []
    kwargs = {} if kwargs is None else kwargs
    # create new args for _new_func, because we want to get the func
    # return val to result list
    new_kwargs = {
        'oldfunc': func,
        'result': result,
        'oldfunc_args': args,
        'oldfunc_kwargs': kwargs
    }

    thd = KThread(target=new_func, args=(), kwargs=new_kwargs)
    thd.start()
    thd.join(timeout)
    # timeout or finished?
    is_alive = thd.isAlive()
    thd.kill()

    if is_alive:
        if try_except is True:
            raise Timeout("{} Timeout: {} seconds.".format(func, timeout))
        _logger.error("Timeout: {} seconds.".format(timeout))
        return None
    else:
        return result[0]
