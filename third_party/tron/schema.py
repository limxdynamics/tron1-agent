from typing import List, Optional
from pydantic import BaseModel, Field

from register import ACTION_TYPE
import logging
import os
import json
logger = logging.getLogger(__name__)

class Message(BaseModel):
    """Represents a chat message in the conversation"""

    data: Optional[dict] = Field(default=None)
    status: Optional[ACTION_TYPE] =  Field(...) # type: ignore j机器人状态
    timestamp: Optional[float] = Field(default=None)
    message: Optional[str] = Field(default=None)
    accid: Optional[str] = Field(default=None) #机器人标识
    guid: Optional[str] = Field(default=None) #机器人标识
    request: Optional[str] = Field(default=None) #机器人标识

    def __add__(self, other) -> List["Message"]:
        """支持 Message + list 或 Message + Message 的操作"""
        if isinstance(other, list):
            return [self] + other # type: ignore
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other) -> List["Message"]:
        """支持 list + Message 的操作"""
        if isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    def to_dict(self) -> dict:
        """Convert message to dictionary format"""
        _message = {}
        if self.accid is not None:
            _message["accid"] = self.accid # type: ignore
        if self.status is not None:
            _message["status"] = self.status
        if self.timestamp is not None:
            _message["timestamp"] = self.timestamp # type: ignore
        if self.message is not None:
            _message["message"] = self.message # type: ignore
        if self.data is not None:
            _message["data"] = self.data # type: ignore
        if self.guid is not None:
            _message["guid"] = self.guid # type: ignore
        if self.request is not None:
            _message["request"] = self.request # type: ignore
        return _message

    @classmethod
    def register_message(cls, **kwargs) -> "Message":
        """Create a user message"""
        return cls(**kwargs)


class Memory(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    max_messages: int = Field(default=100)
    def add_message(self, message: Message) -> None:
        """Add a message to memory"""
        self.messages.append(message)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]
    def add_messages(self, messages: List[Message]) -> None:
        """Add multiple messages to memory"""
        self.messages.extend(messages)

    def clear(self) -> None:
        """Clear all messages"""
        self.messages.clear()

    def get_recent_messages(self, n: int) -> List[Message]:
        """Get n most recent messages"""
        try:
            return self.messages[-n:]
        except:
            return []

    def to_dict_list(self) -> List[dict]:
        """Convert messages to list of dicts"""
        return [msg.to_dict() for msg in self.messages]
    
    def dump_messages_to_jsonl(self, file_path: str):
        """Dump messages to a JSONL file"""
        file_name = os.path.join(file_path, f"action_memory.jsonl")

        with open(file_name, 'w', encoding='utf-8') as file:
            for message in self.to_dict_list():
                json.dump(message, file, ensure_ascii=False)
                file.write('\n')
        return file_name
    