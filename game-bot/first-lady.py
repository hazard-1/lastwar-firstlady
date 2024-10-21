import atexit
import datetime
import os
import signal
import sys
from typing import Optional
from redis import Redis
import logging
from appium.webdriver.webdriver import AppiumOptions, WebDriver
from selenium.webdriver.support.wait import WebDriverWait
import config
import structlog
from events import Events
from model import Reason, Role, Status
from utility import get_time_limit, parse_name
from view import CapitolView, HomeView, ListView, ProfileView, RoleView

QUEUE_MAX_LENGTH = 50
MY_USERNAME = "Bitney"


options = AppiumOptions().load_capabilities(
    {
        "platformName": "Android",
        "appium:udid": "emulator-5554",
        "appium:appPackage": "com.fun.lastwar.gp",
        "appium:appActivity": "com.im30.aps.debug.UnityPlayerActivityCustom",
        "appium:deviceName": "Pixel 8 API 35",
        "appium:automationName": "UiAutomator2",
        "appium:platformVersion": "13",
        "appium:autoGrantPermissions": True,
        "appium:noReset": True,
        "appium:fullReset": False
    }
)


def should_deny(alliance, player_name: str, queue_length: int):
    if player_name in config.bans['players']:
        return Reason.BANNED_PLAYER

    if alliance['name'] in config.bans['alliances']:
        return Reason.BANNED_ALLIANCE

    is_nap_alliance = alliance['type'] == 'NAP'
    is_svs_alliance = alliance['type'] == 'SVS'
    is_nap_or_svs_alliance = is_nap_alliance or is_svs_alliance

    if not is_nap_alliance and queue_length > config.queues['thresholds']['high']:
        return Reason.PRIORITY_TO_NAP_ALLIANCES

    if not is_nap_or_svs_alliance and queue_length > config.queues['thresholds']['low']:
        return Reason.PRIORITY_TO_NAP_AND_SVS_ALLIANCES

    return None


