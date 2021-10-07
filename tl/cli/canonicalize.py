import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'translate an input CSV or TSV file to canonical form'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-c', '--columns', action='store', type=str, dest='columns', required=True,
                        help='the columns in the input file to be linked to KG entities. Multiple columns'
                             ' are specified as a comma separated string.')
    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column', default='label')
    parser.add_argument('-s', '--skip-columns', action='store', type=str, dest='skip_columns',
                        help='a comma separated list of columns, values of which will not be put in context')
    parser.add_argument('--tsv', action='store_true', dest='tsv')
    parser.add_argument('--csv', action='store_true', dest='csv')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    parser.add_argument('--add-context', action='store_true', dest='add_context',
                        help="if provided, the information from other columns will be combined together and saved "
                             "to the column: `context`, separated by `|`")


def run(**kwargs):
    from tl.preprocess import preprocess
    import pandas as pd
    import time

    file_type = 'tsv' if kwargs['tsv'] else 'csv'
    try:
        i_file = kwargs['input_file']
        skip_columns = kwargs.get('skip_columns', None)
        if skip_columns:
            skip_columns = skip_columns.split(',')
        df = pd.read_csv(i_file, sep=',' if file_type == 'csv' else '\t', dtype=object)
        file_name = i_file.name.split("/")[-1]

        start = time.time()
        odf = preprocess.canonicalize(kwargs['columns'], output_column=kwargs['output_column'], df=df,
                                      file_type=file_type, add_context=kwargs['add_context'],
                                      file_name=file_name,
                                      skip_columns=skip_columns)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "canonicalize",
            "time": end - start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: canonicalize\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
