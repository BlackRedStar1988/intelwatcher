from rich.console import Console
from rich.progress import Progress

class Log():
    def __init__(self, debug):
        self.console = Console(log_time=False, log_path=False)
        self.is_debug = debug

    def info(self, text):
        self.console.log(text)

    def error(self, text):
        self.console.log("[bold red]"+text)

    def debug(self, text):
        if self.is_debug:
            self.console.log("[blue]"+text)