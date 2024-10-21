from enum import Enum


class Status(str, Enum):
    OFFLINE = 'offline'
    ONLINE = 'online'
    ACTIVE = 'active'


class Role(str, Enum):
    FIRST_LADY = 'First Lady'
    SECRETARY_OF_STRATEGY = 'Secretary of Strategy'
    SECRETARY_OF_SECURITY = 'Secretary of Security'
    SECRETARY_OF_DEVELOPMENT = 'Secretary of Development'
    SECRETARY_OF_SCIENCE = 'Secretary of Science'
    SECRETARY_OF_INTERIOR = 'Secretary of Interior'


class Reason(str, Enum):
    BANNED_PLAYER = 'Player is banned'
    BANNED_ALLIANCE = 'Alliance is banned'
    PRIORITY_TO_NAP_ALLIANCES = 'Queue has priority to NAP alliances'
    PRIORITY_TO_NAP_AND_SVS_ALLIANCES = "Queue has priority to NAP and SvS alliances"
    APPLIED_FOR_FIRST_LADY = 'Player applied for First Lady'
    APPOINTMENT_WOULD_BE_DURING_CAPITOL_WAR = 'Appointment would be during capitol war'


def sanitize_role(role: Role):
    return role.replace(" ", "_").lower()
