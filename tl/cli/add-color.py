import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'Transform the output to xlsx file and add color to specific rows, it can only run as the last step'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-c', '--column', action='store', type=str, dest='column',
                        help='column name need to be colored, can have multiple columns.')

    parser.add_argument('-k', action='store', type=int, dest='k', default=5,
                        help='the top k results to be colored is 20')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    parser.add_argument('--all-columns', action='store_true', dest='use_all_columns',
                        help='if set with this flag, `-c` option will have no effect and all numeric '
                             'columns will be colored.')

    parser.add_argument('--sort-by-ground-truth', action='store_true', dest='sort_by_gt',
                        help="Only works with the file after running with `ground-truth-labeler`. "
                             "If set, it will always put the ground truth row on first of each (column, row) "
                             "pair candidates")

    parser.add_argument('--ground-truth-score-column', action='store', dest='gt_score_column',
                        default=None,
                        help="The embedding vector score achieved by running with `add-text-embedding-feature` function"
                             " and `ground-truth` column-vector-strategy, only necessary for running with "
                             "`sort-by-ground-truth` "
                             "option.")

    parser.add_argument('--output', action='store', dest='output_uri',
                        default=None,
                        help="The output path to store the output xlsx file.")


def run(**kwargs):
    from tl.features.add_color import ColorRenderUnit
    import pandas as pd
    import time

    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        columns = kwargs['column'].strip().split(",")
        color_render = ColorRenderUnit(df, kwargs["sort_by_gt"], kwargs["gt_score_column"], kwargs["output_uri"])
        color_render.add_color_by_score(columns, k=kwargs['k'], use_all_columns=kwargs["use_all_columns"])
        color_render.add_border()
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "add-color",
            "time": end-start,
        })
        color_render.save_to_file()

    except:
        message = 'Command: add color\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
