"""
allen_api.py
------------
Allen Brain Atlas API integration for structure lookup and annotation.
"""

import requests
import json


ALLEN_API_BASE = "http://api.brain-map.org/api/v2"

# Simple on-disk cache to avoid repeated Allen API calls
_CACHE_PATH = ".cache/allen_structures.json"
_STRUCTURE_CACHE = None


def _load_cache():
    global _STRUCTURE_CACHE
    if _STRUCTURE_CACHE is not None:
        return
    try:
        with open(_CACHE_PATH, "r") as fh:
            _STRUCTURE_CACHE = json.load(fh)
    except Exception:
        _STRUCTURE_CACHE = {}


def _save_cache():
    try:
        import os
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w") as fh:
            json.dump(_STRUCTURE_CACHE, fh)
    except Exception:
        pass


def get_structure_info(structure_id):
    """
    Fetch structure information from Allen Brain Atlas API.
    Returns name, acronym, color, and parent structure.
    """
    _load_cache()
    sid = str(int(structure_id))
    if sid in _STRUCTURE_CACHE:
        return _STRUCTURE_CACHE[sid]

    try:
        url = f"{ALLEN_API_BASE}/data/Structure/{structure_id}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()['msg'][0]
        info = {
            'id': data['id'],
            'name': data['name'],
            'acronym': data['acronym'],
            'color_hex_triplet': data.get('color_hex_triplet', 'CCCCCC'),
            'parent_structure_id': data.get('parent_structure_id')
        }
        _STRUCTURE_CACHE[sid] = info
        _save_cache()
        return info
    except Exception:
        return None


def get_structures_by_acronym(acronym):
    """
    Search structures by acronym (e.g., 'CTX' for cortex).
    """
    try:
        url = f"{ALLEN_API_BASE}/data/query.json?criteria=[name$il'{acronym}']&model=Structure"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()['msg']
    except Exception as e:
        return []


def batch_get_structures(structure_ids):
    """
    Fetch info for multiple structure IDs.
    """
    results = {}
    for sid in structure_ids:
        info = get_structure_info(sid)
        if info:
            results[sid] = info
    return results
