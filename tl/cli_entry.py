import sys
import importlib
import pkgutil
import itertools
from io import StringIO
import signal
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from tl import cli
from tl.exceptions import tl_exception_handler
from tl import __version__

handlers = [x.name for x in pkgutil.iter_modules(cli.__path__)
            if not x.name.startswith('__')]

pipe_delimiter = '/'

signal.signal(signal.SIGPIPE, signal.SIG_DFL)


class TLArgumentParser(ArgumentParser):
    def __init__(self, *args, **kwargs):
        if not kwargs.get('formatter_class'):
            kwargs['formatter_class'] = RawDescriptionHelpFormatter

        super(TLArgumentParser, self).__init__(*args, **kwargs)


def cli_entry(*args):
    """
    Usage:
        tl <command> [options]
    """
    parser = TLArgumentParser()
    parser.add_argument(
        '-V', '--version',
        action='version',
        version='TL %s' % __version__,
        help="show tl version and exit."
    )

    parser.add_argument(
        '--url',
        action='store',
        type=str,
        dest='url',
        required=False,
        help='URL of the Elasticsearch server containing the items in the KG')

    parser.add_argument(
        '--index',
        action='store',
        type=str,
        dest='index',
        required=False,
        help='name of the Elasticsearch index')

    parser.add_argument(
        '-U',
        action='store',
        type=str,
        dest='user',
        required=False,
        help='the user id for authenticating to the ElasticSearch index')

    parser.add_argument(
        '-P',
        action='store',
        type=str,
        dest='password',
        required=False,
        help='the password for authenticating to the ElasticSearch index')

    sub_parsers = parser.add_subparsers(
        metavar='command',
        dest='cmd'
    )
    sub_parsers.required = True

    # load parser of each module
    # TODO: need to optimize with lazy loading method
    for h in handlers:
        mod = importlib.import_module('.{}'.format(h), 'tl.cli')
        sub_parser = sub_parsers.add_parser(h, **mod.parser())
        mod.add_arguments(sub_parser)

    if not args:
        args = tuple(sys.argv)
    if len(args) == 1:
        args = args + ('-h',)
    args = args[1:]

    stdout_ = sys.stdout
    last_stdout = StringIO()
    ret_code = 0

    for cmd_args in [tuple(y) for x, y in itertools.groupby(args, lambda a: a == pipe_delimiter) if not x]:
        # parse command and options
        args = parser.parse_args(cmd_args)

        # load module
        func = None
        if args.cmd:
            mod = importlib.import_module('.{}'.format(args.cmd), 'tl.cli')
            func = mod.run
            kwargs = vars(args)
            del kwargs['cmd']

        # run module
        last_stdout.close()
        last_stdout = StringIO()
        ret_code = tl_exception_handler(func, **kwargs)
        sys.stdin.close()
        sys.stdin = StringIO(last_stdout.getvalue())

    stdout_.write(last_stdout.getvalue())
    last_stdout.close()
    sys.stdin.close()

    return ret_code
