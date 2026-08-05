import logging
from datetime import datetime
from uuid import UUID
import base64
import boto3
import uuid
from typing import List, Tuple, Optional
from urllib.parse import urlparse

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from src.chat.schemas import GetDirectChatSchema, GetMessageSchema
from src.models import Chat, ChatType, Message, ReadStatus, User, ECCKey, EncryptedFile
from src.websocket.crypto_utils import ecc_decrypt, aes_decrypt
from src.config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

async def create_direct_chat(db_session: AsyncSession, *, initiator_user: User, recipient_user: User) -> Chat:
    try:
        chat = Chat(chat_type=ChatType.DIRECT)
        chat.users.append(initiator_user)
        chat.users.append(recipient_user)
        db_session.add(chat)
        await db_session.flush()

        # make empty read statuses for both users last_read_message_id = 0
        initiator_read_status = ReadStatus(chat_id=chat.id, user_id=initiator_user.id, last_read_message_id=0)
        recipient_read_status = ReadStatus(chat_id=chat.id, user_id=recipient_user.id, last_read_message_id=0)
        db_session.add_all([initiator_read_status, recipient_read_status])
        await db_session.commit()

    except Exception as exc_info:
        await db_session.rollback()
        raise exc_info

    else:
        return chat


async def get_direct_chat_by_users(
    db_session: AsyncSession, *, initiator_user: User, recipient_user: User
) -> Chat | None:
    query = select(Chat).where(
        and_(
            Chat.chat_type == ChatType.DIRECT, Chat.users.contains(initiator_user), Chat.users.contains(recipient_user)
        )
    )

    result = await db_session.execute(query)
    chat: Chat | None = result.scalar_one_or_none()

    return chat


async def get_chat_by_guid(db_session: AsyncSession, *, chat_guid: UUID) -> Chat | None:
    query = (
        select(Chat)
        .where(Chat.guid == chat_guid)
        .options(selectinload(Chat.messages), selectinload(Chat.users), selectinload(Chat.read_statuses))
    )
    result = await db_session.execute(query)
    chat: Chat | None = result.scalar_one_or_none()

    return chat


async def get_user_by_guid(db_session: AsyncSession, *, user_guid: UUID) -> User | None:
    query = select(User).where(User.guid == user_guid)
    result = await db_session.execute(query)
    user: User | None = result.scalar_one_or_none()

    return user


async def get_new_messages_per_chat(
    db_session: AsyncSession, chats: list[Chat], current_user: User
) -> list[GetDirectChatSchema]:
    """
    New message are those messages that:
    - don't belong to current user
    - are not yet read by current user

    """
    # Create a dictionary with default values of 0
    new_messages_count_per_chat = {chat.id: 0 for chat in chats}

    # Create an alias for the ReadStatus table
    read_status_alias = aliased(ReadStatus)

    query = (
        select(Message.chat_id, func.count().label("message_count"))
        .join(
            read_status_alias,
            and_(read_status_alias.user_id == current_user.id, read_status_alias.chat_id == Message.chat_id),
        )
        .where(
            and_(
                Message.user_id != current_user.id,
                Message.id > func.coalesce(read_status_alias.last_read_message_id, 0),
                Message.is_deleted.is_(False),
                Message.chat_id.in_(new_messages_count_per_chat),
            )
        )
        .group_by(Message.chat_id)
    )

    result = await db_session.execute(query)
    new_messages_count = result.fetchall()

    for messages_count in new_messages_count:
        new_messages_count_per_chat[messages_count[0]] = messages_count[1]

    return [
        GetDirectChatSchema(
            chat_guid=chat.guid,
            chat_type=chat.chat_type,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            users=chat.users,
            new_messages_count=new_messages_count_per_chat[chat.id],
        )
        for chat in chats
    ]


async def get_user_direct_chats(db_session: AsyncSession, *, current_user: User) -> list[Chat]:
    query = (
        select(Chat)
        .where(
            and_(
                Chat.users.contains(current_user),
                Chat.is_deleted.is_(False),
                Chat.chat_type == ChatType.DIRECT,
            )
        )
        .options(selectinload(Chat.users))
    ).order_by(Chat.updated_at.desc())
    result = await db_session.execute(query)

    chats: list[Chat] = result.scalars().all()

    return chats


async def direct_chat_exists(db_session: AsyncSession, *, current_user: User, recipient_user: User) -> bool:
    query = select(Chat.id).where(
        and_(
            Chat.chat_type == ChatType.DIRECT,
            Chat.is_deleted.is_(False),
            Chat.users.contains(current_user),
            Chat.users.contains(recipient_user),
        )
    )
    result = await db_session.execute(query)
    existing_chat = result.scalar_one_or_none()
    return existing_chat is not None


