"""
allen_api.py
------------
Allen Brain Atlas API integration for structure lookup and annotation.
"""

import requests
import json


ALLEN_API_BASE = "http://api.brain-map.org/api/v2"


def get_structure_info(structure_id):
    """
    Fetch structure information from Allen Brain Atlas API.
    Returns name, acronym, color, and parent structure.
    """
    try:
        url = f"{ALLEN_API_BASE}/data/Structure/{structure_id}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()['msg'][0]
        return {
            'id': data['id'],
            'name': data['name'],
            'acronym': data['acronym'],
            'color_hex_triplet': data.get('color_hex_triplet', 'CCCCCC'),
            'parent_structure_id': data.get('parent_structure_id')
        }
    except Exception as e:
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
