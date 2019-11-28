from fsearch.utils import path_resolve

DEFAULT_CONF = {
    "z_jump_file": "${HOME}/.z",
    "project_roots": [
        {
            "path": "${HOME}",
            "min": 1, "max": 2,
            "search": {"type": "d", "iname": ".git"},
        }
    ]
}
CONF_DIR_PATH = path_resolve("$HOME/.config/fsearch")
CONF_FILE_PATH = path_resolve(CONF_DIR_PATH, "config.json")