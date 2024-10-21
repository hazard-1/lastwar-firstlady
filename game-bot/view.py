import datetime
import config
from selenium.webdriver.support.wait import WebDriverWait
from cv2.typing import MatLike
import time
import cv2
from model import Role
from utility import capture, extract_coordinates, read_text_from_image
import re
import math

CAPITOL_ROI_SERVER_NUMBER = [
    (115, 135),
    (500, 242)
]
CAPITOL_ROI_CONQUEROR = [
    (262, 274),
    (872, 598)
]
CAPITOL_ROI_PRESIDENT = [
    (442, 750),
    (655, 807)
]
CAPITOL_ACTION_VIEW_FIRST_ROLE_NO_CONQUEROR = (235, 1032)
CAPITOL_ACTION_VIEW_FIRST_ROLE_CONQUEROR = (235, 1462)


class CapitolView():
    @staticmethod
    def open_first_role(driver):
        PopupsView.dismiss_awesome(driver)
        WebDriverWait(driver, 10, poll_frequency=0.1).until(
            CapitolView.is_capitol_open)
        if not CapitolView.is_conqueror(driver):
            driver.tap([CAPITOL_ACTION_VIEW_FIRST_ROLE_NO_CONQUEROR])
        else:
            driver.tap([CAPITOL_ACTION_VIEW_FIRST_ROLE_CONQUEROR])
        WebDriverWait(driver, 10, poll_frequency=0.1).until(
            RoleView.is_role_open)

    @staticmethod
    def is_capitol_open(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(CAPITOL_ROI_SERVER_NUMBER)
        text = ''.join(read_text_from_image(img[y1:y2, x1:x2])).lower()
        return text.startswith('#')

    @staticmethod
    def is_conqueror(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(CAPITOL_ROI_CONQUEROR)
        text = ''.join(read_text_from_image(
            img[y1:y2, x1:x2])).lower().replace(" ", '')
        return len(text) > 0
        return 'onqueror' in text


HOME_ROI_HEROES = [
    (19, 2310),
    (229, 2387)
]
HOME_ROI_QUIT_GAME_CONFIMATION = [
    (397, 1071),
    (703, 1142)
]
HOME_ACTION_OFFSCREEN_NOOP = (1, 1)
HOME_ACTION_VIEW_PROFILE = (100, 219)


class HomeView():
    @staticmethod
    def is_quit_game_modal_open(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(HOME_ROI_QUIT_GAME_CONFIMATION)
        text = ''.join(read_text_from_image(img[y1:y2, x1:x2]))
        return text == "Quit the game?"

    @staticmethod
    def is_heroes_button_present(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(HOME_ROI_HEROES)
        text = ''.join(read_text_from_image(img[y1:y2, x1:x2]))
        return text.lower() == 'heroes'

    @staticmethod
    def open_profile(driver):

        WebDriverWait(driver, 10, poll_frequency=0.5).until(
            HomeView.is_heroes_button_present)

        PopupsView.dismiss_awesome(driver)
        driver.tap([HOME_ACTION_VIEW_PROFILE])
        PopupsView.dismiss_awesome(driver)

        WebDriverWait(driver, 10, poll_frequency=0.5).until(
            ProfileView.is_profile_open)


LIST_ROI_TITLE = [
    (55, 445),
    (968, 526)
]
LIST_ROI_APPLICANT = [
    (258, 683),
    (981, 742)
]
LIST_ACTION_APPROVE = (807, 749)
LIST_ACTION_DENY = (930, 737)
LIST_ROI_DENY_ARE_YOU_SURE = [(106, 1008), (967, 1200)]
LIST_ACTION_DENY_CONFIRM = (721, 1454)
LIST_ACTION_CLOSE = (1003, 506)

LIST_ROI_NO_PENDING_APPLICANTS = [(248, 1332), (848, 1387)]
LIST_ROI_APPLICANTS_COUNT = [(335, 594), (790, 645)]
LIST_ACTION_SCROLL_LIST = [
    (545, 760),
    (545, 1923)
]


class ListView():
    @staticmethod
    def get_applicant(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(LIST_ROI_APPLICANT)
        scale_factor = 4
        upscaled = cv2.resize(img[y1:y2, x1:x2], None, fx=scale_factor,
                              fy=scale_factor, interpolation=cv2.INTER_LINEAR)
        blur = cv2.blur(upscaled, (5, 5))
        text = ''.join(read_text_from_image(blur))
        return text if text != '' else None

    @staticmethod
    def go_back_to_role(driver):
        driver.tap([LIST_ACTION_CLOSE])
        WebDriverWait(driver, 10, poll_frequency=0.1).until(
            RoleView.is_role_open)

    @staticmethod
    def approve_next_in_line(driver):
        if config.dry_run:
            return
        driver.tap([LIST_ACTION_APPROVE])
        time.sleep(1)

    @staticmethod
    def swipe_up_to_top(driver, pending_applicants):
        for i in range(math.floor(pending_applicants / 5)):
            # logger.debug('Scrolling to top')
            driver.swipe(
                *LIST_ACTION_SCROLL_LIST[0],
                *LIST_ACTION_SCROLL_LIST[1],
                200)
        time.sleep(1)

    @staticmethod
    def deny_next_in_line(driver):
        if config.dry_run:
            return

        driver.tap([LIST_ACTION_DENY])

        # Wait for confirmation modal
        WebDriverWait(driver, 10, poll_frequency=0.1).until(
            ListView.is_deny_modal_open)

        driver.tap([LIST_ACTION_DENY_CONFIRM])

        # Wait for list to be present again
        WebDriverWait(driver, 10, poll_frequency=0.2).until(
            ListView.is_list_open
        )

    @staticmethod
    def is_list_open(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(LIST_ROI_TITLE)
        text = ''.join(read_text_from_image(img[y1:y2, x1:x2])).lower()
        return text.startswith('officer')

    @staticmethod
    def get_pending_applicants_count(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(LIST_ROI_APPLICANTS_COUNT)
        text = ''.join(read_text_from_image(img[y1:y2, x1:x2])).replace(
            ' ', '').replace('z', '2').replace('o', '0').replace('O', '0')

        if not text.startswith('Applicants'):
            return 0

        start = text.index('[')
        end = text.index('/')

        count = text[start+1:end]
        return int(count)

    @staticmethod
    def is_deny_modal_open(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(LIST_ROI_DENY_ARE_YOU_SURE)
        text = ''.join(read_text_from_image(
            img[y1:y2, x1:x2])).lower().replace(' ', '')
        return 'cancel' in text


POPUP_ROI_AWESOME = [(185, 586), (900, 700)]
POPUP_ACTION_AWESOME = (545, 1724)


class PopupsView():
    @staticmethod
    def is_awesome_open(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(POPUP_ROI_AWESOME)
        text = ''.join(read_text_from_image(
            img[y1:y2, x1:x2])).lower().replace("!", "")
        return text.endswith("awesome")

    @staticmethod
    def dismiss_awesome(driver):
        def awesome_dismissed(driver):
            if not PopupsView.is_awesome_open(driver):
                return True
            driver.tap([POPUP_ACTION_AWESOME])
            return False

        time.sleep(0.5)
        WebDriverWait(driver, 10, poll_frequency=1).until(awesome_dismissed)


PROFILE_ROI_SERVER_NUMBER = [(745, 1503), (932, 1600)]
PROFILE_ACTION_VIEW_CAPITOL = (813, 1552)


class ProfileView():
    @staticmethod
    def open_capitol(driver):
        PopupsView.dismiss_awesome(driver)
        driver.tap([PROFILE_ACTION_VIEW_CAPITOL])
        PopupsView.dismiss_awesome(driver)

    @staticmethod
    def is_profile_open(driver):
        return ProfileView.get_server_number(driver) > 0

    @staticmethod
    def get_server_number(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(PROFILE_ROI_SERVER_NUMBER)
        scale_factor = 2
        upscaled = cv2.resize(img[y1:y2, x1:x2], None, fx=scale_factor,
                              fy=scale_factor, interpolation=cv2.INTER_LINEAR)
        blur = cv2.blur(upscaled, (5, 5))
        text = ''.join(read_text_from_image(blur)).replace('o', '0').replace(
            'O', '0').replace('z', '2').replace('Z', '2').replace('s', '5').replace('S', '5')
        matches = re.match('#\d+', text)
        if matches:
            return int(text.removeprefix('#'))
        return 0


ROLE_ROI_NAME = [
    (55, 445),
    (968, 526)
]
ROLE_ROI_ASSIGNEE = [
    (83, 794),
    (1095, 862)
]

ROLE_ROI_QUEUE_LENGTH: dict[Role, list[tuple[int, int]]] = {
    Role.FIRST_LADY: [(80, 1290), (995, 1352)],  # 4
    Role.SECRETARY_OF_STRATEGY: [(80, 1123), (995, 1171)],  # 2
    Role.SECRETARY_OF_SECURITY: [(80, 1123), (995, 1171)],  # 2
    Role.SECRETARY_OF_DEVELOPMENT: [(80, 1123), (995, 1171)],  # 2
    Role.SECRETARY_OF_SCIENCE: [(80, 1123), (995, 1171)],  # 2
    Role.SECRETARY_OF_INTERIOR: [(80, 1206), (995, 1265)],  # 3
}
ROLE_ACTION_GO_TO_NEXT = (948, 739)
ROLE_ACTION_OPEN_LIST = (939, 1916)
ROLE_ACTION_CLOSE = (1003, 506)
ROLE_ACTION_DISMISS = (389, 1945)

ROLE_ROI_DISMISS_ARE_YOU_SURE = [(213, 1040), (881, 1163)]
ROLE_ACTION_DISMISS_CONFIRM = (344, 1270)

ROLE_ROI_TIME_IN_OFFICE = [(328, 848), (782, 922)]


def get_role_name(img: MatLike):
    x1, x2, y1, y2 = extract_coordinates(ROLE_ROI_NAME)
    scale_factor = 2
    upscaled = cv2.resize(img[y1:y2, x1:x2], None, fx=scale_factor,
                          fy=scale_factor, interpolation=cv2.INTER_LINEAR)
    blur = cv2.blur(upscaled, (5, 5))
    text = ''.join(read_text_from_image(blur)).upper().replace(" ", "")

    # The text detection of these is super janky even with tweaks on CV2 so just pick out the unique parts
    if 'FIRST' in text:
        return Role.FIRST_LADY

    if 'OFDE' in text:
        return Role.SECRETARY_OF_DEVELOPMENT

    if 'OFIN' in text:
        return Role.SECRETARY_OF_INTERIOR

    if 'OFSC' in text:
        return Role.SECRETARY_OF_SCIENCE

    if 'OFSE' in text:
        return Role.SECRETARY_OF_SECURITY

    if 'OFSTR' in text:
        return Role.SECRETARY_OF_STRATEGY

    return None


def get_role_assignee(img: MatLike):
    x1, x2, y1, y2 = extract_coordinates(ROLE_ROI_ASSIGNEE)
    scale_factor = 2
    upscaled = cv2.resize(img[y1:y2, x1:x2], None, fx=scale_factor,
                          fy=scale_factor, interpolation=cv2.INTER_LINEAR)
    blur = cv2.blur(upscaled, (5, 5))
    text = ''.join(read_text_from_image(blur))
    return text


def get_queue_length(img: MatLike, role_name: Role):
    x1, x2, y1, y2 = extract_coordinates(ROLE_ROI_QUEUE_LENGTH[role_name])
    text = ''.join(read_text_from_image(img[y1:y2, x1:x2])).replace(
        ' ', '').replace('z', '2').replace('o', '0').replace('O', '0')
    queue_length = re.sub(
        '[a-zA-Z]', '', text[-6:].split("/")[0].replace('[', ""))
    return int(queue_length)


class RoleView():
    @ staticmethod
    def is_role_open(driver):
        time.sleep(1)
        img = capture(driver)
        role_name = get_role_name(img)
        return role_name is not None

    @ staticmethod
    def is_dismiss_modal_open(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(ROLE_ROI_DISMISS_ARE_YOU_SURE)
        text = ''.join(read_text_from_image(img[y1:y2, x1:x2]))
        return 'remove' in text.lower().replace(' ', '')

    @ staticmethod
    def get_role_info(driver):
        img = capture(driver)
        role_name = get_role_name(img)
        role_assignee = get_role_assignee(img)
        queue_length = get_queue_length(img, role_name)
        return role_name, role_assignee, queue_length

    @ staticmethod
    def open_list(driver):
        driver.tap([ROLE_ACTION_OPEN_LIST])
        WebDriverWait(driver, 10, poll_frequency=0.1).until(
            ListView.is_list_open)

    @ staticmethod
    def go_to_next_role(driver):
        current_role_name = RoleView.get_role_info(driver)
        driver.tap([ROLE_ACTION_GO_TO_NEXT])
        time.sleep(1)

        def get_next_role_name(driver):
            time.sleep(1)
            next_role_name = RoleView.get_role_info(driver)
            if next_role_name != current_role_name:
                return next_role_name
            return False

        WebDriverWait(
            driver, 10, poll_frequency=0.1).until(get_next_role_name)

    @ staticmethod
    def go_back_to_capitol(driver):
        driver.tap([ROLE_ACTION_CLOSE])
        PopupsView.dismiss_awesome(driver)
        WebDriverWait(driver, 10, poll_frequency=0.1).until(
            CapitolView.is_capitol_open)

    @staticmethod
    def dismiss(driver):
        if config.dry_run:
            return
        driver.tap([ROLE_ACTION_DISMISS])
        WebDriverWait(driver, 10, poll_frequency=0.1).until(
            RoleView.is_dismiss_modal_open)
        driver.tap([ROLE_ACTION_DISMISS_CONFIRM])
        WebDriverWait(
            driver, 10, poll_frequency=0.2).until(RoleView.is_role_open)

    @staticmethod
    def get_time_in_office(driver):
        img = capture(driver)
        x1, x2, y1, y2 = extract_coordinates(ROLE_ROI_TIME_IN_OFFICE)
        text = ''.join(read_text_from_image(
            img[y1:y2, x1:x2]))
        if text == '':
            return datetime.timedelta()
        parsed = text[-8:].replace('.',
                                   ':').replace('o', '0').replace('O', '0').split(':')

        if len(parsed) == 0:
            return datetime.timedelta()

        duration = datetime.timedelta(
            hours=int(parsed[0]), minutes=int(parsed[1]), seconds=int(parsed[2]))
        return duration
