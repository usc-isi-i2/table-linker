import pandas as pd


def smallest_qnode_number(df):
    """
    Args:
        df: input dataframe with columns [column, row, label, kg_id, kg_labels, method, retrieval_score, GT_kg_id, GT_kg_label, evaluation_label]

    Returns:
        a dataframe with 'smallest_qnode_number' column
    """
    res = list()
    for ((col, row), group) in df.groupby(['column', 'row']):
        tmp_df = group.copy().fillna("")
        tmp_df['kg_id_num'] = tmp_df['kg_id'].map(lambda x: extract_qnumber(x))
        tmp_kgid_min = tmp_df['kg_id_num'].min()
        tmp_df['smallest_qnode_number'] = (tmp_df['kg_id_num'] == tmp_kgid_min).astype(int)
        group['smallest_qnode_number'] = tmp_df['smallest_qnode_number']
        res.append(group)
    return pd.concat(res)


def extract_qnumber(qnode: str):
    if qnode.startswith('P'):
        return float('inf')
    if qnode.strip():
        return float(qnode.replace("Q", ""))
    return float('inf')  # infinite
