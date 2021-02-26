import sys
import traceback
import argparse

from tl.exceptions import TLException


def parser():
    return {
        'help': """
        Score candidates using feature voting. List of features used: 
        1. exact match top 1: using pre-computed embedding vectors, either from a file or from elasticsearch.
        2. page rank 
        3. qnode with smallest number
        4. Weiss Waterman distance
        5. Jaccard between description and row
        6. column query (SemTab 2020 paper)
        """
    }


def add_arguments(parser):
    # input file
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    # vector embedding file
    parser.add_argument(
        '--embedding-file', action='store',
        help='Vector embedding in TSV format. Column one contains qnodes, and the other columns are vectors.')

    parser.add_argument(
        '--embedding-url', action='store',
        help='''URL to elasticsearch embedding service.
        For text embedding use: "http://kg2018a.isi.edu:9200/wikidataos-text-embedding-01/doc/".
        For graph embedding use: "http://kg2018a.isi.edu:9200/wikidataos-graph-embedding-01/doc/".''')

    parser.add_argument('--column-vector-strategy', action='store', dest='column_vector_strategy',
                        default="centroid-of-voting", choices=["centroid-of-voting"],
                        help="the name of the strategy to use to create the vector for the column.")

    # distance function
    parser.add_argument(
        '--distance-function', action='store', dest='distance_function',
        default="cosine", choices=("cosine", "euclidean"),
        help="the function to compute similarity between column vectors and candidate vectors, "
        "default is cosine.")


    parser.add_argument(
        '-c', '--input-column-name', action='store', dest='input_column_name',
        default='kg_id',
        help="the name of the column containing the Qnodes.")

    # output
    parser.add_argument(
        '-o', '--output-column-name', action='store', dest='output_column_name',
        default=None,
        help="the name of the column where the value of the distance function will be stored.")


def run(**kwargs):
    try:
        from tl.features.vote_embedding import EmbeddingVector
        input_file_path = kwargs.pop("input_file")
        vector_transformer = EmbeddingVector(kwargs)
        vector_transformer.load_input_file(input_file_path)
        vector_transformer.get_vectors()
        vector_transformer.process_vectors()
        vector_transformer.add_score_column()
        vector_transformer.print_output()
    except:
        message = 'Command: score-using-embedding\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise TLException(message)
