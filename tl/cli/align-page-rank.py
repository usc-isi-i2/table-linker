import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'computes page rank feature only to exact match candidiates'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    import pandas as pd
    from tl.features.align_page_rank import align_page_rank
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)

        odf = align_page_rank(df=df)

        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: align-page-rank\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
