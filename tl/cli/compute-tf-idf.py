import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': """Compute tf-idf score based on the candidate nodes' edges similarity."""
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column_name',
                        default="tf_idf_score",
                        help='the output column name where the normalized scores will be stored.Default is tf_idf_score')
    parser.add_argument('--singleton-column', action='store', dest='singleton_column', required=True,
                        help="Name of the column with singleton feature")
    parser.add_argument('--feature-file', action='store', dest='feature_file', required=True,
                        help="a tsv file with feature on which to compute tf idf score")
    parser.add_argument('--feature-name', action='store', dest='feature_name', required=True,
                        help="name of the column in the feature file")
    parser.add_argument('--N', action='store', dest='total_docs', required=False, default=42123553,
                        help="total number of documents in ES index, used to compute IDF")

    # TODO: add support to use different high precision candidates method
    # parser.add_argument('--high-precision-candidates-method', action='store', nargs='?',
    #                     dest='high_precision_candidates_method',
    #                     required=False, default="from_exact_match",
    #                     help="The method to choose the high precision candidates)


def run(**kwargs):
    from tl.features import tfidf
    try:
        tfidf_unit = tfidf.TFIDF(kwargs['output_column_name'],
                                 kwargs['feature_file'],
                                 kwargs['feature_name'],
                                 kwargs['total_docs'],
                                 kwargs['singleton_column'],
                                 input_file=kwargs['input_file'])
        odf = tfidf_unit.compute_tfidf()
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: compute-tf-idf\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
