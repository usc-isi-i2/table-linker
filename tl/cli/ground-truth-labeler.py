import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'compares each candidate for the input cells with the ground truth value for that cell and '
                'adds an evaluation label'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('-f', '--gt-file', action='store', type=str, dest='gt_file', required=True,
                        help='ground truth file path')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.evaluation import evaluation
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = evaluation.ground_truth_labeler(kwargs['gt_file'], df=df)
        end = time.time()
        if kwargs["logfile"]:
            with open(kwargs["logfile"],"a") as f:
                print(f'ground-truth-labeler Time: {str(end-start)}s'
                      f' Input: {kwargs["input_file"]}',file=f)
        else:
            print(f'ground-truth-labeler Time: {str(end-start)}s'
                  f' Input: {kwargs["input_file"]}',file=sys.stderr)
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: ground-truth-labeler\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
