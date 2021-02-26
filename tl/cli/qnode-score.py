import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'computes feature qnode-score'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.features.qnode_score import qnode_score
    import pandas as pd
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        odf = qnode_score(df)
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: qnode-score\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)