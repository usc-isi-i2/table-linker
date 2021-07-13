import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'generates a boolean features for exact match singleton'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    # output
    parser.add_argument(
        '-o', '--output-column-name', action='store', dest='output_column_name',
        default="singleton",
        help="the name of the column where the output feature will be stored.")

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.features import create_singleton_feature
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = create_singleton_feature.create_singleton_feature(kwargs['output_column_name'],
                                                                df=df)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "create-singleton-feature",
            "time": end - start
        })
        odf.to_csv(sys.stdout, index=False)
    except Exception:
        message = 'Command: create-singleton-feature\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
