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

    parser.add_argument('--add-wrong-candidates', action='store_true', dest='add_wrong_candidates',
                        help='If send with this flag, top 3 scores of wrong candidates will also be added.')

    parser.add_argument('--wrong-candidates-score-column', action='store', type=str, dest='wrong_candidates_score_column',
                        default="gt_embed_score",
                        help='Only valid when add-wrong-candidates flag sent, '
                             'can control which column to use for choosing the wrong candidates display. '
                             'Default is `gt_embed_score`')


def run(**kwargs):
    from tl.features.plot_figure import FigurePlotterUnit
    try:
        plot_unit = FigurePlotterUnit(**kwargs)
        plot_unit.plot_bar_figure()

    except:
        message = 'Command: plot-score-figure\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
