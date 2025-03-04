# macro_log
 A logger for klipper gcode macros

Logs are written to ~/printer_data/logs/ml.log

## Example Usage
 - Print a message:
   - `_ML NAME=macro.name MSG="this macro is doing something"`
   - `_PRINT NAME=macro.name MSG="this macro is doing something"`
 - Print a message and show on display:
   - `_ML NAME=macro.name MSG="This is displayed" DISPLAY=1`
   - `_PRINT NAME-macro.name MSG="This is displayed" DISPLAY=1`
 - Send a Mobileraker notification:
   - `_ML NAME=macro.name MSG="Notified" NOTIFY=1`
   - `_PRINT NAME=macro.name MSG="Notified" NOTIFY=1`
 - Log something from a macro
   - `_ML LVL=DEBUG NAME="some.macro" MSG="Hello world!"`
   - `_DEBUG NAME="some.macro" MSG="Hello world!"`

## Using Macro Log
#### Moonraker Update Manager
```
[update_manager macro_log]
type: git_repo
path: ~/macro_log
origin: https://github.com/anonoei/macro_log.git
primary_branch: main
install_script: install.sh
managed_services: klipper
```

### Installation
To install this module you need to clone the repository and run the install.sh script.

#### Automatic installation
```
cd ~
git clone https://github.com/Anonoei/macro_log.git
cd macro_log
./install.sh
```

#### Manual installation
1.  Clone the repository
    1. `cd ~`
    2. `git clone https://github.com/Anonoei/macro_log.git`
    3. `cd macro_log`
2.  Link macro_log to klipper
    1. `ln -sf ~/macro_log/macro_log.py ~/klipper/klippy/extras/macro_log.py`
3.  Restart klipper
    1. `sudo systemctl restart klipper`

### Configuration
Place this in your printer.cfg
```
[macro_log]
```
You can change defaults by specifying the below configuration options
```
[macro_log]
# TRACE: 0
# DEBUG: 1
# INFO: 2
# WARN: 3
# ERROR: 5
log_level: 2
#log_file_level: 0
#format: '%(asctime)s %(message)s'
#date_format: '%H:%M:%S'
```

## Macros
 The default logging macros are listed below, along with their respective logging levels

 - `_PRINT`
 - 0: `_TRACE`
 - 1: `_DEBUG`
 - 2: `_INFO`
 - 3: `_WARN`
 - 5: `_ERROR`

 Argument | Default | Description
 -------- | ------- | -----------
 NAME     | N/A     | Name of the logging instance
 MSG      | N/A     | Message to log
 DISPLAY  | 0       | Show message on display
 NOTIFY   | 0       | Send mobileraker notification

You may also use the `_ML` macro and manually specify a logging level

 - `_ML`

 Argument | Default | Description
 -------- | ------- | -----------
 LVL      | None    | Level to log, one of TRACE, DEBUG, INFO, WARN, ERROR

Using `_ML` without specifying a level is equivalent to `_PRINT`
