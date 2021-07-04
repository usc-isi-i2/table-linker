import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'drop rows base on scores of given columns'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=True,
                        help='column name with ranking scores')

    parser.add_argument('-k', action='store', type=int, dest='k', default=20,
                        help='the top k results to be keep is 20')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.features import normalize_scores
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = normalize_scores.drop_by_score(kwargs['column'], k=kwargs['k'], df=df)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "drop-by-score-"+kwargs["column"],
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: drop-by-score\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
