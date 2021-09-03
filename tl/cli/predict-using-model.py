import sys
import argparse
import traceback
import tl.exceptions
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'final score given by the trained neural network'
    }


def add_arguments(parser):
    """
    Parse Arguments
    Args:
        parser: (argparse.ArgumentParser)

    """
    parser.add_argument('-o', '--output-column', action='store', type=str, dest='output_column', default='siamese_pred',
                        help='name of the column where the final score predicted by the model should be stored')

    parser.add_argument('--ranking-model', action='store', type=str, dest='ranking_model', required=True,
                        help='path where the trained model is stored')

    parser.add_argument('--features', action='store', type=str, dest='features', required=True,
                        help='A comma separated list of features used to train the --ranking-model')

    parser.add_argument('--normalization-factor', action='store', type=str, dest='min_max_scaler_path',
                        required=True,
                        help='path of global normalization factor that is computed during data generation for model '
                             'training')

    parser.add_argument('--ignore-column', action='store', type=str, dest='ignore_column', required=False, default=None,
                        help='')

    parser.add_argument('input_file', nargs='?', type=argparse.FileType('r'), default=sys.stdin)


def run(**kwargs):
    from tl.candidate_ranking import predict_using_model
    import pandas as pd
    import time
    try:
        df = pd.read_csv(kwargs['input_file'], dtype=object)
        start = time.time()
        odf = predict_using_model.predict(features=kwargs['features'],
                                          output_column=kwargs['output_column'],
                                          ranking_model=kwargs['ranking_model'],
                                          min_max_scaler_path=kwargs['min_max_scaler_path'],
                                          ignore_column=kwargs['ignore_column'],
                                          df=df)
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "predict-using-model",
            "time": end-start
        })
        odf.to_csv(sys.stdout, index=False)
    except:
        message = 'Command: predict-using-model\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
