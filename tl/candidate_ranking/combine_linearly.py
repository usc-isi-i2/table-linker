import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException


def combine_linearly(weights, output_column='ranking_score', file_path=None, df=None):
    """
    combines two or more score-columns for candidate knowledge graph objects for each input cell value. Takes as input weights
    for columns being combined to adjust influence.

    Args:
        weights: a comma separated string, in the format <score-column-1>:<weight-1>,<score-column-2>:<weight-2>,...
        representing weights for each score-column. Default weight for each score-column is 1.0.
        output_column: the output column name where the linearly combined scores will be stored. Default is ranking_score
        file_path: input file path
        df: input dataframe

    Returns: a dataframe in ranking score file format

    """
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

    # fill up na to 0 for computation
    target_column_names = list(column_weights.keys())
    df[target_column_names] = df[target_column_names].fillna(0)

    df[output_column] = df.apply(lambda row: linear_combination(row, column_weights), axis=1)
    return df


def linear_combination(row, column_weights):
    score = 0.0
    for column in column_weights:
        score += float(row[column]) * column_weights[column]
    return score
