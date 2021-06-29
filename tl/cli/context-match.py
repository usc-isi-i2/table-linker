import traceback

import argparse
import sys

import tl.exceptions


def parser():
    return {
        'help': 'Match the context values to the properties and add the score of the match.'
    }


def add_arguments(parser):
    # input file
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('--context-file', type=str, dest='context_file', required=False,
                        help="The file is used to look up context values for matching.")
    parser.add_argument('--debug', action='store_true',
                        help="if set, an kgtk debug logger will be saved at home directory. "
                             "Debug adds two new columns to the output denoting the properties matched and the "
                             "respective similarities.")
    parser.add_argument('--similarity-string-threshold', action='store', type=float, dest='similarity_string_threshold',
                        default=0.75,
                        help='The minimum threshold for similarity with input context for string matching. '
                             'Default: 0.75')
    parser.add_argument('--similarity-quantity-threshold', action='store', type=float,
                        dest='similarity_quantity_threshold', default=0.85,
                        help='The minimum threshold for similarity with input context for quantity matching. '
                             'Default: 0.85')
    parser.add_argument('--custom-context-file', type=str, dest='custom_context_file', required=False,
                        help="The file is used to look up context values for matching.") 
    parser.add_argument('--string-separator', action = 'store', type=str, dest = 'string_separator', default = ",", 
                        help = "Any separators to separate from in the context substrings.")

    # output
    parser.add_argument('-o', '--output-column-name', action='store', dest='output_column', default="context_score",
                        help='The output column is the named column of the score for the matches '
                             'computed for the context.')


def run(**kwargs):
    try:
        from tl.features.context_match import MatchContext
        input_file_path = kwargs.pop("input_file")
        context_file_path = kwargs.pop("context_file")
        custom_context_file_path = kwargs.pop("custom_context_file")
        obj = MatchContext(input_file_path, kwargs, context_file_path, custom_context_file_path)
        result_df = obj.process_data_by_column()
        result_df.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: context-match\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
