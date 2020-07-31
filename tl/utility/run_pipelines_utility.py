import sys
import typing
import os
import re
import pandas as pd

from tl.exceptions import TLException
from tl.utility.timeout import timeout_call
from io import StringIO
from tl.evaluation import evaluation
from tl.utility.utility import Utility


class PipelineUtility:
    @staticmethod
    def run_one_pipeline(config: dict, timeout=3600):
        """
            Main running subprocess for one pipeline
        """
        running_option = ""
        # setup the specific gpu usage if given
        if config.get("gpu_id"):
            running_option += "export CUDA_VISIBLE_DEVICES={}\n".format(config["gpu_id"])
        input_file = config["input"]
        update_part_name = input_file.split("/")[-1].replace(".csv", "")

        if not config["command"].startswith("tl"):
            running_option += "tl "

        cli_file_path = os.path.abspath(__file__).replace("utility/utility.py", "cli")
        all_commands = set([each.replace(".py", "") \
                            for each in os.listdir(cli_file_path) \
                            if each.endswith(".py") and not each.startswith("__")])

        re_match = re.compile("(" + "|".join(all_commands) + "){1}")
        file_insert_pos = re_match.search(config["command"])
        config["command"] = config["command"][:file_insert_pos.end()] + " " + \
                            input_file + " " + config["command"][file_insert_pos.end():]
        # main running table linker function
        running_option += config["command"].replace("{}", update_part_name)

        if timeout:
            res = timeout_call(timeout, Utility.execute_shell_code, [running_option, config["debug"]])
        else:
            res = Utility.execute_shell_code(running_option, debug=config["debug"])

        if res is None:
            raise TLException("Timeout on {} seconds when running pipeline on {}!".format(timeout, update_part_name))
        if res == "":
            raise TLException("Executing Error when running pipeline on {}!".format(update_part_name))

        res_io = StringIO(res)
        output_file = pd.read_csv(res_io, dtype=object)

        # add ground truth if ground truth given
        if "GT_kg_id" not in res and config.get("ground_truth_directory") != "":
            name = config.get("ground_truth_pattern").replace("{}", update_part_name)
            gt_file_path = os.path.join(config.get("ground_truth_directory"), name)
            output_file = evaluation.ground_truth_labeler(gt_file_path, df=output_file)

        # if output folder given, write the output of each pipeline
        if config.get("output_folder") != "":
            output_name = config.get("output_name")
            name = output_name.replace("{}", update_part_name)
            output_path = os.path.join(output_name, name)
            output_file.to_csv(output_path, index=False)

        # evaluate the prediction if we can
        if "GT_kg_id" in res:
            evaluation_res = evaluation.metrics(column=config["score_column"], df=output_file)
        else:
            evaluation_res = pd.DataFrame()
        return evaluation_res

    @staticmethod
    def print_pipeline_running_results(results: typing.List[pd.DataFrame], omit_header: bool,
                                       tag: str, input_files: typing.List[str]):
        res_dfs = results  # [pd.read_csv(StringIO(res)) for res in results]
        res_combined = pd.concat(res_dfs)
        file_names = [each.split("/")[-1] for each in input_files]
        res_combined['file'] = file_names
        res_combined['tag'] = tag
        cols = ["tag", "file", "precision", "recall", "f1"]
        res_combined = res_combined[cols]
        res_combined = res_combined.reset_index().drop(columns=["index"])
        res_combined.to_csv(sys.stdout, index=False, header=omit_header)
