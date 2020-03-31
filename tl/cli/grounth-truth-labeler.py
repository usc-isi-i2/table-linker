import sys
import argparse


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
    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=True,
                        help='column name with ranking scores')

    parser.add_argument('-f', '--gt-file', action='store', type=str, dest='gt_file', required=True,
                        help='ground truth file path')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.evaluation import evaluation
    import pandas as pd

    df = pd.read_csv(kwargs['input_file'], dtype=object)

    odf = evaluation.ground_truth_labeler(kwargs['gt_file'], kwargs['column'], df=df)
    odf.to_csv(sys.stdout, index=False)
