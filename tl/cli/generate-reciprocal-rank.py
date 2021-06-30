import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'generates a new feature column called reciprocal rank that takes as input a score column'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    # output
    parser.add_argument('-o', '--output-column-name', action='store', dest='output_column_name',
        default="reciprocal_rank",
        help="the name of the column where the output feature will be stored.")

    parser.add_argument('-c', '--column', action='store', type=str, dest='score_column', required=True,
                        help='name of the column which has the final score used for ranking')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.features import generate_reciprocal_rank
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = generate_reciprocal_rank.generate_reciprocal_rank(kwargs['score_column'], 
                                                               kwargs['output_column_name'],
                                                               df=df)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "generate-reciprocal-rank-"+kwargs["score_column"],
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: generate-reciprocal-rank\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
