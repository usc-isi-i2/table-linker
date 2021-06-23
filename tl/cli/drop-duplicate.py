import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'Remove duplicate rows of each candidates according to specified column and keep the one with higher score on '
                'specified column or keep the one with specified search method.'
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

    parser.add_argument('--keep-method', action='store',
                        dest='keep_method', default="exact-match",
                        help="""The names of the search method need to keep. 
                        If set this, the score column will be ignored when this specified method exists. 
                        If this specified method not exists, still follow the score column order.""")


def run(**kwargs):
    from tl.features import normalize_scores
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = normalize_scores.drop_duplicate(kwargs['column'], kwargs["score_columns"], kwargs["keep_method"], df=df)
        end = time.time()
        if kwargs["logfile"]:
            with open(kwargs["logfile"],"a") as f:
                print(f'drop-duplicate-{kwargs["column"]}'
                      f' Time: {str(end-start)}s'
                      f' Input: {kwargs["input_file"]}',file=f)
        else:
            print(f'drop-duplicate-{kwargs["column"]} Time: {str(end-start)}s'
                  f' Input: {kwargs["input_file"]}',file=sys.stderr)
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: drop-duplicate\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
