# Environment variables
PWNV_CONFIG_ENV = "PWNV_CONFIG"

# Default paths
DEFAULT_CONFIG_BASENAME = "pwnv_config.json"
DEFAULT_CTFS_FOLDER_NAME = "CTF"
DEFAULT_PWNVENV_FOLDER_NAME = ".pwnvenv"
DEFAULT_PLUGINS_FOLDER_NAME = "plugins"
DEFAULT_TEMPLATES_FOLDER_NAME = "templates"
DEFAULT_SELECTION_FILE_NAME = "selection.json"
# Plugins and templates shipped inside the package, copied in by `pwnv init`
DEFAULT_EXAMPLES_FOLDER_NAME = "examples"

# Default interpreter for the shared CTF environment
DEFAULT_PYTHON_VERSION = "3.13"

# Default packages
DEFAULT_PACKAGES = [
    "pwntools",
    "ropgadget",
    "angr",
    "spwn",
    "pycryptodome",
    "z3-solver",
    "requests",
    "libdebug",
]

# Default template filename
DEFAULT_TEMPLATE_FILENAME = "solve.py"
