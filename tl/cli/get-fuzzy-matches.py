import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'retrieves the identifiers of KG entities whose label or aliases match the input values exactly.'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=True,
                        help='the column used for retrieving candidates.')

    parser.add_argument('-p', '--properties', action='store', type=str, dest='properties', default='labels^2,aliases',
                        help='a comma separated names of properties in the KG to search for exact match query')

    parser.add_argument('-n', action='store', type=int, dest='size', default=50,
                        help='maximum number of candidates to retrieve')

    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column_name', default="retrieval_score",
                        help='the output column name where the normalized scores will be stored.Default is retrieval_score')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.candidate_generation import get_fuzzy_matches
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        em = get_fuzzy_matches.FuzzyMatches(es_url=kwargs['url'], es_index=kwargs['index'], es_user=kwargs['user'],
                                            es_pass=kwargs['password'], output_column_name=kwargs['output_column_name'])
        odf = em.get_exact_matches(kwargs['column'], properties=kwargs['properties'],
                                   size=kwargs['size'], df=df)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "get-fuzzy-matches",
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: get-fuzzy-matches\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
