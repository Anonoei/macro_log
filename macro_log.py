# Log your gcode macros
#
# Copyright (C) 2024 Anonoei <dev@anonoei.com>
#
# This file may be distributed under the terms of the MIT license.
from enum import Enum
import logging
import queue
import threading
import os

class Level(Enum):
    TRACE = 0
    DEBUG = 1
    INFO = 2
    WARN = 3
    ERROR = 5

    def __lt__(self, other):
        return self.value < other.value
    def __le__(self, other):
        return self.value <= other.value
    def __gt__(self, other):
        return self.value > other.value
    def __ge__(self, other):
        return self.value >= other.value
    
class LogVars:
    @staticmethod
    def parse(gcmd, level):
        name = gcmd.get('NAME', None)
        msg = gcmd.get('MSG')
        display = gcmd.get_int('DISPLAY', 0)
        notify = gcmd.get_int('NOTIFY', 0)
        return LogVars(level, name, msg, display, notify)

    def __init__(self, level: Level, name: str, msg: str, display: bool = False, notify: bool = False):
        self.level = level
        self.name = name
        self.msg = msg
        self.display = display
        self.notify = notify

# Forward all messages through a queue (polled by background thread)
class QueueHandler(logging.Handler):
    def __init__(self, queue):
        logging.Handler.__init__(self)
        self.queue = queue

    def emit(self, record):
        try:
            self.format(record)
            record.msg = record.message
            record.args = None
            record.exc_info = None
            self.queue.put_nowait(record)
        except Exception:
            self.handleError(record)

# Poll log queue on background thread and log each message to logfile
class QueueListener(logging.handlers.TimedRotatingFileHandler):
    def __init__(self, filename):
        logging.handlers.TimedRotatingFileHandler.__init__(self, filename, when='midnight', backupCount=5)
        self.bg_queue = queue.Queue()
        self.bg_thread = threading.Thread(target=self._bg_thread)
        self.bg_thread.start()

    def _bg_thread(self):
        while True:
            record = self.bg_queue.get(True)
            if record is None:
                break
            self.handle(record)

    def stop(self):
        self.bg_queue.put_nowait(None)
        self.bg_thread.join()

# Class to improve formatting of multi-line messages
class MultiLineFormatter(logging.Formatter):
    def format(self, record):
        indent = ' ' * 9
        lines = super(MultiLineFormatter, self).format(record)
        return lines.replace('\n', '\n' + indent)

class MacroLog:
    def __init__(self, config):
        self.config = config
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()

        self.printer.register_event_handler('klippy:connect', self.handle_connect)
        self.printer.register_event_handler("klippy:disconnect", self.handle_disconnect)

        self.log_level = config.getint('log_level', 2, minval=0, maxval=4)
        self.log_file_level = config.getint('log_file_level', 0, minval=0, maxval=4)
        self.log_format = config.get('format', '%(asctime)s %(message)s')
        self.log_date_format = config.get('date_format', '%H:%M:%S')

        self.queue_listener = None
        self.logger = None

        self.gcode = self.printer.lookup_object('gcode')

        self.gcode.register_command('_LOG', self.cmd_LOG, desc=self.cmd_LOG_help)
        self.gcode.register_command('_TRACE', self.cmd_TRACE, desc=self.cmd_TRACE_help)
        self.gcode.register_command('_DEBUG', self.cmd_DEBUG, desc=self.cmd_DEBUG_help)
        self.gcode.register_command('_INFO',  self.cmd_INFO,  desc=self.cmd_INFO_help)
        self.gcode.register_command('_WARN',  self.cmd_WARN,  desc=self.cmd_WARN_help)
        self.gcode.register_command('_ERROR', self.cmd_ERROR, desc=self.cmd_ERROR_help)
        self.gcode.register_command('_PRINT', self.cmd_PRINT, desc=self.cmd_PRINT_help)

    def _log(self, lv: LogVars):
        if lv.level is None:
            message = f"{lv.name}: {lv.msg}"
            self.logger.info(message)
        else:
            message = f"{lv.level.name} <{lv.name}>: {lv.msg}"
        if lv.level is None or (self.logger and self.log_file_level >= lv.level.value):
            self.logger.info(message)
        if lv.display:
            self.gcode._process_commands([f"SET_DISPLAY_TEXT MSG={message}"], False)
        if lv.level is None or self.log_level >= lv.level.value:
            if lv.notify:
                self.gcode.respond_info(f"MR_NOTIFY: | {message}")
            else:
                self.gcode.respond_info(message)

    def handle_connect(self):
        self._setup_logging()

    def handle_disconnect(self):
        self._log(LogVars(Level.TRACE, "ML", "Disconnecting"))

    def _setup_logging(self):
        # Setup background file based logging before logging any messages
        if self.log_file_level >= Level.TRACE.value:
            logfile_path = self.printer.start_args['log_file']
            dirname = os.path.dirname(logfile_path)
            if dirname is None:
                ml_filepath = '/tmp/ml.log'
            else:
                ml_filepath = dirname + '/ml.log'
            self.queue_listener = QueueListener(ml_filepath)
            self.queue_listener.setFormatter(MultiLineFormatter(self.log_format, datefmt=self.log_date_format))
            queue_handler = QueueHandler(self.queue_listener.bg_queue)
            self.logger = logging.getLogger('ML')
            self.logger.setLevel(logging.NOTSET)
            self.logger.addHandler(queue_handler)
            self._log(LogVars(None, "ML", f"\n ----- Initializing with {ml_filepath = } ----- "))

    cmd_LOG_help = ("")
    def cmd_LOG(self, gcmd):
        lvl = gcmd.get('LVL', None)
        if lvl is not None:
            lvl = lvl.upper()
            for l in Level:
                if l.name == lvl:
                    lvl = l
        self._log(LogVars.parse(gcmd, lvl))

    cmd_TRACE_help = ("")
    def cmd_TRACE(self, gcmd):
        self._log(LogVars.parse(gcmd, Level.TRACE))

    cmd_DEBUG_help = ("")
    def cmd_DEBUG(self, gcmd):
        self._log(LogVars.parse(gcmd, Level.DEBUG))

    cmd_INFO_help = ("")
    def cmd_INFO(self, gcmd):
        self._log(LogVars.parse(gcmd, Level.INFO))

    cmd_WARN_help = ("")
    def cmd_WARN(self, gcmd):
        self._log(LogVars.parse(gcmd, Level.WARN))

    cmd_ERROR_help = ("")
    def cmd_ERROR(self, gcmd):
        self._log(LogVars.parse(gcmd, Level.ERROR))

    cmd_PRINT_help = ("")
    def cmd_PRINT(self, gcmd):
        self._log(LogVars.parse(gcmd, None))

def load_config(config): # Called by klipper from [macro_log]
    return MacroLog(config)