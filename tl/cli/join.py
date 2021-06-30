import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'The join command outputs the linked knowledge graph objects '
                'for an input cell. This command takes as input a Input file '
                'and a file in Ranking Score format and outputs a file in Output format.'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-c', '--ranking-score-column', action='store', type=str, dest='ranking_score_column',
                        required=True,
                        help='column name with ranking scores.')
    parser.add_argument('-f', '--original-input-file', action='store', type=str, dest='original_input_file',
                        required=True,
                        help='original file for which this pipeline is run')
    parser.add_argument('--tsv', action='store_true', dest='tsv')
    parser.add_argument('--csv', action='store_true', dest='csv')
    parser.add_argument('--extra-info', action='store_true', dest='extra_info')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.evaluation.join import Join
    import pandas as pd
    import time

    file_type = 'tsv' if kwargs['tsv'] else 'csv'
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        i_df = pd.read_csv(kwargs['original_input_file'], sep=',' if file_type == 'csv' else '\t', dtype=object)
        start = time.time()
        j = Join()
        odf = j.join(df, i_df, kwargs['ranking_score_column'], extra_info=kwargs['extra_info'])
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "join",
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: join\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
