from enum import Enum
from typing import Literal

class BaseActionType(Enum):
    SIT = "SIT"
    STAND = "STAND"
    TWIST= "TWIST"
    WALK= "WALK"
    UNKNOWN = "UNKNOW"
    ERROR = "ERROR"
    DAMPING = "DAMPING"
    FALLOVER = "ERROR_FALLOVER"
    RECOVER = "RECOVER"
    HEIGHT="HEIGHT"
    LIGHT="LIGHT"


ACTION_VALUES = tuple(action.value for action in BaseActionType)
ACTION_TYPE = Literal[ACTION_VALUES]  # type: ignore
if __name__=="__main__":
    status="UNKNOWN"
    print(BaseActionType._member_map_[status])

