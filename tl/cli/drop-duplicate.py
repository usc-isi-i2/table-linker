import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'Remove duplicate rows of each candidates according to specified column and keep the one with higher score on '
                'specified column.'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=True,
                        help='column name with labels')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    parser.add_argument('--score-column', action='store', nargs='+',
                        dest='score_columns', default=[],
                        help="""The names of the column with the ranking scores as reference.""")


def run(**kwargs):
    from tl.features import normalize_scores
    import pandas as pd
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)

        odf = normalize_scores.drop_duplicate(kwargs['column'], kwargs["score_columns"], df=df)
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: drop-duplicate\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
