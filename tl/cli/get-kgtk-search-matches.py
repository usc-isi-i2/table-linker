import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


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
                        help='the output column name where the normalized scores will be stored.'
                             'Default is retrieval_score')

    parser.add_argument('--kgtk-api-url', action='store', type=str, dest='kgtk_api_url',
                        default="https://kgtk.isi.edu/api",
                        help='KGTK search API url, default: https://kgtk.isi.edu/api')

    parser.add_argument('--auxiliary-fields', action='store', type=str, dest='auxiliary_fields', default=None,
                        help='A comma separated string of auxiliary field names in the elasticsearch.'
                             'A file will be created for each of the specified field at the location specified by'
                             ' the `--auxiliary-folder` option. If this option is specified then,'
                             ' `--auxiliary-folder` must also be specified.')

    parser.add_argument('--auxiliary-folder', action='store', type=str, dest='auxiliary_folder', default=None,
                        help='location where the auxiliary files for auxiliary fields will be stored.'
                             'If this option is specified then `--auxiliary-fields` must also be specified.')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.candidate_generation.get_kgtk_search_matches import KGTKSearchMatches
    import pandas as pd
    import time
    try:
        auxiliary_fields = kwargs.get('auxiliary_fields', None)
        auxiliary_folder = kwargs.get('auxiliary_folder', None)

        if (auxiliary_folder is not None and auxiliary_fields is None) or (
                auxiliary_folder is None and auxiliary_fields is not None):
            raise Exception("Both the options `--auxiliary-fields` and `--auxiliary-folder` have to be specified "
                            "if either one is specified")

        if auxiliary_fields is not None:
            auxiliary_fields = auxiliary_fields.split(",")

        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        em = KGTKSearchMatches(api_url=kwargs['kgtk_api_url'],
                               es_url=kwargs['url'],
                               es_index=kwargs['index'],
                               es_user=kwargs['user'],
                               es_pass=kwargs['password'],
                               )
        odf = em.get_matches(kwargs['column'], size=kwargs['size'],
                             output_column_name=kwargs['output_column_name'], df=df,
                             auxiliary_fields=auxiliary_fields,
                             auxiliary_folder=auxiliary_folder)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "get-kgtk-search-matches",
            "time": end - start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: get-kgtk-search-matches\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
