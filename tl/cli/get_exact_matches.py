import sys
import argparse


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

    parser.add_argument('-p', '--properties', action='store', type=str, dest='properties', default='labels,aliases',
                        help='a comma separated names of properties in the KG to search for exact match query')

    parser.add_argument('-i', action='store_true', type=str, dest='case_sensitive',
                        help='case insensitive retrieval, default is case sensitive')

    parser.add_argument('-n', action='store', type=int, dest='size', default=50,
                        help='maximum number of candidates to retrieve')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(column, properties, input_file, case_sensitive, size):
    from tl.candidate_generation import get_exact_matches
    import pandas as pd

    df = pd.read_csv(input_file, dtype=object)
    em = get_exact_matches.ExactMatches(es_url='', es_index='', es_user='', es_pass='')
    odf = em.get_exact_matches(column, properties=properties, lower_case=case_sensitive, size=size, df=df)
    odf.to_csv(sys.stdout, index=False)
