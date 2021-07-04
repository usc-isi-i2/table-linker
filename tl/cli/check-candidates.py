import traceback
import argparse
import sys
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'Checks if for each cell the ground truth was retrieved'
                ' and outputs those rows for which the ground truth was never'
                ' retrieved'
    }


def add_arguments(parser):
    # input file
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'),
                        default=sys.stdin)


def run(**kwargs):
    try:
        import pandas as pd
        import time
        from tl.evaluation.check_candidates import check_candidates
        df = pd.read_csv(kwargs["input_file"])
        start = time.time()
        result_df = check_candidates(df=df)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "check-candidates",
            "time": end-start
        })
        result_df.to_csv(sys.stdout, index=False)
    except Exception:
        message = 'Command: check-candidates\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
