import sys
import argparse
import traceback
import tl.exceptions


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


def run(**kwargs):
    import pandas as pd
    from tl.features.vote_by_classifier import vote_by_classifier
    import time

    try:
        # check input file
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = vote_by_classifier(kwargs.get('model'),
                                 df=df,
                                 prob_threshold=kwargs.get('prob_threshold', '0'))
        end = time.time()
        if kwargs["logfile"]:
            with open(kwargs["logfile"],"a") as f:
                print(f'vote-by-classifier Time: {str(end-start)}s'
                      f' Input: {kwargs["input_file"]}',file=f)
        else:
            print(f'vote-by-classifier Time: {str(end-start)}s'
                  f' Input: {kwargs["input_file"]}',file=sys.stderr)
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: vote-by-classifier\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