class FirstLady():
    am_first_lady = False
    events: Events
    logger: structlog.stdlib.BoundLogger

    def __init__(self, webdriver: WebDriver, redis: Optional[Redis], logger: structlog.stdlib.BoundLogger):
        self.events = Events(redis, logger)
        self.driver = webdriver
        self.logger = logger

    def start(self) -> None:
        self.events.starting_bot()
        self._reset()
        self._start_bot()

    def _start_bot(self) -> None:
        HomeView.open_profile(self.driver)
        ProfileView.get_server_number(self.driver)
        ProfileView.open_capitol(self.driver)
        CapitolView.open_first_role(self.driver)
        self.events.publish_bot_status(Status.ONLINE)
        self._run()

    def _reset(self) -> None:
        def quit_game_modal_is_open(driver: WebDriver):
            driver.back()
            return HomeView.is_quit_game_modal_open(driver)

        WebDriverWait(self.driver, 120, poll_frequency=0.5).until(
            quit_game_modal_is_open)
        self.driver.back()

    def _manage_applicants(self, role_name, queue_length):
        role_scope = self.events.with_context(
            role_name=role_name)

        pending_length = ListView.get_pending_applicants_count(self.driver)
        role_scope.set_pending_count(pending_length)

        if not self.am_first_lady:
            return

        if pending_length == 0:
            role_scope.no_pending_applicants()
            return

        # Scroll to the top of the list
        if pending_length > 5:
            ListView.swipe_up_to_top(self.driver, pending_length)

        while queue_length < QUEUE_MAX_LENGTH:
            scope = role_scope.with_context(queue_length=queue_length)

            pending_applicant = ListView.get_applicant(self.driver)
            if pending_applicant is None:
                role_scope.no_pending_applicants()
                return

            alliance, player_name = parse_name(pending_applicant)
            applicant_scope = scope.with_context(role_name=role_name,
                                                 player_name=player_name)
            if alliance is not None:
                applicant_scope = applicant_scope.with_context(
                    alliance_name=alliance['name'])

            reason = Reason.APPLIED_FOR_FIRST_LADY if role_name == Role.FIRST_LADY else should_deny(
                alliance, player_name, queue_length)

            # All checks passed so approve, otherwise deny with the reason
            if reason is None:
                ListView.approve_next_in_line(self.driver)
                applicant_scope.approved_applicant()
            else:
                ListView.deny_next_in_line(self.driver)
                applicant_scope.denied_applicant(reason=reason)

            # Confirm the change worked - a different player or no player should be next in line.
            next_applicant = ListView.get_applicant(self.driver)
            if pending_applicant == next_applicant:
                applicant_scope.applicant_is_still_pending()

            if reason is None:
                queue_length = queue_length + 1

            pending_length = pending_length - 1
            role_scope.set_queue_count(queue_length)
            role_scope.set_pending_count(pending_length)

            # When in dry run mode, as no change will have been made this becomes a loop until queue_count = 50, so exit early.
            if config.dry_run:
                break

    def _enforce_time_limits(self, role_name: str, alliance, player_name: str) -> None:
        time_in_office = RoleView.get_time_in_office(self.driver)
        role_time_limit = get_time_limit(role_name)

        scope = self.events.with_context(
            role_name=role_name,
            player_name=player_name,
            role_time_limit=role_time_limit,
            time_in_office=time_in_office)

        if alliance is not None:
            scope = scope.with_context(alliance_name=alliance['name'])

        if time_in_office > role_time_limit:
            if self.am_first_lady:
                RoleView.dismiss(self.driver)
                scope.dismissed_player()

    def _run(self) -> None:
        self.am_first_lady = config.dry_run
        while True:
            role_name, role_assignee, queue_length = RoleView.get_role_info(
                self.driver)
            alliance, player_name = parse_name(role_assignee)
            role_scope = self.events.with_context(role_name=role_name)
            role_scope.set_queue_count(queue_length)

            assignee_scope = role_scope.with_context(
                assignee_player_name=player_name)

            if alliance is not None:
                assignee_scope = assignee_scope.with_context(
                    assignee_alliance_name=alliance['name'])

            assignee_scope.inspecting_role()

            # Check that the bot is currently the first lady, if not just keep polling until someone appoints it
            if role_name == Role.FIRST_LADY:
                if role_assignee == config.username:
                    self.am_first_lady = True
                assignee_scope.first_lady_status(self.am_first_lady)

            if role_name == None:
                role_scope.failed_to_read_role_name()
                RoleView.go_to_next_role(self.driver)
                continue

            self.events.publish_bot_status(
                Status.ACTIVE if self.am_first_lady else Status.ONLINE)

            # Don't manage full queues
            if queue_length >= QUEUE_MAX_LENGTH:
                role_scope.queue_is_full()
                RoleView.go_to_next_role(self.driver)
                continue

            # Manage the applicants.
            RoleView.open_list(self.driver)
            self._manage_applicants(role_name, queue_length)
            ListView.go_back_to_role(self.driver)

            if role_name != Role.FIRST_LADY and player_name is not None:
                self._enforce_time_limits(role_name, alliance, player_name)

            # Don't refresh until after the last one.
            if role_name != Role.SECRETARY_OF_INTERIOR:
                RoleView.go_to_next_role(self.driver)
                continue

            # Refresh all the changes as the game doesn't update from within a role view.
            RoleView.go_back_to_capitol(self.driver)
            CapitolView.open_first_role(self.driver)

            # Reload the config in case anything changed.
            config.load()


first_lady: FirstLady


def exit_handler():
    first_lady.events.publish_bot_status(Status.OFFLINE)


def kill_handler(*args):
    sys.exit(0)


structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # structlog.processors.JSONRenderer()
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

if __name__ == '__main__':
    logger = structlog.get_logger()

    redis: Optional[Redis]
    if os.getenv('REDIS_HOST'):
        redis = Redis(
                    host=os.getenv('REDIS_HOST'), 
                    port=os.getenv('REDIS_PORT') or 6379, 
                    db=os.getenv('REDIS_DB') or 0)
        redis.ping()
    
    if os.getenv('CONFIG_SOURCE') == 'redis':
        config.set_config_loader(config.use_redis_config(redis))
    elif os.getenv('CONFIG_SOURCE') == 'json':
        config.set_config_loader(config.use_json_config(os.getenv('CONFIG_PATH') or 'config.json'))
    else:
        config.set_config_loader(config.use_yaml_config(os.getenv('CONFIG_PATH') or 'config.yaml'))
        
    config.load()

    atexit.register(exit_handler)
    signal.signal(signal.SIGINT, kill_handler)
    signal.signal(signal.SIGTERM, kill_handler)

    first_lady = FirstLady(webdriver=WebDriver('http://127.0.0.1:4723', options=options),
                           redis=redis,
                           logger=logger)
    try:
        first_lady.start()
    except BaseException as err:
        logger.error("Unhandled exception", error=err)
        sys.exit(1)
        raise err
