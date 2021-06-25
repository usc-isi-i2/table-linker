import argparse
import sys
import traceback
from tl.exceptions import TLException
from tl.utility.logging import Logger


def parser():
    return {
        'help': 'run same pipelines on batch of files automatically.'
    }


def add_arguments(parser):
    # input files
    parser.add_argument('input', nargs='+', default=sys.stdin)
    parser.add_argument('--gpu-resources', nargs='+', default=[], dest="gpu_resources")
    # ground truth
    parser.add_argument('--ground-truth-directory', action='store', nargs='?', dest='ground_truth_directory',
                        default="", help="the path of a directory containing the ground truth files for all the input files.")
    parser.add_argument('--ground-truth-file-pattern', action='store', nargs='?', dest='ground_truth_pattern',
                        default="{}_gt.csv",
                        help="the pattern used to create the name of the ground truth file from the name of an input file.")
    parser.add_argument('--omit-headers', action='store_false', help="if set, not store header")
    # tag
    parser.add_argument('--tag', action='store', nargs='?', dest='tag',
                        default="output", help="a tag to use in the output file to identify the results of running the given "
                                               "pipeline")
    # debug
    parser.add_argument('--debug', action='store_true', help="if set, will print debug information.")
    # main pipeline
    parser.add_argument('--pipeline', action='store', nargs='?', dest='pipeline', required=True,
                        default="", help="the pattern used to create the name of the ground truth file from the name of an "
                                         "input file.")
    parser.add_argument('--parallel-count', action='store', nargs='?', dest='parallel_count',
                        default="1", help="The amount of processes to be run at the same time. Default is 1")
    # output
    parser.add_argument('--output', action='store', nargs='?', dest='output_name',
                        default="output_{}", help="defines a name for the output file for each input file.")
    parser.add_argument('--output-folder', action='store', nargs='?', dest='output_folder',
                        default="", help="if provided together with an --output option, the output of each pipeline run will be "
                                         "saved in a file in the given folder.")
    parser.add_argument('--score-column', action='store', nargs='?', dest='score_column', required=True,
                        default="", help="The name of the column used for the scoring to determine the prediction results.")


def run(**kwargs):
    import time
    start = time.time()
    if len(kwargs.get("pipeline")) == 0:
        raise TLException("pipeline command must be given.")

    parallel_count = int(kwargs['parallel_count'])
    input_files = kwargs["input"]
    running_configs = []
    gpu_resources = kwargs.get("gpu_resources")

    # setup the running config
    pipeline_cleaned = kwargs['pipeline']
    for i, each in enumerate(input_files):
        each_config = {
            "input": each,
            "command": pipeline_cleaned,
            "output_folder": kwargs.get("output_folder"),
            "output_name": kwargs.get("output_name"),
            "ground_truth_pattern": kwargs.get("ground_truth_pattern"),
            "ground_truth_directory": kwargs.get("ground_truth_directory", ""),
            "score_column": kwargs.get("score_column"),
            "debug": kwargs.get("debug", False)
        }
        running_configs.append(each_config)
        if len(gpu_resources) > 0:
            each_config["gpu_id"] = gpu_resources[i % len(gpu_resources)]
        else:
            each_config["gpu_id"] = None

    # start running
    try:
        from multiprocessing import Pool
        from tqdm import tqdm
        import time
        import pandas as pd
        from io import StringIO
        from tl.utility.run_pipelines_utility import PipelineUtility
        if parallel_count == 1:
            results = []
            for each in tqdm(running_configs):
                results.append(PipelineUtility.run_one_pipeline(each))
        else:
            from multiprocessing import set_start_method
            set_start_method("spawn")

            # use multiprocess pool function to run in parallel mode
            p = Pool(parallel_count)
            result = p.map_async(PipelineUtility.run_one_pipeline, running_configs)
            pbar = tqdm(total=len(running_configs))
            previous_remain = len(running_configs)
            while not result.ready():
                remain_job = result._number_left
                if remain_job != previous_remain:
                    pbar.update(previous_remain - remain_job)
                    previous_remain = remain_job
                time.sleep(2)
            pbar.close()
            results = result.get()
            p.close()
            p.join()

        PipelineUtility.print_pipeline_running_results(results, omit_header=kwargs['omit_headers'],
                                                       input_files=input_files, tag=kwargs.get('tag'))
        end = time.time()
        logger = Logger(kwargs["logfile"])
        logger.write_to_file(args={
            "command": "run-pipeline",
            "time": end-start
        })
    except:
        message = 'Command: run-pipeline\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise TLException(message)
