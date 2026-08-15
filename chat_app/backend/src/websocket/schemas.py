from datetime import datetime

from pydantic import UUID4, BaseModel

# TODO: Add data validation


class ReceiveMessageSchema(BaseModel):
    user_guid: UUID4
    chat_guid: UUID4
    content: str


class SendMessageSchema(BaseModel):
    type: str = "new"
    message_guid: UUID4
    user_guid: UUID4
    chat_guid: UUID4
    content: str
    created_at: datetime
    is_read: bool | None = False

class SendFileSchema(BaseModel):
    type: str = "new_file"  # Indicating it's a new file message
    message_guid: str
    chat_guid: str
    user_guid: str
    file_data: str  # Base64 encoded file data
    file_extension: str
    created_at: datetime
    is_read: bool = False
    is_new: bool = True
    file_s3url: str
class MessageReadSchema(BaseModel):
    type: str
    chat_guid: UUID4
    message_guid: UUID4


class UserTypingSchema(BaseModel):
    type: str
    chat_guid: UUID4
    user_guid: UUID4


class NewChatCreated(BaseModel):
    type: str = "new_chat_created"
    chat_id: int  # need to pass for guid/id mapping [chats variable]
    chat_guid: UUID4
    created_at: datetime
    updated_at: datetime
    friend: dict
    has_new_messages: bool
    new_messages_count: int


class AddUserToChatSchema(BaseModel):
    chat_guid: str  # used for websocket communication
    chat_id: int


class NotifyChatRemovedSchema(BaseModel):
    type: str = "chat_deleted"
    chat_guid: str
