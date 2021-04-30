import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'computes page rank feature only to exact match candidiates'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    import pandas as pd
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        assert 'pagerank' in df, 'There\'s no page rank column in the table!'

        odf = pd.DataFrame()
        for ((col, row), group) in df.groupby(['column', 'row']):
            exact_match_df = group[group['method'] == 'exact-match'].copy()
            exact_match_df['aligned_pagerank'] = exact_match_df['pagerank'].astype(float)
            odf = odf.append(exact_match_df)

            fuzzy_match_df = group[group['method'] == 'fuzzy-augmented'].copy()
            fuzzy_match_df['aligned_pagerank'] = 0
            odf = odf.append(fuzzy_match_df)
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: align-page-rank\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
