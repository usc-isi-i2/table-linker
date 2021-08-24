import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'Use different string similarity functions to calculate the string similarity scores'
                'between the retrieved candidates labels and given labels.'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    parser.add_argument('-i', action='store_true', dest='ignore_case',
                        help='ignore case, default is case sensitive')

    parser.add_argument('-c', action='store', dest='target_columns', nargs='+',
                        default=["label_clean", "kg_labels"],
                        help="The target columns aimed to calculate the string similarity. Should only send 2 values.")

    parser.add_argument('--method', action='store', dest='similarity_method', nargs='+',
                        default=[],
                        help="The string similarity methods to use, can have multiple methods.")

    parser.add_argument('-o', '--output-column-name', action='store', dest='output_column',
                        help='The output column is the named column of string similarity computed')

    parser.add_argument('--threshold', action='store', dest='threshold', type=float, default=0.0,
                        help='str threshold')


def run(**kwargs):
    from tl.features.string_similarity import StringSimilarity
    import pandas as pd
    import time

    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        method = kwargs["similarity_method"]
        kwargs["df"] = df
        similarity_calculation_unit = StringSimilarity(similarity_method=kwargs.pop("similarity_method"), **kwargs)
        odf = similarity_calculation_unit.get_similarity_score(threshold=kwargs['threshold'])
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "string-similarity-" + str(method),
            "time": end - start
        })
        odf.to_csv(sys.stdout, index=False)

    except:
        message = 'Command: string-similarity\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
