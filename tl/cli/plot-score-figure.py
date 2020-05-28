import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'drop rows base on scores of given columns'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=True, nargs='+',
                        help='column names with ranking scores, can be multiple')

    parser.add_argument('-k', action='store', type=int, dest='k', default=[1, 3, 5], nargs='+',
                        help='the top k results to be calculated for scoring, can have multiple values')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    parser.add_argument('--output', action='store', dest='output_uri',
                        default=None,
                        help="If given, the plotted figure will be saved to given path.")


def run(**kwargs):
    from tl.features.plot_figure import FigurePlotterUnit
    import pandas as pd
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)

        FigurePlotterUnit.plot_bar_figure(columns=kwargs['column'], k=kwargs['k'], df=df, output_path=kwargs["output_uri"])
    except:
        message = 'Command: plot-score-figure\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
