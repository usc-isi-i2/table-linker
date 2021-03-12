import pandas as pd


def smallest_qnode_number(df):
    """
    Args:
        df: input dataframe with columns [column, row, label, kg_id, kg_labels, method, retrieval_score, GT_kg_id, GT_kg_label, evaluation_label]

    Returns:
        a dataframe with 'smallest_qnode_number' column
    """
    res = pd.DataFrame()
    for ((col, row), group) in df.groupby(['column', 'row']):
        tmp_df = group.copy()
        tmp_df = tmp_df.fillna('')
        tmp_df['kg_id_num_str'] = tmp_df['kg_id'].str.replace('Q', '')
        # Considering some candidates can be Pnode: filter as empty string
        for i, row in tmp_df[tmp_df['kg_id_num_str'].str.startswith('P')].iterrows():
            tmp_df.loc[i, 'kg_id_num_str'] = ''
        tmp_df['kg_id_num'] = pd.to_numeric(tmp_df['kg_id_num_str'])
        tmp_kgid_min = tmp_df[tmp_df['kg_id_num'] > 0]['kg_id_num'].min()
        tmp_df['smallest_qnode_number'] = (tmp_df['kg_id_num'] == tmp_kgid_min).astype(int)
        group['smallest_qnode_number'] = tmp_df['smallest_qnode_number']
        res = res.append(group)
    return res