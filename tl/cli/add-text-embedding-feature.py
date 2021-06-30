import typing
import argparse
import sys
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'use KGTK text embedding function to add vectors for candidates for further steps.'
    }


def add_arguments(parser):
    from tl.utility.utility import Utility
    from kgtk.cli.text_embedding import ALL_EMBEDDING_MODELS_NAMES
    # input file
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    # debug
    parser.add_argument('--debug', action='store_true', help="if set, an kgtk debug logger will be saved at home directory.")

    # query endpoint, default use official wikidata?
    parser.add_argument('--sparql-query-endpoint', action='store', dest='query_server',
                        help="sparql_query_endpoint", default="https://query.wikidata.org/sparql")

    # embedding model choice
    parser.add_argument('--column-vector-strategy', action='store', dest='column_vector_strategy',
                        default="exact-matches", choices=("ground-truth", "exact-matches", "page-rank-precomputed", "page-rank"),
                        help="the name of the strategy to use to create the vector for the column.")
    parser.add_argument('--embedding-model', action='store', nargs='+', dest='all_models_names',
                        default="bert-base-wikipedia-sections-mean-tokens", choices=ALL_EMBEDDING_MODELS_NAMES,
                        help="the model to used for embedding")

    # distance function
    parser.add_argument('--distance-function', action='store', dest='distance_function',
                        default="cosine", choices=("cosine", "euclidean"),
                        help="the function to compute similarity between column vectors and candidate vectors, "
                             "default is cosine.")

    # n_value
    parser.add_argument('--centroid-sampling-amount', action='store', dest='n_value',
                        default=0, type=int,
                        help="the number of cells used to estimate the vector for a column (K in the column-vector-strategy). "
                             "The default is 0, which causes all eligible cells to be used to compute the column vector.")

    # output
    parser.add_argument('-o', '--output-column-name', action='store', dest='output_column_name',
                        default=None,
                        help="the name of the column where the value of the distance function will be stored. If not provided, "
                             "the name of the embedding model will be used.")

    parser.add_argument('--save-embedding-feature', action='store_true', dest='save_embedding_feature',
                        help="if set, will also save the embedding sentences and embedding vectors as extra columns")

    # projector file
    parser.add_argument('--generate-projector-file', action='store', dest='projector_file_name',
                        default=None,
                        help="generate the files needed to run the Google Project visualization, using the given name to "
                             "compose the names of the output files. If given, an additional tsv file will be saved. If only a "
                             "file name given, it will save on user's home directory.")

    # properties to use for embedding
    parser.add_argument('--use-default-file', type=Utility.str2bool, action='store',
                        dest='use_default_file', default=True,
                        help="""Whether to use the setting from default file.""")
    parser.add_argument('--label-properties', action='store', nargs='+',
                        dest='label_properties', default=["label"],
                        help="""The names of the edges for label properties, Default is ["label"]. \n This argument is only
                        valid for input in kgtk format.""")
    parser.add_argument('--description-properties', action='store', nargs='+',
                        dest='description_properties', default=["description"],
                        help="""The names of the edges for description properties, Default is ["description"].\n This argument
                        is only valid for input in kgtk format.""")
    parser.add_argument('--isa-properties', action='store', nargs='+',
                        dest='isa_properties', default=["P31"],
                        help="""The names of the edges for `isa` properties, Default is ["P31"] (the `instance of` node in
                        wikidata).\n This argument is only valid for input in kgtk format.""")
    parser.add_argument('--has-properties', action='store', nargs='+',
                        dest='has_properties', default=["all"],
                        help="""The names of the edges for `has` properties, Default is ["all"] (will automatically append all
                        properties found for each node).\n This argument is only valid for input in kgtk format.""")
    parser.add_argument('--property-value', action='store', nargs='+',
                        dest='property_values', default=[],
                        help="""For those edges found in `has` properties, the nodes specified here will display with
                            corresponding edge(property) values. instead of edge name. """)

    parser.add_argument("--dimensional-reduction", nargs='?', action='store',
                        default="none", dest="dimensional_reduction", choices=("pca", "tsne", "none"),
                        help='whether to run dimensional reduction algorithm or not after the embedding, default is None (not '
                             'run). '
                        )
    parser.add_argument("--dimension", type=int, nargs='?', action='store',
                        default=2, dest="dimension_val",
                        help='How many dimension should remained after reductions, only valid when set to run dimensional '
                             'reduction, default value is 2 '
                        )
    parser.add_argument('--ignore-empty-sentences', action='store_true', dest='ignore_empty_sentences',
                        help="if set, the candidate rows with empty embedding sentences (only Q nodes) will be ignored")


def run(**kwargs):
    try:
        from tl.features.text_embedding import EmbeddingVector
        import time
        input_file_path = kwargs.pop("input_file")
        vector_transformer = EmbeddingVector(kwargs)
        vector_transformer.load_input_file(input_file_path)
        start = time.time()
        vector_transformer.get_vectors()
        vector_transformer.process_vectors()
        vector_transformer.add_score_column()
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "add-text-embedding-feature",
            "time": end-start
        })
        vector_transformer.print_output()
    except:
        message = 'Command: add-text-embedding-feature\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
