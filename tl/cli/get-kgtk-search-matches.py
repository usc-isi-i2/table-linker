import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'uses KGTK search API to retrieve identifiers of KG entities matching the input search term.'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=True,
                        help='the column used for retrieving candidates.')

    parser.add_argument('-n', action='store', type=int, dest='size', default=20,
                        help='maximum number of candidates to retrieve')

    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column_name',
                        default="retrieval_score",
                        help='the output column name where the normalized scores will be stored.Default is retrieval_score')

    parser.add_argument('--kgtk-api-url', action='store', type=str, dest='kgtk_api_url',
                        default="https://kgtk.isi.edu/api",
                        help='KGTK search API url, default: https://kgtk.isi.edu/api')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.candidate_generation.get_kgtk_search_matches import KGTKSearchMatches
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        em = KGTKSearchMatches(api_url=kwargs['kgtk_api_url'])
        odf = em.get_matches(kwargs['column'], size=kwargs['size'],
                             output_column_name=kwargs['output_column_name'], df=df)
        end = time.time()
        if kwargs["logfile"]:
            with open(kwargs["logfile"],"a") as f:
                print(f'get-kgtk-search-matches Time: {str(end-start)}s'
                      f' Input: {kwargs["input_file"]}',file=f)
        else:
            print(f'get-kgtk-search-matches Time: {str(end-start)}s'
                  f' Input: {kwargs["input_file"]}',file=sys.stderr)
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: get-kgtk-search-matches\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
