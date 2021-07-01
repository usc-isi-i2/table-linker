import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'Uses the augmented wikidata index for generating candidates.'
    }


def add_arguments(parser):
    """
    Parser Arguments
    Args:
         parser: (argparse.ArgumentParser)
    """

    parser.add_argument('-c', '--column', action='store', type=str, dest='column', required=True,
                        help='Column used for retrieving candidates.')

    parser.add_argument('-n', action='store', type=int, dest='size', default=100,
                        help='maximum number of candidates to retrieve')

    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column_name',
                        default="retrieval_score",
                        help='Output column name where the scores will be stored is retrieval_score')

    parser.add_argument('-p', '--properties', action='store', type=str, dest='properties',
                        default='''labels.en,labels.de,labels.es,labels.fr,labels.it,labels.nl,labels.pl,
                                labels.pt,labels.sv,aliases.en,aliases.de,aliases.es,aliases.fr,aliases.it,
                                aliases.nl,aliases.pl,aliases.pt,aliases.sv,wikipedia_anchor_text.en,
                                wikitable_anchor_text.en,abbreviated_name.en,redirect_text.en''',
                        help='comma separated names of properties in the index over which we need to do fuzzy searches')

    parser.add_argument('--auxiliary-fields', action='store', type=str, dest='auxiliary_fields', default=None,
                        help='A comma separated string of auxiliary field names in the elasticsearch.'
                             'A file will be created for each of the specified field at the location specified by'
                             ' the `--auxiliary-folder` option. If this option is specified then,'
                             ' `--auxiliary-folder` must also be specified.')

    parser.add_argument('--auxiliary-folder', action='store', type=str, dest='auxiliary_folder', default=None,
                        help='location where the auxiliary files for auxiliary fields will be stored.'
                             'If this option is specified then `--auxiliary-fields` must also be specified.')

    parser.add_argument('--isa', action='store', type=str, dest='isa', default=None,
                        help='only candidates which are instance of this Qnode will be returned')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.candidate_generation.get_fuzzy_augmented_matches import FuzzyAugmented
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
        em = FuzzyAugmented(es_url=kwargs['url'], es_index=kwargs['index'], es_user=kwargs['user'],
                            es_pass=kwargs['password'], properties=kwargs['properties'],
                            output_column_name=kwargs['output_column_name'])
        odf = em.get_matches(column=kwargs['column'],
                             size=kwargs['size'], df=df,
                             auxiliary_fields=auxiliary_fields,
                             auxiliary_folder=auxiliary_folder,
                             isa=kwargs['isa'])
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "get-fuzzy-augmented-matches",
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)

    except:
        message = 'Command: get-fuzzy-augmented-matches\n'
        message += 'Error Message: {}\n'.format(traceback.format_exc())
        print('entered except', file=sys.stderr)
        raise tl.exceptions.TLException(message)
