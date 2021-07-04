import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'add score column based on by checking the extra information.'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('--extra-information-file', action='store', type=str,
                        dest='extra_information_file', default=None,
                        help='path to the extra information file')

    parser.add_argument('--score-column', action='store', nargs='?', dest='score_column', required=False,
                        default=None, help="The name of the column used for the scoring to determine the prediction results.")

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    parser.add_argument('--sparql-query-endpoint', action='store', dest='query_address',
                        help="sparql_query_endpoint", default="https://query.wikidata.org/sparql")


def run(**kwargs):
    from tl.features.extra_information import ExtraInformationProcessing
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        processing_unit = ExtraInformationProcessing(**kwargs)
        odf = processing_unit.check_extra_information(df=df)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "check-extra-information",
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: check-extra-information\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
