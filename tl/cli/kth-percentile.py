import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': """Label the top kth percentile candidates for a column."""
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=True,
                        help='the input column which has numeric values to compute the k-percentile on')
    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column_name',
                        default="kth_percenter",
                        help='the output column name where the value {0/1} will be stored, '
                             'indicating whether this candidate belongs to k percenters. Default is kth_percenter')
    parser.add_argument('--ignore-column', action='store', type=str, dest='ignore_column', required=False,
                        help='the column which marks candidates to be ignored or not')
    parser.add_argument('--minimum-cells', action='store', type=int, dest='minimum_cells', required=False,
                        help='minimum number of cells which should have a kth percenter candidate')
    parser.add_argument('--k-percentile', action='store', dest='k_percentile', type=str, required=False, default='mean',
                        help="The value for kth percentile. The values to this option should either be any number "
                             "between [0.0, 1.0], or a string ∈ {mean, median}")


def run(**kwargs):
    from tl.features.kth_percentile import KthPercentile
    import time
    try:
        start = time.time()
        column = kwargs['column']
        kp = KthPercentile(input_file=kwargs['input_file'],
                           column=column,
                           output_column=kwargs['output_column_name'],
                           k_percentile=kwargs['k_percentile'],
                           ignore_column=kwargs['ignore_column'],
                           minimum_cells=kwargs['minimum_cells'])

        odf = kp.process(column)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "kth-percentile",
            "time": end - start
        })
        odf.to_csv(sys.stdout, index=False)
    except Exception as e:
        message = 'Command: kth-percentile\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
