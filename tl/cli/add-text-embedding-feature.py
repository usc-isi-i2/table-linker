import typing
import argparse
import sys
import traceback
import tl.exceptions

def parser():
    return {
        'help': 'use ktgk text embedding function to add vectors for candidates for further steps.'
    }

def add_arguments(parser):
    from tl.utility.utility import Utility
    from kgtk.cli.text_embedding import ALL_EMBEDDING_MODELS_NAMES
    # input file
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    # query endpoint, default use official wikidata?
    parser.add_argument('-q', '--sparql-query-endpoint', action='store', dest='query_server',
            help="sparql_query_endpoint", default="https://query.wikidata.org/sparql")

    # embedding model choice
    parser.add_argument('-c', '--column-vector-strategy', action='store', dest='column_vector_strategy',
            default="exact-matches", choices=("ground-truth", "exact-matches"),
            help="the name of the strategy to use to create the vector for the column:")
    parser.add_argument('-m', '--embedding-model', action='store', nargs='+', dest='models_names',
            default="bert-base-wikipedia-sections-mean-tokens", choices=ALL_EMBEDDING_MODELS_NAMES,
            help="the model to used for embedding")

    # distance function
    parser.add_argument('-d', '--distance-function', action='store', dest='distance_function',
            default="cosine", choices=("cosine", "euclidean"), 
            help="the function to compute similarity between column vectors and candidate vectors, default is cosine.")

    # n_value
    parser.add_argument('-n', action='store', dest='n_value',
            default=0, type=int,
            help="the number of cells used to estimate the vector for a column (K in the column-vector-strategy). The default is 0, which causes all eligible cells to be used to compute the column vector.")

    # output column name
    parser.add_argument('-o', '--output-column-name', action='store', dest='output_column_name',
            default=None, 
            help="the name of the column where the value of the distance function will be stored. If not provided, the name of the embedding model will be used.")

    # projector file
    parser.add_argument('-g', '--generate-projector-file', action='store', dest='projector_file_name',
            default=None, 
            help="generate the files needed to run the Google Project visualization, using the given name to compose the names of the output files. If given, an additional tsv file will be saved. If only a file name given, it will save on user's home directory.")

    # properties to use for embedding
    parser.add_argument('--label-properties', action='store', nargs='+', 
            dest='label_properties',default= ["label"],
            help="""The names of the eges for label properties, Default is ["label"]. \n This argument is only valid for input in kgtk format.""")
    parser.add_argument('--description-properties', action='store', nargs='+', 
            dest='description_properties', default= ["description"],
            help="""The names of the eges for description properties, Default is ["description"].\n This argument is only valid for input in kgtk format.""")
    parser.add_argument('--isa-properties', action='store', nargs='+', 
            dest='isa_properties', default= ["P31"],
            help="""The names of the eges for `isa` properties, Default is ["P31"] (the `instance of` node in wikidata).\n This argument is only valid for input in kgtk format.""")
    parser.add_argument('--has-properties', action='store', nargs='+', 
            dest='has_properties', default= ["all"],
            help="""The names of the eges for `has` properties, Default is ["all"] (will automatically append all properties found for each node).\n This argument is only valid for input in kgtk format.""")

    # run TSNE or not
    parser.add_argument("--run-TSNE", type=Utility.str2bool, nargs='?',  action='store',
                        default=False, dest="run_TSNE",
                        help="whether to run TSNE or not after the embedding, default is true.")


def run(**kwargs):
    try:
        from tl.features.text_embedding import EmbeddingVector
        input_file_path = kwargs.pop("input_file")
        vector_transformer = EmbeddingVector(kwargs)
        vector_transformer.load_input_file(input_file_path)
        vector_transformer.get_vectors()
        vector_transformer.get_centroid()
        vector_transformer.add_score_column()
        vector_transformer.print_output()
    except:
        message = 'Command: clean\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)