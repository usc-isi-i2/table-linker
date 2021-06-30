import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger
from tl.exceptions import UnsupportTypeError


def parser():
    return {
        'help': 'computes pseudo ground feature based on specified columns and'
                ' thresholds'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'),
                        default=sys.stdin)

    parser.add_argument('--column-thresholds', type=str, action='store',
                        dest='column_thresholds',
                        help="string specifying the columns to be used along "
                             "with corresponding thresholds; column:threshold"
                             "; multiple features can be specified "
                             "by separating with a comma.")

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
        column_thresholds = [(_.split(":")[0], float(_.split(":")[1]))
                             for _ in kwargs["column_thresholds"].split(",")]
        output_column_name = kwargs["output_column"]

        df = pd.read_csv(input_file_path)
        if ffv.is_candidates_file(df):
            start = time.time()
            result_df = create_pseudo_gt(df=df,
                                         column_thresholds=column_thresholds,
                                         output_column=output_column_name)
            end = time.time()
            logger = Logger(kwargs["logfile"])
            logger.write_to_file(args={
                "command": "create-pseudo-gt",
                "time": end-start
            })
            result_df.to_csv(sys.stdout, index=False)
        else:
            raise UnsupportTypeError(
                "The input file is not a candidates file!")
    except Exception:
        message = 'Command: create-pseudo-gt\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
