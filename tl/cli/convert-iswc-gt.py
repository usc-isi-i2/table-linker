import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'converts the ISWC Ground Truth file to `TL Ground Truth` file'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-d', action='store', type=str, dest='output_directory', required=True,
                        help='output directory where the files in TL GT will be created')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.utility.convert_iswc_gt import ConvertISWC
    import time

    try:
        start = time.time()
        convert_iswc_obj = ConvertISWC()
        convert_iswc_obj.convert_iswc_gt(kwargs['output_directory'])
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "convert-iswc-gt",
            "time": end-start
        })
    except:
        message = 'Command: convert-iswc-gt\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
