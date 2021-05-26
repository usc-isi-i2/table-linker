import typing
import argparse
import sys
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'Match the context values to the properties and add the score of the match.'
    }


def add_arguments(parser):
    from tl.utility.utility import Utility
    from kgtk.cli.text_embedding import ALL_EMBEDDING_MODELS_NAMES
    # input file
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    # debug
    parser.add_argument('context_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('--debug', action='store_true', help="if set, an kgtk debug logger will be saved at home directory. Debug adds two new columns to the output denoting the properties matched and the respective similarities.")
    parser.add_argument('--sim_string', action='store', type=float, dest='sim_string', default=0.75,
                        help='The minimum threshold for similarity with input context for string matching.')
    parser.add_argument('--sim_quantity', action='store', type=float, dest='sim_quantity', default=0.85,
                        help='The minimum threshold for similarity with input context for quantity matching.')

    # output
    parser.add_argument('-o', '--output-column-name', action='store', dest='output_column', default = "context_score",
                        help='The output column is the named column of the score for the matches computed for the context.')

def run(**kwargs):
    try:
        from tl.features.context_match import match
        input_file_path = kwargs.pop("input_file")
        context_file_path = kwargs.pop("context_file")
        obj = match(input_file_path, context_file_path, kwargs)
        obj.divide_by_column()
    except:
        message = 'Command: context_matching\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