async def decrypt_file_message(db_session: AsyncSession, message: Message) -> Optional[str]:
    if not message.file_path:
        return None
    try:
        # Extract S3 key
        parsed_url = urlparse(message.file_path)
        s3_key = parsed_url.path.lstrip("/")
        
        # Initialize boto3 S3 client
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME,
        )
        s3_bucket = settings.AWS_IMAGES_BUCKET
        
        logger.info(f"Fetching encrypted file from S3: {s3_key}")
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        encrypted_file_bytes = response['Body'].read()
        
        # Get EncryptedFile record
        result = await db_session.execute(
            select(EncryptedFile).where(EncryptedFile.filename == s3_key)
        )
        encrypted_file_record = result.scalar_one_or_none()
        
        if encrypted_file_record:
            # Get recipient's ECC private key
            result = await db_session.execute(
                select(ECCKey).where(ECCKey.user_guid == encrypted_file_record.user_guid)
            )
            recipient_ecc_key = result.scalar_one_or_none()
            if recipient_ecc_key:
                logger.info(f"Decrypting AES key with private key for user: {recipient_ecc_key.user_guid}")
                # Decrypt AES key using recipient's ECC private key
                aes_key = ecc_decrypt(encrypted_file_record.encrypted_key, recipient_ecc_key.private_key)
                # Decrypt file bytes using AES key
                decrypted_file_bytes = aes_decrypt(encrypted_file_bytes, aes_key)
                return base64.b64encode(decrypted_file_bytes).decode('utf-8')
            else:
                logger.error(f"ECC private key not found for user: {encrypted_file_record.user_guid}")
                return base64.b64encode(encrypted_file_bytes).decode('utf-8')
        else:
            logger.warning(f"EncryptedFile record not found for S3 key: {s3_key}. Returning raw data.")
            return base64.b64encode(encrypted_file_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Error decrypting file message {message.guid}: {e}")
        return None


async def get_chat_messages(
    db_session: AsyncSession, *, user_id: int, chat: Chat, size: int
) -> tuple[list[GetMessageSchema], bool, Message | None]:
    query = (
        select(Message)
        .where(and_(Message.chat_id == chat.id, Message.is_deleted.is_(False)))
        .order_by(Message.created_at.desc())
        .limit(size + 1)
        .options(selectinload(Message.user), selectinload(Message.chat))
    )
    result = await db_session.execute(query)
    messages: list[Message] = result.scalars().all()
    # check if there are more messages
    has_more_messages = len(messages) > size
    messages = messages[:size]

    # assuming only two read statuses
    for read_status in chat.read_statuses:
        if read_status.user_id != user_id:
            other_user_last_read_message_id = read_status.last_read_message_id
        else:
            my_last_read_message_id = read_status.last_read_message_id

    last_read_message = await db_session.get(Message, other_user_last_read_message_id)
    
    get_message_schemas = []
    for message in messages:
        message_type_str = message.message_type.value if hasattr(message.message_type, "value") else str(message.message_type)
        file_data = None
        if message_type_str == "file":
            file_data = await decrypt_file_message(db_session, message)
        
        get_message_schemas.append(
            GetMessageSchema(
                message_guid=message.guid,
                content=message.content or "",
                created_at=message.created_at,
                chat_guid=message.chat.guid,
                user_guid=message.user.guid,
                is_read=message.id
                <= (other_user_last_read_message_id if message.user.id == user_id else my_last_read_message_id),
                message_type=message_type_str,
                file_name=message.file_name,
                file_s3url=message.file_path,
                file_data=file_data,
            )
        )

    return get_message_schemas, has_more_messages, last_read_message


async def get_active_message_by_guid_and_chat(
    db_session: AsyncSession, *, chat_id: int, message_guid: UUID
) -> Message | None:
    query = select(Message).where(
        and_(Message.guid == message_guid, Message.is_deleted.is_(False), Message.chat_id == chat_id)
    )

    result = await db_session.execute(query)
    message: Message | None = result.scalar_one_or_none()

    return message


# async def get_older_chat_messages(
#     db_session: AsyncSession,
#     *,
#     chat: Chat,
#     user_id: int,
#     limit: int = 10,
#     created_at: datetime,
# ) -> Tuple[List[GetMessageSchema], bool]:
#     logger.debug(f"Fetching older messages for chat {chat.guid}, user {user_id}, before {created_at}")

#     query = (
#         select(Message)
#         .where(
#             and_(
#                 Message.chat_id == chat.id,
#                 Message.is_deleted.is_(False),
#                 Message.created_at < created_at,
#             )
#         )
#         .order_by(Message.created_at.desc())
#         .limit(limit + 1)  # Fetch limit + 1 messages to check 'has_more_messages'
#         .options(selectinload(Message.user), selectinload(Message.chat))
#     )

#     logger.debug(f"Executing query: {query.compile(compile_kwargs={'literal_binds': True})}")
#     result = await db_session.execute(query)
#     older_messages: List[Message] = result.scalars().all()
    
#     logger.debug(f"Fetched {len(older_messages)} messages from DB")

#     has_more_messages = len(older_messages) > limit
#     older_messages = older_messages[:limit]  # Limit to requested amount

#     # Handle read statuses safely
#     other_user_last_read_message_id = None
#     my_last_read_message_id = None

#     for read_status in chat.read_statuses:
#         if read_status.user_id != user_id:
#             other_user_last_read_message_id = read_status.last_read_message_id
#         else:
#             my_last_read_message_id = read_status.last_read_message_id

#     formatted_messages = []
#     for message in older_messages:
#         is_read = (
#             message.id
#             <= (other_user_last_read_message_id if message.user.id == user_id else my_last_read_message_id)
#             if other_user_last_read_message_id is not None and my_last_read_message_id is not None
#             else False
#         )

#         message_type = message.message_type.value.lower()

#         formatted_message = GetMessageSchema(
#             message_guid=message.guid,
#             message_type=message_type,  # ✅ Ensure consistency
#             content=message.content if message_type == "text" else None,
#             created_at=message.created_at,
#             chat_guid=message.chat.guid,
#             user_guid=message.user.guid,
#             is_read=is_read,
#             file_name=message.file_name if message_type == "file" else None,
#             file_path=message.file_path if message_type == "file" else None,  # ✅ Fixed file type check
#         )

#         logger.debug(f"Formatted message: {formatted_message.dict()}")
#         formatted_messages.append(formatted_message)

#     logger.debug(f"Returning {len(formatted_messages)} messages, has more: {has_more_messages}")

#     return formatted_messages, has_more_messages

async def get_older_chat_messages(
    db_session: AsyncSession,
    *,
    chat: Chat,
    user_id: int,
    limit: int = 10,
    created_at: datetime,
) -> tuple[list[GetMessageSchema], bool]:
    query = (
        select(Message)
        .where(
            and_(
                Message.chat_id == chat.id,
                Message.is_deleted.is_(False),
                Message.created_at < created_at,
            )
        )
        .order_by(Message.created_at.desc())
        .limit(limit + 1)  # Fetch limit + 1 messages
        .options(selectinload(Message.user), selectinload(Message.chat))
    )

    result = await db_session.execute(query)
    older_messages: list[Message] = result.scalars().all()

    # Determine if there are more messages
    has_more_messages = len(older_messages) > limit
    older_messages = older_messages[:limit]

    # assuming only two read statuses
    for read_status in chat.read_statuses:
        if read_status.user_id != user_id:
            other_user_last_read_message_id = read_status.last_read_message_id
        else:
            my_last_read_message_id = read_status.last_read_message_id

    get_message_schemas = []
    for message in older_messages:
        message_type_str = message.message_type.value if hasattr(message.message_type, "value") else str(message.message_type)
        file_data = None
        if message_type_str == "file":
            file_data = await decrypt_file_message(db_session, message)

        get_message_schemas.append(
            GetMessageSchema(
                message_guid=message.guid,
                content=message.content or "",
                created_at=message.created_at,
                chat_guid=message.chat.guid,
                user_guid=message.user.guid,
                is_read=message.id
                <= (other_user_last_read_message_id if message.user.id == user_id else my_last_read_message_id),
                message_type=message_type_str,
                file_name=message.file_name,
                file_s3url=message.file_path,
                file_data=file_data,
            )
        )

    # Return the first 'limit' messages and a flag indicating if there are more
    return get_message_schemas, has_more_messages

async def add_new_messages_stats_to_direct_chat(
    db_session: AsyncSession, *, current_user: User, chat: Chat
) -> GetDirectChatSchema:
    # new non-model (chat) fields are added
    has_new_messages: bool = False
    new_messages_count: int

    # assuming chat has two read statuses
    # current user's read status is used to determine new messages count
    for read_status in chat.read_statuses:
        # own read status -> for new messages
        if read_status.user_id == current_user.id:
            my_last_read_message_id = read_status.last_read_message_id

    new_messages_query = select(func.count()).where(
        and_(
            Message.user_id != current_user.id,
            Message.id > my_last_read_message_id,
            Message.is_deleted.is_(False),
            Message.chat_id == chat.id,
        )
    )
    result = await db_session.execute(new_messages_query)
    new_messages_count: int = result.scalar_one_or_none()
    if new_messages_count:
        has_new_messages = True

    return GetDirectChatSchema(
        chat_guid=chat.guid,
        chat_type=chat.chat_type,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        users=chat.users,
        has_new_messages=has_new_messages,
        new_messages_count=new_messages_count,
    )


async def get_unread_messages_count(db_session: AsyncSession, *, user_id: int, chat: Chat) -> int:
    # Get the user's last read message ID in the chat
    user_read_status = next((rs for rs in chat.read_statuses if rs.user_id == user_id), None)
    if not user_read_status:
        return 0  # User has no read status in this chat

    user_last_read_message_id = user_read_status.last_read_message_id

    # Count the number of unread messages for the user
    query = select(func.count()).where(
        and_(
            Message.chat_id == chat.id,
            Message.is_deleted.is_(False),
            Message.id > user_last_read_message_id,
        )
    )

    result = await db_session.execute(query)
    unread_messages_count = result.scalar()

    return unread_messages_count
