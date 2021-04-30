import sys
import argparse
import traceback
import tl.exceptions


def parser():
    return {
        'help': 'compute voting model prediction on candidate file'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    parser.add_argument(
        '--model', action='store', dest='model',
        help='location of the trained voting model'
    )

    parser.add_argument(
        '--prob-threshold', action='store', dest='prob_threshold',
        help='classifier voting threshold of prob_1'
    )


def run(**kwargs):
    import pandas as pd
    import os
    import pickle
    try:
        # check input file
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        features_list = [
            'aligned_pagerank', 'smallest_qnode_number', 'monge_elkan', 'des_cont_jaccard_normalized'
        ]
        for ft in features_list:
            assert ft in df, f'There\'s no {ft} column in the table!'

        # check model file
        model_file = kwargs.get('model', '')
        assert os.path.isfile(model_file), f'There\'s no model file: {model_file}!'
        with open(model_file, 'rb') as fid:
            model_loaded = pickle.load(fid)

        # check prediction threshold
        prob_threshold = kwargs.get('prob_threshold', '0')
        try:
            prob_threshold = float(prob_threshold)
        except:
            prob_threshold = 0

        # make prediction on target file
        odf = df.copy()

        test_features = df.loc[
            :, ['aligned_pagerank', 'smallest_qnode_number', 'monge_elkan', 'des_cont_jaccard_normalized']
        ]

        # preds = model_loaded.predict(test_features)
        prob = model_loaded.predict_proba(test_features)

        # odf['pred'] = preds
        # odf['prob_0'] = [p[0] for p in prob]
        df['prob_1'] = [p[1] for p in prob]
        odf['vote_by_classifier'] = (df['prob_1'] > prob_threshold).astype(int)

        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: vote-by-classifier\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
