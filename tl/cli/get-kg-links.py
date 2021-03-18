import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'returns top k candidates for each cell linking task'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-c', '--column', action='store', type=str, dest='score_column', required=True,
                        help='name of the column which has the final score used for ranking')

    parser.add_argument('-l', '--label', action='store', type=str, dest='label_column',
                        default='label',
                        help='column name with input cell labels. Default is label. '
                             'These values will be stored in the output column label in the output file for this command.')

    parser.add_argument('-k', action='store', type=int, dest='top_k',
                        default=5,
                        help='desired number of output candidates per input cell.')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.features import get_kg_links
    import pandas as pd
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        odf = get_kg_links.get_kg_links(kwargs['score_column'],
                                        df=df,
                                        top_k=kwargs['top_k'],
                                        label_column=kwargs['label_column'])
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: get-kg-links\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
