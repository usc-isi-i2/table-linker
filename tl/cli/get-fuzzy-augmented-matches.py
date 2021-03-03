import sys
import argparse
import traceback
import tl.exceptions

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

    parser.add_argument('-c','--column',action='store',type=str,dest='column',required=True,
                        help='Column used for retrieving candidates.')

    parser.add_argument('-n',action='store',type=int,dest='size',default=100,
                        help='maximum number of candidates to retrieve')

    parser.add_argument('-o','--output-column',action='store',type=str,dest='output_column_name',default="retrieval_score",
                        help='Output column name where the scores will be stored is retrieval_score')

    parser.add_argument('-p','--properties',action='store',type=str,dest='properties',
                        default='''labels.en,labels.de,labels.es,labels.fr,labels.it,labels.nl,labels.pl,
                                labels.pt,labels.sv,aliases.en,aliases.de,aliases.es,aliases.fr,aliases.it,
                                aliases.nl,aliases.pl,aliases.pt,aliases.sv,wikipedia_anchor_text.en,
                                wikitable_anchor_text.en,abbreviated_name.en,redirect_text.en''',
                        help='comma separated names of properties in the index over which we need to do fuzzy searches')

    parser.add_argument('--es-url',action='store',type=str,dest='es_url',default='http://localhost:9200')

    parser.add_argument('--es-index',action='store',type=str,dest='es_index',default='wikidata_index')

    parser.add_argument('input_file',nargs='?',type=argparse.FileType('r'),default=sys.stdin)


def run(**kwargs):
    from tl.candidate_generation.get_fuzzy_augmented_matches import FuzzyAugmented
    import pandas as pd
    try:
        df = pd.read_csv(kwargs['input_file'],dtype=object)
        em = FuzzyAugmented(es_url=kwargs['es_url'],es_index=kwargs['es_index'],properties=kwargs['properties'])
        odf = em.get_matches(column=kwargs['column'],size=kwargs['size'],df=df,
                             output_column_name=kwargs['output_column_name'])
        odf.to_csv(sys.stdout, index=False)

    except:
        message = 'Command: get-fuzzy-augmented-matches\n'
        message += 'Error Message: {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)