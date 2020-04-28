import argparse
import sys
import traceback
import tl.exceptions
import os
import typing


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


def run_one_pipeline(config: dict):
    """
        Main running subprocess
    """
    from tl.utility.utility import Utility
    running_option = ""
    # setup the specific gpu usage if given
    if config.get("gpu_id"):
        running_option += "export CUDA_VISIBLE_DEVICES={}\n".format(config["gpu_id"])
    input_file = config["input"]
    update_part_name = input_file.split("/")[-1].replace(".csv", "")

    if not config["command"].startswith("tl"):
        running_option += "tl "

    all_commands = set([each.replace(".py", "") \
                        for each in os.listdir(os.path.dirname(os.path.abspath(__file__))) \
                        if each.endswith(".py") and not each.startswith("__")])

    import re
    re_match = re.compile("(" + "|".join(all_commands) + "){1}")
    file_insert_pos = re_match.search(config["command"])
    config["command"] = config["command"][:file_insert_pos.end()] + " " + input_file + " " + config["command"][
                                                                                             file_insert_pos.end():]
    # main running table linker function
    running_option += config["command"].replace("{}", update_part_name)

    res = Utility.execute_shell_code(running_option, debug=config["debug"])
    if res == "":
        raise tl.exceptions.TLException("Executing Error!")

    import tempfile
    temp_path = tempfile.mkstemp(prefix='table_linker_temp_file')[1]
    # add ground truth if ground truth given
    if "GT_kg_id" in res or config.get("ground_truth_directory") == "":
        with open(temp_path, "w") as f:
            f.write(res)
    else:
        with open(temp_path, "w") as f:
            f.write(res)
        name = config.get("ground_truth_pattern").replace("{}", update_part_name)
        gt_file_path = os.path.join(config.get("ground_truth_directory"), name)
        running_option = "tl ground-truth-labeler {} -f {}".format(temp_path, gt_file_path)
        res = Utility.execute_shell_code(running_option, debug=config["debug"])
        # update file to the new result with ground truth
        os.remove(temp_path)
        temp_path = tempfile.mkstemp(prefix='table_linker_temp_file')[1]
        with open(temp_path, "w") as f:
            f.write(res)

    # if output folder given, write the output of each pipeline
    if config.get("output_folder") != "":
        output_name = config.get("output_name")
        name = output_name.replace("{}", update_part_name)
        output_path = os.path.join(output_name, name)
        with open(output_path, "w") as f:
            f.write(res)

    # evaluate the prediction
    running_option = "tl metrics {} -c {}".format(temp_path, config["score_column"])
    res = Utility.execute_shell_code(running_option, debug=config["debug"])
    os.remove(temp_path)
    return res


def print_result(results: typing.List[str], omit_header: bool, tag: str, input_files: typing.List[str]):
    from io import StringIO
    import pandas as pd
    res_dfs = [pd.read_csv(StringIO(res)) for res in results]
    res_combined = pd.concat(res_dfs)
    file_names = [each.split("/")[-1] for each in input_files]
    res_combined['file'] = file_names
    res_combined['tag'] = tag
    cols = ["tag", "file", "precision", "recall", "f1"]
    res_combined = res_combined[cols]
    res_combined = res_combined.reset_index().drop(columns=["index"])
    res_combined.to_csv(sys.stdout, index=False, header=omit_header)


def run(**kwargs):
    if len(kwargs.get("pipeline")) == 0:
        raise tl.exceptions.TLException("pipeline command must be given.")

    from tqdm import tqdm
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
        if parallel_count == 1:
            results = []
            for each in tqdm(running_configs):
                results.append(run_one_pipeline(each))
        else:
            p = Pool(parallel_count)
            result = p.map_async(run_one_pipeline, running_configs)
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
            # results = p.map(run_one_pipeline, running_configs)

        print_result(results, omit_header=kwargs['omit_headers'], input_files=input_files, tag=kwargs.get('tag'))
    except:
        message = 'Command: clean\n'
        message += 'Error Message:  {}\n'.format(traceback.format_exc())
        raise tl.exceptions.TLException(message)
