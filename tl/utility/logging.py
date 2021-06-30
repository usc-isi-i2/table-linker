import sys


class Logger(object):
    def __init__(self, log_file: str) -> None:
        if not log_file:
            self.log_file = sys.stderr
        else:
            self.log_file = open(log_file, "a")

    def write_to_file(self, args: dict):
        print(f'{args["command"]} Time: {args["time"]}s', file=self.log_file)
