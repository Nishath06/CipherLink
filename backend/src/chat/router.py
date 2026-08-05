import json
import logging
from typing import Annotated
from uuid import UUID
import boto3
from typing import Optional
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.chat.schemas import (
    CreateDirectChatSchema,
    DisplayDirectChatSchema,
    GetDirectChatSchema,
    GetDirectChatsSchema,
    GetMessagesSchema,
    GetOldMessagesSchema,
)
import re
from urllib.parse import urlparse
from src.chat.services import (
    create_direct_chat,
    direct_chat_exists,
    get_active_message_by_guid_and_chat,
    get_chat_by_guid,
    get_chat_messages,
    get_new_messages_per_chat,
    get_older_chat_messages,
    get_unread_messages_count,
    get_user_by_guid,
    get_user_direct_chats,
)

from src.config import settings
from src.database import get_async_session
from src.dependencies import get_cache, get_cache_setting, get_current_user
from src.models import Chat, Message, User
from src.utils import clear_cache_for_get_direct_chats

chat_router = APIRouter(tags=["Chat Management"])

logger = logging.getLogger(__name__)
s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION_NAME,
)
s3_bucket = settings.AWS_IMAGES_BUCKET

@chat_router.post("/chat/direct/", summary="Create a direct chat", response_model=DisplayDirectChatSchema)
async def create_direct_chat_view(
    create_direct_chat_schema: CreateDirectChatSchema,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    # check if another user (recipient) exists
    recipient_user_guid = create_direct_chat_schema.recipient_user_guid
    recipient_user: User | None = await get_user_by_guid(db_session, user_guid=recipient_user_guid)

    # TODO: must check that recipient user is not the same as initiator
    if not recipient_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"There is no recipient user with provided guid [{recipient_user_guid}]",
        )

    if await direct_chat_exists(db_session, current_user=current_user, recipient_user=recipient_user):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Chat with recipient user exists [{recipient_user_guid}]"
        )

    # Check if the data is already in the cache
    chat: Chat = await create_direct_chat(db_session, initiator_user=current_user, recipient_user=recipient_user)

    return chat


@chat_router.get("/chat/{chat_guid}/messages/", summary="Get user's chat messages")
async def get_user_messages_in_chat(
    chat_guid: UUID,
    size: Annotated[int | None, Query(gt=0, lt=200)] = 20,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
    cache: aioredis.Redis = Depends(get_cache),
    cache_enabled: bool = Depends(get_cache_setting),
):
    chat: Chat | None = await get_chat_by_guid(db_session, chat_guid=chat_guid)

    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat with provided guid does not exist")

    # determine the number of unread messages
    unread_messages_count: int = await get_unread_messages_count(db_session, user_id=current_user.id, chat=chat)

    # get larger of provided messages size or unread messages
    size: int = max(size, unread_messages_count)

    # determine cache key
    cache_key: str = f"messages_{chat_guid}_{size}"

    if cache_enabled:
        # return cached chat messages if key exists
        if cached_chat_messages := await cache.get(cache_key):
            logger.info("Cache: Messages")
            return json.loads(cached_chat_messages)

    if current_user not in chat.users:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You don't have access to this chat")

    messages, has_more_messages, last_read_message = await get_chat_messages(
        db_session, user_id=current_user.id, chat=chat, size=size
    )
    response = GetMessagesSchema(
        messages=messages,
        has_more_messages=has_more_messages,
    )
    if last_read_message:
        response.last_read_message = last_read_message

    if cache_enabled:
        # Store the chat in the cache with a TTL
        await cache.set(cache_key, response.model_dump_json(), ex=settings.REDIS_CACHE_EXPIRATION_SECONDS)

    return response


# TODO: when to clear the cache?
@chat_router.get("/chats/direct/", summary="Get user's direct chats")
async def get_user_chats_view(
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
    cache: aioredis.Redis = Depends(get_cache),
    cache_enabled: bool = Depends(get_cache_setting),
):
    # return cached direct chats if key exists
    cache_key = f"direct_chats_{current_user.guid}"
    if cached_direct_chats := await cache.get(cache_key):
        logger.info("Cache: Chats")
        return json.loads(cached_direct_chats)

    chats: list[Chat] = await get_user_direct_chats(db_session, current_user=current_user)

    chats_with_new_messages_count: list[GetDirectChatSchema] = await get_new_messages_per_chat(
        db_session, chats, current_user
    )

    # calculate total unread messages count for all user's chats
    total_unread_messages_count = sum(direct_chat.new_messages_count for direct_chat in chats_with_new_messages_count)

    response = GetDirectChatsSchema(
        chats=chats_with_new_messages_count, total_unread_messages_count=total_unread_messages_count
    )

    if cache_enabled:
        # Store response in the cache with a TTL
        await cache.set(cache_key, response.model_dump_json(), ex=settings.REDIS_CACHE_EXPIRATION_SECONDS)

    return response


@chat_router.delete("/chats/direct/{chat_guid}/", summary="Delete user's chat", status_code=status.HTTP_204_NO_CONTENT)
async def delete_direct_chat_view(
    chat_guid: UUID,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
    cache: aioredis.Redis = Depends(get_cache),
    cache_enabled: bool = Depends(get_cache_setting),
):
    chat: Chat | None = await get_chat_by_guid(db_session, chat_guid=chat_guid)

    if not chat or current_user not in chat.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat with provided guid is not found")

    await db_session.delete(chat)
    await db_session.commit()

    if cache_enabled:
        for user in chat.users:
            await clear_cache_for_get_direct_chats(cache=cache, user=user)


