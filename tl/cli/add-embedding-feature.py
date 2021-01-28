import sys
import traceback
import typing
import argparse

from tl.exceptions import TLException

def parser():
    return {
        'help': 'add candidate embedding vectors.'
    }


def add_arguments(parser):
    # input file
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    # vector embedding file
    parser.add_argument(
        '--embedding-file', action='store',
        help='Vector embedding in TSV format. Column one contains qnodes, and the other columns are vectors.')

    parser.add_argument('--column-vector-strategy', action='store', dest='column_vector_strategy',
                        default="centroid-of-singletons", choices=["centroid-of-singletons"],
                        help="the name of the strategy to use to create the vector for the column.")

    # distance function
    parser.add_argument(
        '--distance-function', action='store', dest='distance_function',
        default="cosine", choices=("cosine", "euclidean"),
        help="the function to compute similarity between column vectors and candidate vectors, "
        "default is cosine.")

    # output
    parser.add_argument(
        '-o', '--output-column-name', action='store', dest='output_column_name',
        default=None,
        help="the name of the column where the value of the distance function will be stored.")

def run(**kwargs):
    print(kwargs)
    try:
        from tl.features.external_embedding import EmbeddingVector
        import pdb
        pdb.set_trace()
        input_file_path = kwargs.pop("input_file")
        vector_transformer = EmbeddingVector(kwargs)
        vector_transformer.load_input_file(input_file_path)
        vector_transformer.get_vectors()
        vector_transformer.process_vectors()
        vector_transformer.add_score_column()
        vector_transformer.print_output()
    except:
        message = 'Command: add-embedding-feature\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise TLException(message)
