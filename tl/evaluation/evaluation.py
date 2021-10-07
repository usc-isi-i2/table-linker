import pandas as pd
from collections import defaultdict
from tl.exceptions import RequiredInputParameterMissingException
from tl.features import normalize_scores


def read_csv(file_path, dtype=object):
    try:
        df = pd.read_csv(file_path, dtype=dtype)
    except UnicodeDecodeError:
        # try latin_1 encode as well
        df = pd.read_csv(file_path, dtype=dtype, encoding='latin_1')
    return df


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

    gt_df = read_csv(gt_file_path, dtype=object)
    gt_df.rename(columns={'kg_id': 'GT_kg_id', 'kg_label': 'GT_kg_label'}, inplace=True)

    if file_path:
        df = read_csv(file_path, dtype=object)
    df.fillna('', inplace=True)

    # kyao: Use only columns defined ground truth file format
    evaluation_df = pd.merge(df, gt_df.loc[:, ['column', 'row', 'GT_kg_id', 'GT_kg_label']], on=['column', 'row'],
                             how='left')

    evaluation_df['GT_kg_id'].fillna(value="", inplace=True)
    evaluation_df['GT_kg_label'].fillna(value="", inplace=True)

    evaluation_df['evaluation_label'] = evaluation_df.apply(lambda row: assign_evaluation_label(row), axis=1)

    return evaluation_df


def assign_evaluation_label(row):
    if row['GT_kg_id'] == '':
        return 0

    gt_kg_ids = set(row['GT_kg_id'].split("|"))
    if row['kg_id'] in gt_kg_ids:
        return 1
    return -1


def metrics(column, file_path=None, df=None, k: int = 1, tag=""):
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
        df = read_csv(file_path, dtype=object)

    # remove duplicate candidates if exist
    df = normalize_scores.drop_duplicate("kg_id", [column], df=df)

    # replace na to 0.0
    df[column] = df[column].astype(float).fillna(0.0)
    df['max_score'] = df.groupby(by=['column', 'row'])[column].transform(max)

    # relevant df
    rdf = df[df['evaluation_label'].astype(float) != 0.0]

    col_grouped = rdf.groupby(by=['column'])
    results = []
    for col, cgdf in col_grouped:
        # true positive for precision at 1
        tp_ps = []

        # true positive for recall at k
        tp_rs = defaultdict(list)
        grouped = cgdf.groupby(by=['row'])
        n = len(grouped)
        for key, gdf in grouped:
            gdf = gdf.sort_values(by=[column, 'kg_id'], ascending=[False, True]).reset_index()

            for i, row in gdf.iterrows():
                if float(row['evaluation_label']) == 1 and row[column] == row['max_score']:
                    tp_ps.append(key)

                # this df is sorted by score, so highest ranked candidate is rank 1 and so on...
                rank = i + 1
                if rank <= k and (row['evaluation_label'] == '1' or row['evaluation_label'] == 1.0):
                    tp_rs[k].append(key)

        precision = float(len(tp_ps)) / float(n)
        recall = {k: float(len(each_tp_rs)) / float(n) for k, each_tp_rs in tp_rs.items()}
        # sort as k value increasing
        recall = {k: v for k, v in sorted(recall.items(), key=lambda x: x[0])}

        for _k, each_recall in recall.items():
            if precision == 0 and each_recall == 0:
                f1_score = 0.0
            else:
                f1_score = (2 * precision * each_recall) / (precision + each_recall)
            results.append({"k": _k,
                            'f1': f1_score,
                            'precision': precision,
                            'recall': each_recall,
                            'column': col,
                            'tag': tag})

    output_df = pd.DataFrame(results)
    return output_df
