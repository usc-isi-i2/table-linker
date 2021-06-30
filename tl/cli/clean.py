import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'cleans the cell values in a column, creating a new column with the clean values.'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=True,
                        help='the column to be cleaned')

    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column', default=None,
                        help='the name of the column where cleaned column values are stored. If not provided, the name '
                             'of the new column is the name of the input column with the suffix _clean')

    parser.add_argument('--symbols', action='store', type=str, dest='symbols', default='!@#$%^&*()+={}[]:;’\”/<>',
                        help="""'a string containing the set of characters to be removed, default is “!@#$%%^&*()+={}[]:;’\”/<>”'""")

    parser.add_argument('--replace-by-space', action='store', type=str, dest='replace_by_space', default='yes',
                        help='replace all instances of the symbols a space, delete otherwise')

    parser.add_argument('--keep-original', action='store', type=str, dest='keep_original', default='no',
                        help='if specified, the output column will contain the original value and the clean value'
                             'will be appended, separated by |')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.preprocess import preprocess
    import pandas as pd
    import time

    keep_original = kwargs['keep_original'].lower().strip() != 'no'
    replace_by_space = kwargs['replace_by_space'].lower().strip() == 'yes'

    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = preprocess.clean(kwargs['column'], output_column=kwargs['output_column'], df=df,
                               symbols=kwargs['symbols'],
                               keep_original=keep_original,
                               replace_by_space=replace_by_space)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "clean",
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: clean\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
