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
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.features import create_singleton_feature
    import pandas as pd
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        odf = create_singleton_feature.create_singleton_feature(df=df)
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: create-singleton-feature\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)