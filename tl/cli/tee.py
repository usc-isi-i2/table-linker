import argparse
import sys
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'wrap of Linux `tee` function for internal pipeline.'
    }


def add_arguments(parser):
    # input file
    parser.add_argument('input', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('--output', action='store', nargs='?', dest='output_file_path',
                        default="", help="the output file path")


def run(**kwargs):
    try:
        from tl.utility.tee import Tee
        import time
        start = time.time()
        tee = Tee(kwargs.get("output_file_path"))
        input_content = kwargs.get("input")
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "tee",
            "time": end-start
        })
        tee.writeln(input_content)
    except:
        message = 'Command: tee\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
