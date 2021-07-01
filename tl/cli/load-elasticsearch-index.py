import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'loads a jsonlines file to Elasticsearch index.'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """

    parser.add_argument('--kgtk-jl-path', action='store',  dest='kgtk_jl_path',required=True,
                       help='Path of the KGTK jsonlines file that needs to be loaded')
    
    parser.add_argument('--es-url', action='store', dest='es_url',required=True,
                       help='Elasticsearch URL')

    parser.add_argument('--es-index', action='store', dest='es_index',required=True,
                       help='Name of the index')

    parser.add_argument('--mapping-file-path', action='store', dest='mapping_file_path',default=None,
                       help='Path of the mapping file')

    parser.add_argument('--es-user', action='store', dest='es_user',default=None,
                       help='Name of the elasticsearch index')

    parser.add_argument('--es-pass', action='store', dest='es_pass',default=None,
                       help='Password of elasticsearch index')

    parser.add_argument('--es-version', action='store', type=float, dest='es_version', default=7.9,
                        help='Version of the Elasticsearch you are using')


def run(**kwargs):
    from tl.utility.utility import Utility
    import time
    try:
        start = time.time()
        Utility.load_elasticsearch_index(kwargs['kgtk_jl_path'], kwargs['es_url'], kwargs['es_index'],
                                         es_version=kwargs['es_version'],
                                         mapping_file_path=kwargs['mapping_file_path'],
                                         es_user=kwargs['es_user'],
                                         es_pass=kwargs['es_pass'])
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "load-elasticsearch-index",
            "time": end-start
        })
    
    except:
        message = 'Command: load-elasticsearch-index\n'
        message += 'Error Message: {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)