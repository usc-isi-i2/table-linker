import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': """Identify pseudo GT and then compute tf-idf score using semantic features in the pseudo GT."""
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column_name',
                        default="smc_score",
                        help='the output column name where the normalized scores will be stored.Default is smc_score')
    parser.add_argument('--pagerank-column', action='store', dest='pagerank_column', required=True,
                        help="Name of the column with pagerank feature")
    parser.add_argument('--retrieval-score-column', action='store', dest='retrieval_score_column', required=True,
                        help="Name of the column with retrieval score feature")
    parser.add_argument('--feature-file', action='store', dest='feature_file', required=True,
                        help="a tsv file with feature on which to compute tf idf score")
    parser.add_argument('--feature-name', action='store', dest='feature_name', required=True,
                        help="name of the column in the feature file")
    parser.add_argument('--high-confidence-column', action='store', dest='hc_column', required=False,
                        help="name of the column indicating a candidate is high confidence. It not provided, the"
                             "command will identify high confidence candidates based on pagerank and retrieval score")
    parser.add_argument('--N', action='store', dest='total_docs', required=False, default=52546967,
                        help="total number of documents in ES index, used to compute IDF. Default: 52546967")


def run(**kwargs):
    from tl.features.semantics_feature import SemanticsFeature
    import time
    try:
        start = time.time()
        tfidf_unit = SemanticsFeature(kwargs['output_column_name'],
                                      kwargs['feature_file'],
                                      kwargs['feature_name'],
                                      float(kwargs['total_docs']),
                                      kwargs['pagerank_column'],
                                      kwargs['retrieval_score_column'],
                                      hc_column=kwargs['hc_column'],
                                      input_file=kwargs['input_file'])

        odf = tfidf_unit.compute_semantic_feature()
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "pgt-semantic-tf-idf-" + kwargs["feature_name"],
            "time": end - start
        })
        odf.to_csv(sys.stdout, index=False)
    except Exception as e:
        message = 'Command: pgt-semantic-tf-idf\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
