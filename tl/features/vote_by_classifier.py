import pandas as pd
import pickle
from tl.exceptions import RequiredInputParameterMissingException


def vote_by_classifier(model_file, input_file=None, df=None, prob_threshold=0.995):
    if input_file is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("input_file", "df"))
    if not model_file:
        raise RequiredInputParameterMissingException('Model path cannot be None')

    if input_file:
        df = pd.read_csv(input_file, dtype=object)
    features_list = [
        'aligned_pagerank', 'smallest_qnode_number', 'monge_elkan', 'des_cont_jaccard_normalized'
    ]
    for ft in features_list:
        assert ft in df, f'There\'s no {ft} column in the table!'

    with open(model_file, 'rb') as fid:
        model_loaded = pickle.load(fid)

    try:
        prob_threshold = float(prob_threshold)
    except:
        prob_threshold = 0

    # make prediction on target file
    odf = df.copy()

    test_features = df.loc[
                    :, ['aligned_pagerank', 'smallest_qnode_number', 'monge_elkan', 'des_cont_jaccard_normalized']
                    ]

    prob = model_loaded.predict_proba(test_features)

    df['prob_1'] = [p[1] for p in prob]
    odf['vote_by_classifier'] = (df['prob_1'] > prob_threshold).astype(int)
    return odf
