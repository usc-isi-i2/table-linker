import sys
import traceback
import argparse

from tl.exceptions import TLException


def parser():
    return {
        'help': """
        Tabulates votes for candidates using features specified. Example features include: 
        1. page rank top 1
        2. qnode with smallest number
        3. Monge Elkan distance
        4. Jaccard between description and row cell content
        """
    }


def add_arguments(parser):
    # input file
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    # Features used in voting
    parser.add_argument(
        '-c', '--input-column-names', action='store', dest='input_column_names',
        default='qnode_score',
        help="the column name of features to use in voting, separated by ','"
    )


def run(**kwargs):
    try:
        import pandas as pd

        input_file_path = kwargs.pop("input_file")
        input_column_names = kwargs.pop("input_column_names")
        data = pd.read_csv(input_file_path)
        feature_col_name = input_column_names.split(',')

        for ft in feature_col_name:
            assert ft in data, f'feature column name:{ft} does not exist in input dataset!'

        odf = pd.DataFrame()
        for ((col, row), group) in data.groupby(['column', 'row']):
            tmp_df = group.copy()
            # employ voting on cheap features for non-singleton candidate set
            feature_votes = {
                ft: tmp_df[ft].max()
                for ft in feature_col_name
            }
            for ft in feature_col_name:
                # NaN (astype(float) gives 0.0) is handled by casting no votes
                if feature_votes[ft] == 0:
                    tmp_df[f'vote_{ft}'] = 0
                else:
                    tmp_df[f'vote_{ft}'] = (tmp_df[ft] == feature_votes[ft]).astype(int)
            group['votes'] = tmp_df.loc[:, [f'vote_{ft}' for ft in feature_col_name]].sum(axis=1)
            odf = odf.append(group)

        odf.to_csv(sys.stdout, index=False)

    except:
        message = 'Command: feature-voting\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise TLException(message)
