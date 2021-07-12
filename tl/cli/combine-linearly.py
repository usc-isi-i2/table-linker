import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'linearly combines two or more score-columns for candidate knowledge graph objects '
                'for each input cell value'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-w', '--weights', action='store', type=str, dest='weights', required=True,
                        help='a comma separated string, in the format '
                             '<score-column-1>:<weight-1>,<score-column-2>:<weight-2>,... '
                             'representing weights for each score-column. '
                             'Default weight for each score-column is 1.0')

    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column',
                        default='ranking_score',
                        help=' the output column name where the linearly combined scores will be stored. '
                             'Default is ranking_score')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.candidate_ranking import combine_linearly
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = combine_linearly.combine_linearly(weights=kwargs['weights'], output_column=kwargs['output_column'], df=df)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "combine-linearly",
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: combine-linearly\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
