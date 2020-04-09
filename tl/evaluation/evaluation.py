import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException


def ground_truth_labeler(gt_file_path, file_path=None, df=None):
    """
    compares each candidate for the input cells with the ground truth value for that cell and adds an evaluation label.

    Args:
        gt_file_path: ground truth file path.
        column: column name with ranking scores
        file_path: input file path
        df: or input dataframe

    Returns: a dataframe with added column `evaluation_label`

    """
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format('file_path', 'df'))

    gt_df = pd.read_csv(gt_file_path, dtype=object)
    gt_df.rename(columns={'kg_id': 'GT_kg_id', 'kg_label': 'GT_kg_label'}, inplace=True)

    if file_path:
        df = pd.read_csv(file_path, dtype=object)
    df.fillna('', inplace=True)

    evaluation_df = pd.merge(df, gt_df, on=['column', 'row'], how='left')

    evaluation_df['GT_kg_id'].fillna(value="", inplace=True)
    evaluation_df['GT_kg_label'].fillna(value="", inplace=True)

    evaluation_df['evaluation_label'] = evaluation_df.apply(lambda row: assign_evaluation_label(row), axis=1)

    # evaluation_df.drop(columns=['max_score'], inplace=True)
    return evaluation_df


def assign_evaluation_label(row):
    if row['GT_kg_id'] == '':
        return 0

    if row['kg_id'] == row['GT_kg_id']:
        return 1
    return -1


def metrics(column, file_path=None, df=None, k=1, tag=""):
    """
    computes the precision, recall and f1 score for the tl pipeline.

    Args:
        column: column with ranking score
        file_path: input file path
        df: or input dataframe
        k: calculate recall at top k candidates
        tag: a tag to use in the output file to identify the results of running the given pipeline

    Returns:

    """
    if file_path is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format('file_path', 'df'))

    if file_path:
        df = pd.read_csv(file_path)

    df['max_score'] = df.groupby(by=['column', 'row'])[column].transform(max)

    # relevant df
    rdf = df[df['evaluation_label'] != '0']

    n = len(rdf)

    # true positive for precision at 1
    tp_ps = []

    # true positive for recall at k
    tp_rs = []

    grouped = rdf.groupby(by=['column', 'row'])
    for key, gdf in grouped:
        gdf = gdf.reset_index()
        gdf.sort_values(by=[column, 'kg_id'], ascending=[False, True], inplace=True)
        for i, row in gdf.iterrows():
            if row['evaluation_label'] == '1' and row[column] == row['max_score']:
                tp_ps.append(key)

            # this df is sorted by score, so highest ranked candidate is rank 1 and so on...
            rank = i + 1
            if rank <= k and row['evaluation_label'] == '1':
                tp_rs.append(key)

    precision = float(len(tp_ps)) / float(n)
    recall = float(len(tp_rs)) / float(n)
    if precision == 0 and recall == 0:
        f1_score = 0.0
    else:
        f1_score = (2 * precision * recall) / (precision + recall)

    return pd.DataFrame({'f1': f1_score, 'precision': precision, 'recall': recall, 'tag': tag}, index=[0])
