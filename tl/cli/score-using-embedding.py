import sys
import traceback
import typing
import argparse

from tl.exceptions import TLException
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'Score candidates using pre-computed embedding vectors, either from a file or from elasticsearch.'
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
        For text embedding use: "http://kg2018a.isi.edu:9200/wikidataos-text-embedding-01/".
        For graph embedding use: "http://kg2018a.isi.edu:9200/wikidataos-graph-embedding-01/".''')

    parser.add_argument('--column-vector-strategy', action='store', dest='column_vector_strategy',
                        default="centroid-of-singletons",
                        choices=["centroid-of-singletons", 'centroid-of-voting', 'centroid-of-lof'],
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

    parser.add_argument(
        '--min-vote', action='store', dest='min_vote',
        default=0,
        help="When using centroid-of-voting, the minimum vote count a candidate need to receive to be count as high confidence candidate.")

    parser.add_argument(
        '--lof-strategy', action='store', dest='lof_strategy',
        default='ems-mv', choices=["ems-mv", 'ems-only', 'pseudo-gt'],
        help='''
        The name of outlier removal (lof) strategy: 
        - on exact-match-singleton candidates only 
        - on exact-match-singleton and model-voted candidates combined
        - on the pseudo ground truth from the create-pseudo-gt command
        This argument is only valid for column-vector-strategy == centroid-of-lof
        ''')

    # output
    parser.add_argument(
        '-o', '--output-column-name', action='store', dest='output_column_name',
        default=None,
        help="the name of the column where the value of the distance function will be stored.")


def run(**kwargs):
    try:
        from tl.features.external_embedding import EmbeddingVector
        import time
        start = time.time()
        vector_transformer = EmbeddingVector(kwargs)
        vector_transformer.get_vectors()
        vector_transformer.process_vectors()
        vector_transformer.add_score_column()
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "score-using-embedding",
            "time": end-start
        })
        vector_transformer.print_output()
    except:
        message = 'Command: score-using-embedding\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise TLException(message)
