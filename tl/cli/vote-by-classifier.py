import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'compute voting model prediction on candidate file'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    parser.add_argument(
        '--model', action='store', dest='model',
        help='location of the trained voting model'
    )

    parser.add_argument(
        '--prob-threshold', action='store', dest='prob_threshold',
        help='classifier voting threshold of prob_1'
    )

    parser.add_argument('--features', action='store', type=str, dest='features', required=True,
                        help='A comma separated list of features used to train the --model')


def run(**kwargs):
    import pandas as pd
    from tl.features.vote_by_classifier import vote_by_classifier
    import time

    try:
        # check input file
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = vote_by_classifier(kwargs.get('features'),
                                 kwargs.get('model'),
                                 df=df,
                                 prob_threshold=kwargs.get('prob_threshold', '0'))
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "vote-by-classifier",
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except Exception as e:
        message = 'Command: vote-by-classifier\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
