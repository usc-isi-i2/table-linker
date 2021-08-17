import traceback

import argparse
import sys

import tl.exceptions
import time
from tl.utility.logging import Logger
from multiprocessing import cpu_count


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
    parser.add_argument('--use-cpus', action='store', type=int,
                        dest='use_cpus', required=False, default = cpu_count(),
                        help="Number of CPUs to be used for ParallelProcessor."
                             " If unspecified, number of CPUs in system will"
                             " be used.")
    parser.add_argument('--missing-property-replacement-factor', action='store', type=float,
                        dest='missing_property_replacement_factor', default=0.25,
                        help='This factor is multiplied with the minimum similarity with which the '
                             'most significant property matched')
    parser.add_argument('--ignore-column-name', action='store',
                        dest='ignore_column_name', default="ignore",
                        help='This column is used to consider only few rows by setting to 1.')

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
        string_separator = kwargs.pop("string_separator")
        output_column_name = kwargs.pop("output_column")
        similarity_string_threshold = kwargs.pop("similarity_string_threshold")
        similarity_quantity_threshold = kwargs.pop("similarity_quantity_threshold")
        use_cpus = kwargs.pop("use_cpus")
        missing_property_replacement_factor = kwargs.pop("missing_property_replacement_factor")
        ignore_column_name = kwargs.pop("ignore_column_name")
        obj = MatchContext(input_file_path, similarity_string_threshold, similarity_quantity_threshold,
                           string_separator, missing_property_replacement_factor, ignore_column_name,
                           output_column_name, context_file_path, custom_context_file_path, use_cpus)
        start = time.time()
        result_df = obj.process_data_by_column()
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "context-match",
            "time": end-start,
        })
        result_df.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: context-match\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
