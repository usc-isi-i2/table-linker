import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': """Pick high confidence candidates"""
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column_name',
                        default="ignore_candidate",
                        help='the output column name where the value {0/1} will be stored.Default is ignore_candidate')
    parser.add_argument('-s', '--string-similarity-columns', action='store', dest='str_sim_columns', required=True,
                        help="a comma separated list of columns with string similarity features")
    parser.add_argument('--maximum-cells', action='store', dest='max_cells', required=False, default=100,
                        help="maximum number of cells that can set to not ignore")
    parser.add_argument('--minimum-cells', action='store', dest='min_cells', required=False, default=10,
                        help="minimum number of cells that can be set to not ignore")
    parser.add_argument('--desired-cell-factor', action='store', dest='desired_cell_factor', required=False,
                        default=0.25,
                        help="fraction of number of cells to be considered")
    parser.add_argument('--string-similarity-threshold', action='store', dest='str_sim_threshold', required=False,
                        default=0.9,
                        help="string similarity threshold below which cells will be ignored")
    parser.add_argument('--string-similarity-threshold-2', action='store', dest='str_sim_threshold_backup',
                        required=False, default=0.8,
                        help="a second string similarity threshold to fall back on, in case there are not sufficient "
                             "candidates with string similarity greater than or equal to --string-similarity-threshold")


def run(**kwargs):
    from tl.features.pick_hc_candidates import PickHCCandidates
    import time
    try:
        start = time.time()
        phcc = PickHCCandidates(string_sim_cols=kwargs['str_sim_columns'].split(","),
                                input_file=kwargs['input_file'],
                                desired_cell_factor=kwargs['desired_cell_factor'],
                                maximum_cells=kwargs['max_cells'],
                                minimum_cells=kwargs['min_cells'],
                                str_sim_threshold=kwargs['str_sim_threshold'],
                                str_sim_threshold_backup=kwargs['str_sim_threshold_backup'])

        odf = phcc.process()
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "pick-hc-candidates",
            "time": end - start
        })
        odf.to_csv(sys.stdout, index=False)
    except Exception as e:
        message = 'Command: pick-hc-candidates\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
