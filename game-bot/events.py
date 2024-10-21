import json
import config
from redis import Redis
import datetime
from structlog.stdlib import BoundLogger
from typing import Optional


from model import Reason, Status, sanitize_role

ONE_DAY_IN_SECONDS = 1*60*60*24


class Events():
    __redis: Optional[Redis]
    __logger: BoundLogger
    __context = {}

    def __init__(self, redis: Optional[Redis], logger: BoundLogger, **kwargs):
        self.__redis = redis
        self.__logger = logger.bind(**kwargs)
        self.__context = kwargs

    def with_context(self, **kwargs):
        context = {}
        for (k, v) in self.__context.items():
            context[k] = v
        for (k, v) in kwargs.items():
            context[k] = v
        return Events(self.__redis, self.__logger, **context)

    def starting_bot(self):
        self.__logger.info('Starting bot')

    def publish_bot_status(self, status: Status):
        if self.__redis is None:
            return

        self.__redis.publish('bot:status', status)
        self.__logger.debug(f'Published status message', status=status)

        key = "metrics:bot:is_online"
        value = 1 if status is not Status.OFFLINE else 0
        self.__redis.ts().add(key=key,
                              timestamp="*",
                              value=value,
                              retention_msecs=config.metrics_retention_duration,
                              duplicate_policy='last')
        self.__logger.debug(f'Set {key} metric', value=value)

        key = key = "metrics:bot:is_first_lady"
        value = 1 if status is Status.ACTIVE else 0
        self.__redis.ts().add(key=key,
                              timestamp="*",
                              value=value,
                              retention_msecs=config.metrics_retention_duration,
                              duplicate_policy='last')
        self.__logger.debug(f'Set {key} metric', value=value)

    def no_pending_applicants(self):
        self.__logger.debug('No pending applicants')
        self.set_pending_count(0)

    def __publish_action_result(self, reason):
        if self.__redis is None:
            return

        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        one_day_ago = now - ONE_DAY_IN_SECONDS

        action_key = f'actions:{now}'
        range_key = 'approvals' if reason is None else 'denials'

        action = {
            "role_name": self.__context['role_name'],
            "alliance_name": self.__context['alliance_name'] if ('alliance_name' in self.__context and self.__context['alliance_name'] is not None) else '',
            "player_name": self.__context['player_name'],
            'approved': int(reason is None),
            "timestamp": now
        }

        if reason is not None:
            action["reason"] = reason

        pipe = self.__redis.pipeline()
        pipe.hset(action_key, mapping=action)
        pipe.expire(action_key, ONE_DAY_IN_SECONDS)
        pipe.zremrangebyscore(range_key, 0, one_day_ago)
        pipe.zadd(range_key, dict({f"{action_key}": now}))
        pipe.publish('bot:actions', now)
        pipe.execute()

    def approved_applicant(self):
        self.__logger.info('Approved applicant')
        self.__publish_action_result(None)

    def denied_applicant(self, reason: Reason):
        self.__logger.info('Denied applicant', reason=reason)
        self.__publish_action_result(reason)

    def applicant_is_still_pending(self):
        if config.dry_run:
            return
        self.__logger.error('Applicant is still pending')
        raise ValueError('Applicant is still pending')

    def dismissed_player(self):
        self.__logger.info('Dismissed player',
                           role_name=self.__context['role_name'],
                           player_name=self.__context['player_name'],
                           alliance_name= self.__context['alliance_name'] if ('alliance_name' in self.__context and self.__context['alliance_name'] is not None) else '',
                           time_in_office=str(
                               self.__context['time_in_office']),
                           role_time_limit=str(self.__context['role_time_limit']))

    def first_lady_status(self, am_first_lady):
        status = Status.ACTIVE if am_first_lady else Status.ONLINE
        self.publish_bot_status(status)

    def set_queue_count(self, queue_length):
        if self.__redis is None:
            return

        key = f'metrics:queues:{sanitize_role(self.__context["role_name"])}:queuing'
        self.__redis.ts().add(key=key,
                              timestamp="*",
                              value=queue_length,
                              retention_msecs=config.metrics_retention_duration,
                              duplicate_policy='last',
                              labels={
                                  "role_name": self.__context["role_name"],
                                  "type": 'queuing'
                              })
        self.__logger.debug(f'Set {key} metric', value=queue_length)

    def set_pending_count(self, pending_length):
        if self.__redis is None:
            return
        
        key = f'metrics:queues:{sanitize_role(self.__context["role_name"])}:pending'
        self.__redis.ts().add(key=key,
                              timestamp="*",
                              value=pending_length,
                              retention_msecs=config.metrics_retention_duration,
                              duplicate_policy='last',
                              labels={
                                  "role_name": self.__context["role_name"],
                                  "type": 'pending'
                              })
        self.__logger.debug(f'Set {key} metric', value=pending_length)

    def inspecting_role(self):
        self.__logger.debug('Inspecting role')

    def queue_is_full(self):
        self.__logger.debug('Queue is full')
