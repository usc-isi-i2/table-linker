import sys
import argparse
import traceback
import tl.exceptions


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

    parser.add_argument('-i', action='store_true', dest='case_sensitive',
                        help='case insensitive retrieval, default is case sensitive')

    parser.add_argument('-n', action='store', type=int, dest='size', default=50,
                        help='maximum number of candidates to retrieve')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.candidate_generation import get_exact_matches
    import pandas as pd
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        em = get_exact_matches.ExactMatches(es_url=kwargs['url'], es_index=kwargs['index'], es_user=kwargs['user'],
                                            es_pass=kwargs['password'])
        odf = em.get_exact_matches(kwargs['column'], properties=kwargs['properties'],
                                   lower_case=kwargs['case_sensitive'],
                                   size=kwargs['size'], df=df)
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: get-exact-matches\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
