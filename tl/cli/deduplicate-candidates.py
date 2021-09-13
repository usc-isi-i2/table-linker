import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'drops duplicate candidates for a cell, keeping exact-match candidates'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=False, default='kg_id',
                        help='the column which has candidate ids. Default: "kg_id"')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.candidate_generation.deduplicate_candidates import DedupCandidates
    import pandas as pd
    import time
    try:

        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        dc = DedupCandidates()
        odf = dc.process(column=kwargs['column'],
                         df=df)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "deduplicate-candidates",
            "time": end - start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: deduplicate-candidates\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
