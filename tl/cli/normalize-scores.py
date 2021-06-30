import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'normalizes the retrieval scores for all the candidate knowledge graph objects for each retrieval '
                'method for all input cells in a column'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-c', '--column', action='store', type=str, dest='column', default='retrieval_score',
                        help='column name which has the retrieval scores')

    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column',
                        help='the output column name where the normalized scores will be stored.Default is input column'
                             ' name appended with the suffix _normalized')
    
    parser.add_argument('-t', '--normalization-type', action='store', type=str, dest='normalization_type', default='max_norm',
                        help='Choose type of normalization. We support Max normalization and Z Score normalization '
                            'Choose from "max_norm" or "zscore" '
                            'By default the normalization type is Max normalization')

    parser.add_argument('-w', '--weights', action='store', type=str, dest='weights',
                        help='a comma separated string of the format '
                             '<retrieval_method_1:<weight_1>, <retrieval_method_2:<weight_2>,...> '
                             'specifying the weights for each retrieval method. '
                             'By default, all retrieval method weights are set to 1.0')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.features import normalize_scores
    import pandas as pd
    import time

    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        if kwargs['normalization_type'] != 'max_norm' and kwargs['normalization_type'] != 'zscore':
            raise Exception('Entered normalization type is not supported '
                            'Select from "max_norm" or "zscore"') 

        odf = normalize_scores.normalize_scores(column=kwargs['column'], output_column=kwargs['output_column'], df=df,
                                                weights=kwargs['weights'], norm_type=kwargs['normalization_type'])
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "normalize-scores-"+kwargs["column"],
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: normalize-scores\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
