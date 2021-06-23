import sys
import argparse
import traceback
import tl.exceptions


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
        if kwargs["logfile"]:
            with open(kwargs["logfile"],"a") as f:
                print(f'generate-reciprocal-rank-{kwargs["score_column"]}'
                      f' Time: {str(end-start)}s'
                      f' Input: {kwargs["input_file"]}',file=f)
        else:
            print(f'generate-reciprocal-rank-{kwargs["score_column"]}'
                  f' Time: {str(end-start)}s'
                  f' Input: {kwargs["input_file"]}',file=sys.stderr)
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: generate-reciprocal-rank\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
