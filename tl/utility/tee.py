import tl.exceptions
import sys


class Tee(object):
    def __init__(self, tee_filename):
        try:
            self.tee_fil = open(tee_filename, "w")
        except IOError as ioe:
            raise tl.exceptions.TLException(" Caught IOError: {}".format(repr(ioe)))
        except Exception as e:
            raise tl.exceptions.TLException("Caught Exception: {}".format(repr(e)))

    def write(self, s):
        sys.stdout.write(s)
        self.tee_fil.write(s)

    def writeln(self, input_io):
        for each_line in input_io.readlines():
            self.write(each_line)

    def close(self):
        try:
            self.tee_fil.close()
        except IOError as ioe:
            raise tl.exceptions.TLException("Caught IOError: {}".format(repr(ioe)))
        except Exception as e:
            raise tl.exceptions.TLException("Caught Exception: {}".format(repr(e)))
