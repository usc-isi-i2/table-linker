import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


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
                             "by separating with a comma."
                             " Eg: gt_score:median,singleton:1")

    parser.add_argument('--filter', type=str, action='store',
                        dest='filter', required=False, default=None,
                        help="string specifying the columns and the values to"
                             " be used to filter the dataframe")

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
        input_file_path = kwargs["input_file"]
        column_thresholds = kwargs["column_thresholds"]
        output_column_name = kwargs["output_column"]
        filter = kwargs["filter"]

        df = pd.read_csv(input_file_path)
        start = time.time()
        result_df = create_pseudo_gt(df=df,
                                     column_thresholds=column_thresholds,
                                     output_column=output_column_name,
                                     filter=filter)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "create-pseudo-gt",
            "time": end-start
        })
        result_df.to_csv(sys.stdout, index=False)
    except Exception:
        message = 'Command: create-pseudo-gt\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