def convert_uuid(obj):
    """Convert UUID objects to strings for JSON serialization."""
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# @chat_router.get(
#     "/chat/{chat_guid}/messages/old/{message_guid}/",
#     summary="Get user's historical chat messages",
# )
# async def get_older_messages(
#     chat_guid: UUID,
#     message_guid: UUID,
#     limit: Annotated[int | None, Query(gt=0, lt=200)] = 10,
#     db_session: AsyncSession = Depends(get_async_session),
#     current_user: User = Depends(get_current_user),
# ):
#     logger.info(f"Fetching old messages for chat {chat_guid}, starting from {message_guid}, limit: {limit}")

#     chat = await get_chat_by_guid(db_session, chat_guid=chat_guid)
#     if not chat:
#         logger.warning(f"Chat not found: {chat_guid}")
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat with provided guid is not found")

#     if current_user.id not in [user.id for user in chat.users]:
#         logger.warning(f"Access denied for user {current_user.id} in chat {chat_guid}")
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this chat")

#     message = await get_active_message_by_guid_and_chat(db_session, chat_id=chat.id, message_guid=message_guid)
#     if not message:
#         logger.warning(f"Message not found: {message_guid}")
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message with provided guid is not found")

#     logger.info(f"Fetching older messages before {message.created_at}")
#     old_messages, has_more_messages = await get_older_chat_messages(
#         db_session, chat=chat, user_id=current_user.id, created_at=message.created_at, limit=limit
#     )

#     formatted_messages = []
#     for msg in old_messages:
#         logger.info(f"Processing message {msg.message_guid} of type {msg.message_type}")

#         if msg.message_type == "file":
#             file_base64 = fetch_file_from_s3(msg.file_path)
#             if file_base64:
#                 truncated_file_base64 = file_base64[:100] + "..."  # Shorten log output
#                 logger.info(f"File {msg.file_name} retrieved (Base64 Preview: {truncated_file_base64})")
#             else:
#                 logger.error(f"File retrieval failed for {msg.file_name} at {msg.file_path}")
                  

#             formatted_messages.append({
#                 "message_guid": msg.message_guid,
#                 "user_guid": msg.user_guid,
#                 "chat_guid": msg.chat_guid,
#                 "message_type": msg.message_type,
#                 "file_name": msg.file_name,
#                 "file_path": msg.file_path,  # Include the file path instead of file_url
#                 "file_data": file_base64,  
#                 "created_at": msg.created_at.isoformat(),
#                 "is_read": msg.is_read,
#             })

#         else:
#             formatted_messages.append({
#                 "message_guid": msg.message_guid,
#                 "user_guid": msg.user_guid,
#                 "chat_guid": msg.chat_guid,
#                 "message_type": msg.message_type,
#                 "content": msg.content,
#                 "created_at": msg.created_at.isoformat(),
#                 "is_read": msg.is_read,
#             })

#     # Log structured JSON response (truncated to 500 characters)
#     response_log = json.dumps(formatted_messages, indent=2, default=convert_uuid)[:500]
#     logger.info(f"Returning {len(formatted_messages)} messages, has_more_messages={has_more_messages}, response={response_log}...")

#     return GetOldMessagesSchema(messages=formatted_messages, has_more_messages=has_more_messages)


# def fetch_file_from_s3(file_path: str) -> Optional[str]:
#     try:
#         logger.info(f"Fetching file from S3: {file_path}")  
#         print(f"Fetching file from S3: {file_path}")  

#         # Extract the S3 key from the URL
#         parsed_url = urlparse(file_path)
#         s3_key = parsed_url.path.lstrip("/")  # Remove leading '/'

#         logger.info(f"Extracted S3 key: {s3_key}")
#         print(f"Extracted S3 key: {s3_key}")  

#         response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
#         file_data = response['Body'].read()

#         logger.info(f"Successfully fetched file from S3: {s3_key}")  
#         print(f"Successfully fetched file from S3: {s3_key}")  

#         return base64.b64encode(file_data).decode('utf-8')

#     except Exception as e:
#         logger.error(f"Error fetching file from S3: {e}")
#         print(f"Error fetching file from S3: {e}")  
#         return None

@chat_router.get(
    "/chat/{chat_guid}/messages/old/{message_guid}/",
    summary="Get user's historical chat messages",
)
async def get_older_messages(
    chat_guid: UUID,
    message_guid: UUID,
    limit: Annotated[int | None, Query(gt=0, lt=200)] = 10,
    db_session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    chat: Chat | None = await get_chat_by_guid(db_session, chat_guid=chat_guid)

    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat with provided guid is not found")

    if current_user not in chat.users:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You don't have access to this chat")

    message: Message | None = await get_active_message_by_guid_and_chat(
        db_session, chat_id=chat.id, message_guid=message_guid
    )

    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message with provided guid is not found")

    old_messages, has_more_messages = await get_older_chat_messages(
        db_session, chat=chat, user_id=current_user.id, created_at=message.created_at, limit=limit
    )
    return GetOldMessagesSchema(messages=old_messages, has_more_messages=has_more_messages)
