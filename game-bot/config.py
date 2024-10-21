from redis import Redis
import yaml
import json
from utility import decode_redis


def use_redis_config(r: Redis):
    def load():
        config = {
            "dry_run": False,
            "alliances": {},
            "queues": {
                "thresholds": {},
                "time_limits": {}
            },
            "bans": {
                "alliances": [],
                "players": []
            }
        }

        for value in r.smembers('settings:alliances:nap'):
            name = value.decode()
            config['alliances'][name] = {
                "name": name,
                "aliases": {name},
                "type": 'NAP'
            }

        for value in r.smembers('settings:alliances:svs'):
            name = value.decode()
            config['alliances'][name] = {
                "name": name,
                "aliases": {name},
                "type": 'SVS'
            }

        test = set([])
        for key in r.scan_iter('settings:aliases:*'):
            alliance_name = key.decode().split(":")[2]
            if alliance_name in config['alliances']:
                config['alliances'][alliance_name]['aliases'] = [alliance_name]
                for alias in r.smembers(key):
                    config['alliances'][alliance_name]['aliases'].append(
                        alias.decode())

        thresholds = decode_redis(r.hgetall('settings:queues:thresholds'))
        for key, value in thresholds.items():
            config['queues']['thresholds'][key] = int(value)

        time_limits = decode_redis(r.hgetall('settings:queues:time_limits'))
        for key, value in time_limits.items():
            config['queues']['time_limits'][key] = int(value)

        for value in r.smembers('settings:bans:players'):
            config['bans']['players'].append(value.decode())
        for value in r.smembers('settings:bans:alliances'):
            config['bans']['alliances'].append(value.decode())

        config['dry_run'] = bool(r.get('settings:dry_run') or False)
        return config
    return load


def use_yaml_config(path: str):
    def load():
        config = yaml.safe_load(open(path, 'r'))
        return config
    return load


def use_json_config(path: str):
    def load():
        config = json.load(open(path, 'r'))
        return config
    return load


def set_config_loader(fn):
    global __loader
    __loader = fn


__loader = use_yaml_config('config.yaml')


alliances = {}
queues = {
    'time_limits': {
        'default': 1*60*10
    },
    'thresholds': {
        'high': 40,
        'low': 20
    }
}
bans = {
    'alliances': [],
    'players': []
}
metrics_retention_duration: int = 1000*60*60*24*7
dry_run: bool = False
username = ''

def load():
    global __loader
    c = __loader()
    global username
    username = c['username']
    global dry_run
    dry_run = c['dry_run']
    global alliances
    alliances = c['alliances']
    global queues
    queues = c['queues']
    global bans
    bans = c['bans']
    global metrics_retention_duration
    metrics_retention_duration = 1000*60*60*24*7
