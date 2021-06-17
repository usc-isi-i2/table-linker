import typing
import pandas as pd
import numpy as np

from tl.utility.utility import Utility
from tl.exceptions import RequiredInputParameterMissingException
from tl.exceptions import RequiredColumnMissingException


def normalize_scores(column='retrieval_score', output_column=None, weights=None, file_path=None, df=None,
                     norm_type=None):
    """
    normalizes the retrieval scores for all the candidate knowledge graph objects for each retrieval method for all
    input cells in a column

    Args:
        column: column name which has the retrieval scores. Default is retrieval_score
        output_column: the output column name where the normalized scores will be stored. Default is input column name
        appended with the suffix _normalized
        weights: a comma separated string of the format <retrieval_method_1:<weight_1>, <retrieval_method_2:<weight_2>
        ,...> specifying the weights for each retrieval method. By default, all retrieval method weights are set to 1.0
        file_path: input file path
        df: or input dataframe

    Returns:

    """
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("file_path", "df"))

    if output_column is None:
        output_column = '{}_normalized'.format(column)

    method_weights = {}
    if weights is not None:
        m_ws = weights.split(',')
        for m_w in m_ws:
            _ = m_w.split(':')

            method_weights[_[0]] = float(_[1])

    if file_path:
        df = pd.read_csv(file_path, dtype=object)

    df[column] = df[column].map(lambda x: float(x))

    grouped_df = df.groupby(by=['column', 'method'])

    o_df = list()
    if norm_type == 'max_norm':
        for i, gdf in grouped_df:
            max_score = gdf[column].max()
            # TODO find a better way to do this without having to make a copy
            fdf = gdf.copy(deep=True)
            fdf[output_column] = gdf[column].map(lambda x: divide_a_by_b(x, max_score) * method_weights.get(i[1], 1.0))
            o_df.append(fdf)
    elif norm_type == 'zscore':
        for i, gdf in grouped_df:
            mean_score = gdf[column].mean()
            std_score = gdf[column].std()
            # TODO find a better way to do this without having to make a copy
            fdf = gdf.copy(deep=True)
            fdf[output_column] = gdf[column].map(
                lambda x: zscore_normalization(x, mean_score, std_score) * method_weights.get(i[1], 1.0))
            o_df.append(fdf)

    out_df = Utility.sort_by_col_and_row(pd.concat(o_df))
    return out_df


def drop_by_score(column, file_path=None, df=None, k=20):
    """
    group the dataframe by column, row and then drop the candidates out of given amount k from highest score to lowest
    score

    Args:
        column: column with ranking score
        file_path: input file path
        df: or input dataframe
        k: top k candidates

    Returns:
        filtered dataframe
    """
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format('file_path', 'df'))

    if file_path:
        df = pd.read_csv(file_path)

    # replace na to 0.0
    df[column] = df[column].astype(float).fillna(0.0)
    # astype float first to prevent error of "invalid literal for int() with base 10: '0.0'"
    df["column"] = df["column"].astype(float).astype(int)
    df["row"] = df["row"].astype(float).astype(int)

    res = pd.DataFrame()
    for key, gdf in df.groupby(by=['column', 'row']):
        gdf = gdf.sort_values(by=[column, 'kg_id'], ascending=[False, True]).iloc[:k, :]
        res = res.append(gdf)
    return res


def drop_duplicate(column: str, score_col: typing.List[str], keep_method: str = None, file_path: str = None,
                   df: pd.DataFrame = None):
    """
    group the dataframe by column, row and then check if there are duplicate rows on given column,
    remove the duplicated one and only keep the highest score one

    Args:
        column: column with labels
        score_col: column with ranking scores
        keep_method: the method need to keep
        file_path: input file path
        df: or input dataframe
    Returns:
        filtered dataframe
    """
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format('file_path', 'df'))

    if file_path:
        df = pd.read_csv(file_path)

    for each_col in [column] + score_col:
        if each_col not in df.columns:
            raise RequiredColumnMissingException("Column {} does not exist in given dataframe.".format(each_col))

    # replace na to 0.0
    df[score_col] = df[score_col].astype(float).fillna(0.0)
    # astype float first to prevent error of "invalid literal for int() with base 10: '0.0'"
    df["column"] = df["column"].astype(float).astype(int)
    df["row"] = df["row"].astype(float).astype(int)

    res = []
    for key, gdf in df.groupby(by=['column', 'row']):
        # for those nodes with no candidates, we need to check here
        temp = gdf[column].unique()
        if len(temp) == 1 and not isinstance(temp[0], str) and np.isnan(temp[0]):
            res.append(gdf.iloc[0].to_dict())
            continue

        for candidate_id, candidate_df in gdf.groupby(by=[column]):
            if len(candidate_df) > 1:
                # only do keep method when the method specified exists
                if keep_method is not None and keep_method in candidate_df["method"].unique():
                    candidate_df = candidate_df[candidate_df["method"] == keep_method]
                if score_col and len(candidate_df) > 1:
                    candidate_df = candidate_df.sort_values(by=score_col, ascending=[False]).iloc[:1, :]
            res.append(candidate_df.iloc[0].to_dict())

    # sometimes the column order may changed, resort it to ensure follow original order
    res = pd.DataFrame(res)
    res = res.reindex(columns=df.columns)
    return res


def divide_a_by_b(a, b):
    if b == 0.0:
        return 0.0
    return a / b


def zscore_normalization(val, mean_val, std_val):
    normalized_score = (val - mean_val) / std_val
    return normalized_score
