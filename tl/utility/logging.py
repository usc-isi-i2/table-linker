import sys


class Logger(object):
    def __init__(self, log_file: str) -> None:
        if not log_file:
            self.log_file = sys.stderr
        else:
            self.log_file = open(log_file, "a")

    def write_to_file(self, args: dict):
        if args["command"] == "compute-tf-idf":
            print(f'{args["command"]}-{args["feature_name"]}'
                  f' Time: {args["time"]}s Input: {args["input_file"]}',
                  file=self.log_file)
        elif args["command"] == "convert-iswc-gt":
            print(f'{args["command"]} Time: {args["time"]}s'
                  f' Output: {args["output_directory"]}', file=self.log_file)
        elif (args["command"] == "drop-duplicate" or
              args["command"] == "drop-by-score"):
            print(f'{args["command"]}-{args["column"]}'
                  f' Time: {args["time"]}s'
                  f' Input: {args["input_file"]}', file=self.log_file)
        elif (args["command"] == "generate-reciprocal-rank" or
              args["command"] == "get-kg-links"):
            print(f'{args["command"]}-{args["score_column"]}'
                  f' Time: {args["time"]}s'
                  f' Input: {args["input_file"]}', file=self.log_file)
        elif args["command"] == "join":
            print(f'join-{args["original_input_file"]}'
                  f' Time: {args["time"]}s'
                  f' Input: {args["input_file"]}', file=self.log_file)
        elif args["command"] == "load-elasticsearch-index":
            print(f'{args["command"]} Time: {args["time"]}s'
                  f' KGTK JL: {args["kgtk_jl_path"]}', file=self.log_file)
        elif args["command"] == "plot-score-figure":
            print(f'{args["command"]} Time: {args["time"]}s'
                  f' Score Table: {args["output_score_table"]}',
                  file=self.log_file)
        elif args["command"] == "normalize-scores":
            print(f'{args["command"]}-{args["column"]}'
                  f' Time: {args["time"]}s'
                  f' Input: {args["input_file"]}', file=self.log_file)
        elif (args["command"] == "run-pipeline" or
              args["command"] == "score-using-embedding"):
            print(f'{args["command"]} Time: {args["time"]}s',
                  file=self.log_file)
        elif args["command"] == "string-similarity":
            print(f'{args["command"]}-{args["method"]} Time: {args["time"]}s'
                  f' Input: {args["input_file"]}', file=self.log_file)
        elif args["command"] == "tee":
            print(f'{args["command"]} Time: {args["time"]}s'
                  f' Input: {args["input"]}', file=self.log_file)
        else:
            print(f'{args["command"]} Time: {args["time"]}s'
                  f' Input: {args["input_file"]}', file=self.log_file)
