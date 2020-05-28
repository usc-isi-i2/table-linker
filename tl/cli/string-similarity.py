import sys
import argparse
import traceback
import tl.exceptions


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

    parser.add_argument('-i', action='store_true', dest='case_sensitive',
                        help='case insensitive retrieval, default is case sensitive')

    parser.add_argument('--method', action='store', dest='similarity_method', nargs='+',
                        default=[],
                        help="The string similarity methods to use, can have multiple methods.")

    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column',
                        default='similarity_score',
                        help=' the output column name to store the similarity score')


def run(**kwargs):
    from tl.features.string_similarity import StringSimilarity
    import pandas as pd

    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        kwargs["df"] = df
        similarity_calculation_unit = StringSimilarity(similarity_method=kwargs.pop("similarity_method"), **kwargs)
        odf = similarity_calculation_unit.get_similarity_score()
        odf.to_csv(sys.stdout, index=False)

    except:
        message = 'Command: string-similarity\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
