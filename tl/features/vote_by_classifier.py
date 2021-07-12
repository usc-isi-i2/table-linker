import pandas as pd
import pickle
from tl.exceptions import RequiredInputParameterMissingException


def vote_by_classifier(features: str, model_file: str, input_file: str = None, df: pd.DataFrame = None,
                       prob_threshold: float = 0.995):
    if input_file is None and df is None:
        raise RequiredInputParameterMissingException(
            'One of the input parameters is required: {} or {}'.format("input_file", "df"))
    if not model_file:
        raise RequiredInputParameterMissingException('Model path cannot be None')

    if input_file:
        df = pd.read_csv(input_file, dtype=object)

    with open(model_file, 'rb') as fid:
        model_loaded = pickle.load(fid)

    try:
        prob_threshold = float(prob_threshold)
    except ValueError:
        prob_threshold = 0.0

    # make prediction on target file
    odf = df.copy()

    classifier_features = [x.strip() for x in features.split(',')]
    for ft in classifier_features:
        assert ft in df, f'There\'s no {ft} column in the table!'

    test_features = df.loc[:, classifier_features]

    prob = model_loaded.predict_proba(test_features)

    df['prob_1'] = [p[1] for p in prob]
    odf['vote_by_classifier'] = (df['prob_1'] > prob_threshold).astype(int)
    return odf
