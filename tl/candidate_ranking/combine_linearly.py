import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException


def combine_linearly(weights=None, output_column='ranking_score', file_path=None, df=None):
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format('file_path', 'df'))

    column_weights = {}
    if weights is not None:
        c_ws = weights.split(',')
        for c_w in c_ws:
            _ = c_w.split(':')
            if len(_) > 1:
                column_weights[_[0]] = float(_[1])
            else:
                column_weights[_[0]] = 1.0

    if file_path:
        df = pd.read_csv(file_path, dtype=object)

    df[output_column] = df.apply(lambda row: linear_combination(row, column_weights), axis=1)
    return df


def linear_combination(row, column_weights):
    score = 0.0
    for column in column_weights:
        score += float(row[column]) * column_weights[column]
    return score


combine_linearly(file_path='/Users/amandeep/Github/table-linker/tl/sample_delete_later/normalized_file.csv',
                 weights='retrieval_score_normalized:2.0')
