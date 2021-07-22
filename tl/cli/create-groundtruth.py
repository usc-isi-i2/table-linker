import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


# defined here:
# https://docs.google.com/document/d/1K4gPGAbp1nu7AtiEVLJfjdDI6xuSv4GP1z5LCno59Ik/edit#heading=h.dkiyolgxjfzp

def parser():
    return {
        'help': 'creates a ground truth file from a colorized excel file. If the file is not a .xlsx file, an exception'
                ' will be thrown'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('-e', '--evaluation-label-column', action='store', type=str, dest='evaluation_label_column',
                        default='GT',
                        help='name of the column which marks the candidate as ground truth. Default: GT')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('rb'), default=sys.stdin)


def run(**kwargs):
    from tl.utility.utility import Utility
    import pandas as pd
    import time

    evaluation_label_column = kwargs['evaluation_label_column']

    try:
        df = pd.read_excel(kwargs['input_file'])
        start = time.time()
        util = Utility()
        odf = util.create_gt_file_from_candidates(df, evaluation_label_column)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "create-groundtruth",
            "time": end - start
        })
        odf.to_csv(sys.stdout, index=False)
    except Exception:
        message = 'Command: create-groundtruth\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
