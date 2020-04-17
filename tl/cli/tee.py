import argparse
import sys
import traceback
import tl.exceptions


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


def parser():
    return {
        'help': 'wrap of Linux `tee` function for internal pipeline.'
    }

def add_arguments(parser):
    # input file
    parser.add_argument('input', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('-o', '--output', action='store', nargs='?', dest='output_file_path',
                        default="", help="the output file path")

def run(**kwargs):
    try:
        tee = Tee(kwargs.get("output_file_path"))
        input_content = kwargs.get("input")
        tee.writeln(input_content)
    except:
        message = 'Command: clean\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)