import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'returns top k candidates for each cell linking task'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-c', '--column', action='store', type=str, dest='score_column', required=True,
                        help='name of the column which has the final score used for ranking')

    parser.add_argument('-l', '--label', action='store', type=str, dest='label_column',
                        default='label',
                        help='column name with input cell labels. Default is label. '
                             'These values will be stored in the output column label in the output file for this command.')

    parser.add_argument('-k', action='store', type=int, dest='top_k',
                        default=5,
                        help='desired number of output candidates per input cell.')

    parser.add_argument('--k-rows', action='store_true', dest='k_rows', required=False,
                        default=False,
                        help='if specified, output top k candidates in different rows, rather than concatenated in a'
                             'single row')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.features import get_kg_links
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = get_kg_links.get_kg_links(kwargs['score_column'],
                                        df=df,
                                        top_k=kwargs['top_k'],
                                        label_column=kwargs['label_column'],
                                        k_rows=kwargs['k_rows'])
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "get-kg-links-"+kwargs["score_column"],
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: get-kg-links\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
