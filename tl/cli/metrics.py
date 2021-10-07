import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'computes the precision, recall and f1 score for the tl pipeline'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=True,
                        help='column name with ranking scores')

    parser.add_argument('-k', action='store', type=int, dest='k', default=1,
                        help='calculate recall at top k, can send multiple values in one time, default is 1')

    parser.add_argument('--tag', action='store', type=str, dest='tag', default='',
                        help='a tag to use in the output file to identify the results of running the given pipeline')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.evaluation import evaluation
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = evaluation.metrics(kwargs['column'], k=kwargs['k'], df=df, tag=kwargs['tag'])
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "metrics",
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: metrics\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
