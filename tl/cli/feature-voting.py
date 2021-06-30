import sys
import traceback
import argparse

from tl.exceptions import TLException
from tl.utility.logging import Logger


def parser():
    return {
        'help': """
        Tabulates votes for candidates using features specified. Example features include: 
        1. page rank top 1
        2. qnode with smallest number
        3. Monge Elkan distance
        4. Jaccard between description and row cell content
        """
    }


def add_arguments(parser):
    # input file
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    # Features used in voting
    parser.add_argument(
        '-c', '--input-column-names', action='store', dest='input_column_names',
        default='qnode_score',
        help="the column name of features to use in voting, separated by ','"
    )


def run(**kwargs):
    try:
        import pandas as pd
        from tl.features.feature_voting import feature_voting
        import time
        input_file_path = kwargs.pop("input_file")
        input_column_names = kwargs.pop("input_column_names")
        df = pd.read_csv(input_file_path)
        start = time.time()
        feature_col_names = input_column_names.split(',')

        odf = feature_voting(feature_col_names, df)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "feature-voting",
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)

    except:
        message = 'Command: feature-voting\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise TLException(message)
