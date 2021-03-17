import pandas as pd


def feature_voting(feature_col_names, df):
    for ft in feature_col_names:
        assert ft in df, f'feature column name:{ft} does not exist in input dataset!'

    odf = pd.DataFrame()
    for (_, group) in df.groupby(['column', 'row']):
        tmp_df = group.copy()
        # employ voting on cheap features for non-singleton candidate set
        feature_votes = {
            ft: tmp_df[ft].max()
            for ft in feature_col_names
        }
        for ft in feature_col_names:
            # NaN (astype(float) gives 0.0) is handled by casting no votes
            if feature_votes[ft] == 0:
                tmp_df[f'vote_{ft}'] = 0
            else:
                tmp_df[f'vote_{ft}'] = (tmp_df[ft] == feature_votes[ft]).astype(int)
        group['votes'] = tmp_df.loc[:, [f'vote_{ft}' for ft in feature_col_names]].sum(axis=1)
        odf = odf.append(group)
    return odf
