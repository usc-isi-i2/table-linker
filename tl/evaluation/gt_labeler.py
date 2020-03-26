import pandas as pd
from tl.exceptions import RequiredInputParameterMissingException


def ground_truth_labeler(gt_file_path, column, file_path=None, df=None):
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
    gt_df.rename(columns={'kg_id': 'GT_kg_id'}, inplace=True)

    if file_path:
        df = pd.read_csv(file_path, dtype=object)
    df[column] = df[column].map(lambda x: float(x))

    id_labels = list(zip(df.kg_id, df.kg_labels))
    id_labels_dict = {}
    for id, labels in id_labels:
        id_labels_dict[id] = labels.split('|')[0]

    gt_df['GT_kg_label'] = gt_df['GT_kg_id'].map(lambda x: id_labels_dict.get(x, ""))

    evaluation_df = pd.merge(df, gt_df, on=['column', 'row'], how='left')

    evaluation_df['GT_kg_id'].fillna(value="", inplace=True)
    evaluation_df['GT_kg_label'].fillna(value="", inplace=True)
    # evaluation_df['max_score'] = evaluation_df.groupby(by=['column', 'row'])[column].transform(max)
    evaluation_df['evaluation_label'] = evaluation_df.apply(lambda row: evaluate(row, column), axis=1)

    # evaluation_df.drop(columns=['max_score'], inplace=True)
    return evaluation_df


def evaluate(row, column):
    if row['GT_kg_id'] == '':
        return 0

    # if row[column] == row['max_score'] and row['kg_id'] == row['GT_kg_id']:
    if row['kg_id'] == row['GT_kg_id']:
        return 1
    return -1


print(ground_truth_labeler('/Users/amandeep/Github/table-linker/data/countries_gt.csv', 'ranking_score',
                           file_path='/Users/amandeep/Github/table-linker/data/countries_features_ranked.csv'))
