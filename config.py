import os
import configparser
from functools import lru_cache

# DATA_DIR is writable (beside the .exe when frozen, beside this file otherwise)
_DATA_DIR   = os.environ.get('CADENCE_DATA_DIR',
                              os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(_DATA_DIR, 'config.txt')

DEFAULTS = {
    'db_path':    os.path.join(_DATA_DIR, 'cadence.db'),
    'pdf_folder': r'C:\invoice',
}


@lru_cache(maxsize=1)
def load():
    cfg = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH)
    return {
        'db_path':    cfg.get('paths', 'db_path',    fallback=DEFAULTS['db_path']),
        'pdf_folder': cfg.get('paths', 'pdf_folder', fallback=DEFAULTS['pdf_folder']),
    }


def save(db_path, pdf_folder):
    cfg = configparser.ConfigParser()
    cfg['paths'] = {'db_path': db_path, 'pdf_folder': pdf_folder}
    with open(CONFIG_PATH, 'w') as f:
        cfg.write(f)
    load.cache_clear()
