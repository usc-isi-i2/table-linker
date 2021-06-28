import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger
from tl.exceptions import UnsupportTypeError


def parser():
    return {
        'help': 'computes pseudo ground feature based on singleton feature and'
                ' context match score'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'),
                        default=sys.stdin)

    parser.add_argument('--singleton-column', type=str, action='store',
                        dest='singleton_column', required=True,
                        default='singleton',
                        help="specify column name of singleton feature. "
                             "Default is 'singleton'")

    parser.add_argument('--context-score-column', type=str, action='store',
                        dest='context_column', required=True,
                        default='context_score',
                        help="specify column name of context score feature. "
                             "Default is 'context_score'")

    parser.add_argument('--context-score-threshold', type=float,
                        action='store', required=True, default=0.7,
                        dest='context_score_threshold',
                        help="specify the threshold for context score. "
                             "Default is 0.7")

    # output column
    parser.add_argument('-o', '--output-column-name', type=str,
                        default='pseudo_gt', action='store',
                        dest='output_column',
                        help="Output column name indicating 1 if considered "
                             "as pseudo ground truth and 0 if not. Default "
                             "is 'pseudo_gt'")


def run(**kwargs):
    try:
        from tl.features.create_pseudo_gt import create_pseudo_gt
        import time
        import pandas as pd
        from tl.file_formats_validator import FFV
        ffv = FFV()
        input_file_path = kwargs["input_file"]
        singleton_column = kwargs["singleton_column"]
        context_column = kwargs["context_column"]
        context_threshold = kwargs["context_score_threshold"]
        output_column_name = kwargs["output_column"]

        df = pd.read_csv(input_file_path)
        if ffv.is_candidates_file(df):
            start = time.time()
            result_df = create_pseudo_gt(df=df,
                                         singleton_column=singleton_column,
                                         context_column=context_column,
                                         context_threshold=context_threshold,
                                         output_column=output_column_name)
            end = time.time()
            logger = Logger(kwargs["logfile"])
            logger.write_to_file(args={
                "command": "create-pseudo-gt",
                "time": end-start,
                "input_file": input_file_path
            })
            result_df.to_csv(sys.stdout, index=False)
        else:
            raise UnsupportTypeError(
                "The input file is not a candidates file!")
    except Exception:
        message = 'Command: create-pseudo-gt\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
