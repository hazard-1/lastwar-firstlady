
import base64
import datetime
import json
import re
import cv2
import numpy as np
from ocr import reader, TEXT_DETECTION_THRESHOLD
import config
from model import Role


def read_text_from_image(*args):
    detections = reader.readtext(*args)
    results = []
    for _, text, score in detections:
        if score > TEXT_DETECTION_THRESHOLD:
            results.append(text)
    return results


def parse_name(applicant: str):
    if applicant.lower().strip() == 'vacant':
        return (None, None)

    if not applicant.startswith('['):
        return (None, applicant)

    alliance = ''
    player = ''

    # Expected to match most cases
    exp = re.match('(\[[A-Za-z0-9]+\])(.+)', applicant)
    if exp:
        alliance = get_alliance(
            exp.group(1).removeprefix('[').removesuffix(']'))
        player = exp.group(2).strip()
    else:
        raise ValueError(
            f'failed to parse alliance and player name: {applicant}')

    return (alliance, player)


def extract_coordinates(coords: tuple[tuple[int, int], tuple[int, int]]):
    x1 = coords[0][0]
    x2 = coords[1][0]
    y1 = coords[0][1]
    y2 = coords[1][1]
    return x1, x2, y1, y2


def capture(driver):
    encoded_data = driver.get_screenshot_as_base64()
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def get_alliance(alliance_name: str) -> dict: 
    if alliance_name is None or alliance_name == '':
        return None

    if alliance_name in config.alliances:
        return config.alliances[alliance_name]
    for alliance in config.alliances.values():
        if alliance_name in alliance['aliases']:
            return alliance
    return dict({
        'name': alliance_name,
        'type': None,
        'aliases': []
    })


def get_time_limit(role_name: Role):
    key = role_name.replace(" ", "_").lower()
    time_limits = config.queues['time_limits']
    if key in time_limits:
        return datetime.timedelta(seconds=int(time_limits[key]))
    return datetime.timedelta(seconds=int(time_limits['default']))


def decode_redis(src):
    if isinstance(src, list):
        rv = list()
        for key in src:
            rv.append(decode_redis(key))
        return rv
    elif isinstance(src, dict):
        rv = dict()
        for key in src:
            rv[key.decode()] = decode_redis(src[key])
        return rv
    elif isinstance(src, bytes):
        return src.decode()
    else:
        raise Exception("type not handled: " + type(src))
