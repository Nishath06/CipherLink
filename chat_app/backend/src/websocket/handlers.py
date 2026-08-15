import asyncio
import logging
from datetime import datetime
import base64
import boto3
import uuid
from src.models import MessageType
import os
from src.config import settings
import redis.asyncio as aioredis
from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from src.websocket.crypto_utils import (
    aes_encrypt,
    aes_decrypt,
    ecc_decrypt,
    ecc_encrypt,
)
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from botocore.exceptions import NoCredentialsError

from src.managers.websocket_manager import WebSocketManager
from src.models import Chat, Message, ReadStatus, User,ECCKey,EncryptedFile
from src.utils import clear_cache_for_get_direct_chats, clear_cache_for_get_messages
from src.websocket.schemas import (
    AddUserToChatSchema,
    MessageReadSchema,
    NotifyChatRemovedSchema,
    ReceiveMessageSchema,
    SendMessageSchema,
    UserTypingSchema,
    SendFileSchema,
)
from src.websocket.services import (
    get_chat_id_by_guid,
    get_message_by_guid,
    mark_last_read_message,
    mark_user_as_online,
    send_new_chat_created_ws_message,
)

logger = logging.getLogger(__name__)


socket_manager = WebSocketManager()


s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION_NAME,
)
s3_bucket = settings.AWS_IMAGES_BUCKET

@socket_manager.handler("new_message")
async def new_message_handler(
    websocket: WebSocket,
    db_session: AsyncSession,
    cache: aioredis.Redis,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    cache_enabled: bool,
    **kwargs,
):
    """
    message is received as "new_message" type but broadcasted to all users
    as "new" type
    """
    message_schema = ReceiveMessageSchema(**incoming_message)
    chat_guid: str = str(message_schema.chat_guid)

    notify_friend_about_new_chat: bool = False
    # newly created chat
    if not chats or chat_guid not in chats:
        chat_id: int | None = await get_chat_id_by_guid(db_session, chat_guid=chat_guid)
        if chat_id:
            # this action modifies chats variable in websocket view
            chats[chat_guid] = chat_id
            await socket_manager.add_user_to_chat(chat_guid, websocket)
            # must notify friend that new chat has been created
            notify_friend_about_new_chat = True

        else:
            await socket_manager.send_error("Chat has not been added", websocket)
            return

    chat_id = chats.get(chat_guid)
    try:
        # Save message and broadcast it back
        message = Message(
            content=message_schema.content,
            chat_id=chat_id,
            user_id=current_user.id,
        )
        db_session.add(message)
        await db_session.flush()  # to generate id

        # Update the updated_at field of the chat
        chat: Chat = await db_session.get(Chat, chat_id)
        chat.updated_at = datetime.now()
        db_session.add(chat)

        await db_session.commit()
        await db_session.refresh(message, attribute_names=["user", "chat"])  # ?
        await db_session.refresh(chat, attribute_names=["users"])  # ?

    except Exception as exc_info:
        await db_session.rollback()
        logger.exception(f"[new_message] Exception, rolling back session, detail: {exc_info}")
        raise exc_info

    await mark_user_as_online(
        cache=cache, current_user=current_user, socket_manager=socket_manager, chat_guid=chat_guid
    )
    # clear cache for all users
    if cache_enabled:
        for user in chat.users:
            await clear_cache_for_get_direct_chats(cache=cache, user=user)
        # clear cache for getting messages
        await clear_cache_for_get_messages(cache=cache, chat_guid=chat_guid)

    send_message_schema = SendMessageSchema(
        message_guid=message.guid,
        chat_guid=chat.guid,
        user_guid=current_user.guid,
        content=message.content,
        created_at=message.created_at,
        is_read=False,
        is_new=True,
    )
    outgoing_message: dict = send_message_schema.model_dump_json()

    await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)

    if notify_friend_about_new_chat:
        logger.info("Notifying friend about newly created chat")
        await send_new_chat_created_ws_message(socket_manager=socket_manager, current_user=current_user, chat=chat)

# @socket_manager.handler("new_file")
# async def file_upload_handler(
#     websocket: WebSocket,
#     db_session: AsyncSession,
#     cache: aioredis.Redis,
#     incoming_message: dict,
#     chats: dict,
#     current_user,
#     cache_enabled: bool,
#     **kwargs,
# ):
#     """
#     Handles incoming file messages, uploads to S3, and stores metadata in the DB.
#     """
#     logger.info(f"[new_file] Incoming message: {incoming_message}")

#     file_name = incoming_message.get("file_name")
#     file_data = incoming_message.get("file_data")  # Base64 data
#     chat_guid = incoming_message.get("chat_guid")

#     if not file_name or not file_data or not chat_guid:
#         logger.error("[new_file] Missing required file parameters")
#         await socket_manager.send_error("Missing required file parameters", websocket)
#         return

#     logger.info(f"[new_file] File name: {file_name}, Chat GUID: {chat_guid}")

#     if chat_guid not in chats:
#         logger.info(f"[new_file] Chat GUID {chat_guid} not found in active chats. Fetching from DB...")
#         chat_id = await get_chat_id_by_guid(db_session, chat_guid)
#         if chat_id:
#             chats[chat_guid] = chat_id
#             await socket_manager.add_user_to_chat(chat_guid, websocket)
#             logger.info(f"[new_file] Chat {chat_guid} added with ID {chat_id}")
#         else:
#             logger.error(f"[new_file] Chat {chat_guid} not found in DB")
#             await socket_manager.send_error("Chat not found", websocket)
#             return
#     chat_id = chats[chat_guid]

#     try:
#         # Decode base64 file data
#         logger.info(f"[new_file] Decoding base64 file data for {file_name}...")
#         try:
#             file_bytes = base64.b64decode(file_data)
#             logger.info(f"[new_file] File successfully decoded.")
#         except Exception as decode_error:
#             logger.error(f"[new_file] Failed to decode base64 data: {decode_error}")
#             await socket_manager.send_error("Invalid file data", websocket)
#             return

#         # Upload to S3
#         s3_key = f"uploads/{uuid.uuid4()}_{file_name}"
#         logger.info(f"[new_file] Uploading file to S3 at key: {s3_key}...")

#         try:
#             s3_client.put_object(Bucket=s3_bucket, Key=s3_key, Body=file_bytes)
#             file_url = f"https://{s3_bucket}.s3.amazonaws.com/{s3_key}"
#             logger.info(f"[new_file] File successfully uploaded to S3: {file_url}")
#         except Exception as s3_error:
#             logger.error(f"[new_file] S3 upload failed: {s3_error}")
#             await socket_manager.send_error("File upload to S3 failed", websocket)
#             return

#         # Save message in DB
#         logger.info(f"[new_file] Saving file message in database...")
#         message = Message(
#             message_type=MessageType.FILE,
#             content="",
#             file_name=file_name,
#             file_path=file_url,
#             user_id=current_user.id,
#             chat_id=chat_id,
#         )
#         db_session.add(message)
#         await db_session.commit()
#         await db_session.refresh(message, attribute_names=["user", "chat"])
#         logger.info(f"[new_file] File message successfully saved with ID {message.id}")

#         # Clear cache
#         if cache_enabled:
#             logger.info("[new_file] Clearing cache for user and chat...")
#             await clear_cache_for_get_direct_chats(cache, current_user)
#             await clear_cache_for_get_messages(cache, chat_guid)

#         # Send message to frontend
#         send_message_schema = SendMessageSchema(
#             message_guid=message.guid,
#             chat_guid=chat_guid,
#             user_guid=current_user.guid,
#             content="",
#             file_name=file_name,
#             file_path=file_url,
#             created_at=datetime.utcnow(),
#             is_read=False,
#             is_new=True,
#         )
#         outgoing_message = send_message_schema.model_dump_json()
#         logger.info(f"[new_file] Broadcasting file message to chat {chat_guid}")

#         await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)

#     except Exception as e:
#         logger.exception(f"[new_file] Unexpected error: {str(e)}")
#         await db_session.rollback()
#         await socket_manager.send_error(f"File upload failed: {str(e)}", websocket)


# @socket_manager.handler("new_file")
# async def file_upload_handler(
#     websocket: WebSocket,
#     db_session: AsyncSession,
#     cache: aioredis.Redis,
#     incoming_message: dict,
#     chats: dict,
#     current_user,
#     cache_enabled: bool,
#     **kwargs,
# ):
#     """
#     Handles incoming file messages, uploads to S3, stores metadata in the DB,
#     fetches the image from S3, converts it into base64, and logs it.
#     """
#     logger.info(f"[new_file] Incoming message: {incoming_message}")

#     file_name = incoming_message.get("file_name")
#     file_data = incoming_message.get("file_data")  # Base64 data
#     chat_guid = incoming_message.get("chat_guid")

#     if not file_name or not file_data or not chat_guid:
#         logger.error("[new_file] Missing required file parameters")
#         await socket_manager.send_error("Missing required file parameters", websocket)
#         return

#     logger.info(f"[new_file] File name: {file_name}, Chat GUID: {chat_guid}")

#     file_extension = os.path.splitext(file_name)[1]

#     if chat_guid not in chats:
#         logger.info(f"[new_file] Chat GUID {chat_guid} not found in active chats. Fetching from DB...")
#         chat_id = await get_chat_id_by_guid(db_session, chat_guid)
#         if chat_id:
#             chats[chat_guid] = chat_id
#             await socket_manager.add_user_to_chat(chat_guid, websocket)
#             logger.info(f"[new_file] Chat {chat_guid} added with ID {chat_id}")
#         else:
#             logger.error(f"[new_file] Chat {chat_guid} not found in DB")
#             await socket_manager.send_error("Chat not found", websocket)
#             return
#     chat_id = chats[chat_guid]

#     try:
#         # Decode base64 file data
#         logger.info(f"[new_file] Decoding base64 file data for {file_name}...")
#         try:
#             file_bytes = base64.b64decode(file_data)
#             logger.info("[new_file] File successfully decoded.")
#         except Exception as decode_error:
#             logger.error(f"[new_file] Failed to decode base64 data: {decode_error}")
#             await socket_manager.send_error("Invalid file data", websocket)
#             return

#         # Upload to S3
#         s3_key = f"uploads/{uuid.uuid4()}_{file_name}"
#         logger.info(f"[new_file] Uploading file to S3 at key: {s3_key}...")

#         try:
#             s3_client.put_object(Bucket=s3_bucket, Key=s3_key, Body=file_bytes)
#             file_url = f"https://{s3_bucket}.s3.amazonaws.com/{s3_key}"
#             logger.info(f"[new_file] File successfully uploaded to S3: {file_url}")
#         except NoCredentialsError:
#             logger.error("[new_file] AWS credentials not found.")
#             await socket_manager.send_error("AWS credentials error", websocket)
#             return
#         except Exception as s3_error:
#             logger.error(f"[new_file] S3 upload failed: {s3_error}")
#             await socket_manager.send_error("File upload to S3 failed", websocket)
#             return

#         # Save message in DB
#         logger.info("[new_file] Saving file message in database...")
#         message = Message(
#             message_type=MessageType.FILE,
#             content="",
#             file_name=file_name,
#             file_path=file_url,
#             user_id=current_user.id,
#             chat_id=chat_id,
#         )
#         db_session.add(message)
#         await db_session.commit()
#         await db_session.refresh(message, attribute_names=["user", "chat"])
#         logger.info(f"[new_file] File message successfully saved with ID {message.id}")

#         # Fetch file from S3 and convert to Base64
#         try:
#             logger.info("[new_file] Fetching file from S3...")
#             s3_object = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
#             file_content = s3_object['Body'].read()
#             base64_file_content = base64.b64encode(file_content).decode('utf-8')
#             logger.info(f"[new_file] Base64 file content: {base64_file_content[:100]}... (truncated)")
#         except Exception as fetch_error:
#             logger.error(f"[new_file] Failed to fetch file from S3: {fetch_error}")

#         # Clear cache
#         if cache_enabled:
#             logger.info("[new_file] Clearing cache for user and chat...")
#             await clear_cache_for_get_direct_chats(cache, current_user)
#             await clear_cache_for_get_messages(cache, chat_guid)

#         # Send message to frontend
#         send_file_schema = SendFileSchema(
#             type="new_file",
#             message_guid=str(message.guid),  # Convert UUID to string
#             chat_guid=chat_guid,
#             user_guid=str(current_user.guid),  # Convert UUID to string
#             file_data=base64_file_content,
#             file_extension=file_extension,
#             created_at=datetime.utcnow(),
#             is_read=False,
#             is_new=True
#         )


#         outgoing_message = send_file_schema.model_dump_json()
#         logger.info(f"[new_file] Broadcasting file message to chat {outgoing_message}")

#         await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)

#     except Exception as e:
#         logger.exception(f"[new_file] Unexpected error: {str(e)}")
#         await db_session.rollback()
#         await socket_manager.send_error(f"File upload failed: {str(e)}", websocket)
@socket_manager.handler("new_file")
async def file_upload_handler(
    websocket: WebSocket,
    db_session: AsyncSession,
    cache: aioredis.Redis,
    incoming_message: dict,
    chats: dict,
    current_user,
    cache_enabled: bool,
    **kwargs,
):
    """
    Handles incoming file messages, encrypts them using hybrid ECC-AES encryption,
    uploads to S3, stores metadata and the encrypted AES key in the DB,
    and broadcasts the original file via WebSocket.
    """
    logger.info(f"[new_file] Incoming message: ")

    file_name = incoming_message.get("file_name")
    file_data = incoming_message.get("file_data")  # Base64 data
    chat_guid = incoming_message.get("chat_guid")
    receiver_guid = incoming_message.get("receiver_guid")

    if not file_name or not file_data or not chat_guid:
        logger.error("[new_file] Missing required file parameters")
        await socket_manager.send_error("Missing required file parameters", websocket)
        return

    logger.info(f"[new_file] File name: {file_name}, Chat GUID: {chat_guid}")

    file_extension = os.path.splitext(file_name)[1]
    
    # Truncate file name if too long (ensure it fits in DB column)
    if len(file_name) > 45:  # Leave some space for the extension
        base_name = os.path.splitext(file_name)[0]
        truncated_name = base_name[:45 - len(file_extension)] + file_extension
        logger.info(f"[new_file] Filename too long, truncating from '{file_name}' to '{truncated_name}'")
        file_name = truncated_name

    if chat_guid not in chats:
        logger.info(f"[new_file] Chat GUID {chat_guid} not found in active chats. Fetching from DB...")
        chat_id = await get_chat_id_by_guid(db_session, chat_guid)
        if chat_id:
            chats[chat_guid] = chat_id
            await socket_manager.add_user_to_chat(chat_guid, websocket)
            logger.info(f"[new_file] Chat {chat_guid} added with ID {chat_id}")
        else:
            logger.error(f"[new_file] Chat {chat_guid} not found in DB")
            await socket_manager.send_error("Chat not found", websocket)
            return
    chat_id = chats[chat_guid]

    try:
        # Decode base64 file data
        logger.info(f"[new_file] Decoding base64 file data for {file_name}...")
        try:
            file_bytes = base64.b64decode(file_data)
            logger.info(f"[new_file] File successfully decoded.")
        except Exception as decode_error:
            logger.error(f"[new_file] Failed to decode base64 data: {decode_error}")
            await socket_manager.send_error("Invalid file data", websocket)
            return

        # Fetch recipient's ECC public key for hybrid encryption
        recipient_ecc_key = None
        if receiver_guid:
            result = await db_session.execute(
                select(ECCKey).where(ECCKey.user_guid == uuid.UUID(receiver_guid))
            )
            recipient_ecc_key = result.scalar_one_or_none()

        if not recipient_ecc_key:
            # Fallback: get the other user in the chat
            chat_query = select(Chat).where(Chat.id == chat_id).options(selectinload(Chat.users))
            result = await db_session.execute(chat_query)
            chat_obj = result.scalar_one_or_none()
            if chat_obj:
                recipient_user = next((u for u in chat_obj.users if u.id != current_user.id), None)
                if recipient_user:
                    result = await db_session.execute(
                        select(ECCKey).where(ECCKey.user_guid == recipient_user.guid)
                    )
                    recipient_ecc_key = result.scalar_one_or_none()

        s3_key = f"uploads/{uuid.uuid4()}_{file_name}"
        
        # Hybrid Encryption: AES encrypt file, ECC encrypt AES key
        if recipient_ecc_key:
            logger.info(f"[new_file] Encrypting file using recipient's ECC key: {recipient_ecc_key.public_key[:30]}...")
            try:
                # Generate a random 32-byte AES key
                aes_key = os.urandom(32)
                # Encrypt raw file bytes using AES-CFB
                encrypted_bytes = aes_encrypt(file_bytes, aes_key)
                # Encrypt the AES key using recipient's ECC public key
                encrypted_aes_key = ecc_encrypt(aes_key, recipient_ecc_key.public_key)
                
                # Save the encrypted key in the DB
                encrypted_file_record = EncryptedFile(
                    filename=s3_key,
                    user_guid=recipient_ecc_key.user_guid,
                    encrypted_key=encrypted_aes_key
                )
                db_session.add(encrypted_file_record)
                
                # S3 body will be the encrypted bytes
                s3_body = encrypted_bytes
                logger.info("[new_file] Hybrid encryption succeeded.")
            except Exception as enc_err:
                logger.error(f"[new_file] Hybrid encryption failed: {enc_err}, falling back to unencrypted")
                s3_body = file_bytes
        else:
            logger.warning("[new_file] Recipient ECC public key not found! Uploading file unencrypted.")
            s3_body = file_bytes

        # Upload to S3
        logger.info(f"[new_file] Uploading file to S3 at key: {s3_key}...")
        try:
            s3_client.put_object(Bucket=s3_bucket, Key=s3_key, Body=s3_body)
            file_url = f"https://{s3_bucket}.s3.amazonaws.com/{s3_key}"
            logger.info(f"[new_file] File successfully uploaded to S3: {file_url}")
        except NoCredentialsError:
            logger.error("[new_file] AWS credentials not found.")
            await socket_manager.send_error("AWS credentials error", websocket)
            return
        except Exception as s3_error:
            logger.error(f"[new_file] S3 upload failed: {s3_error}")
            await socket_manager.send_error("File upload to S3 failed", websocket)
            return

        # Save message in DB
        logger.info("[new_file] Saving file message in database...")
        message = Message(
            message_type=MessageType.FILE,
            content="",
            file_name=file_name,
            file_path=file_url,
            user_id=current_user.id,
            chat_id=chat_id,
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message, attribute_names=["user", "chat"])
        logger.info(f"[new_file] File message successfully saved with ID {message.id}")

        # Clear cache
        if cache_enabled:
            logger.info("[new_file] Clearing cache for user and chat...")
            await clear_cache_for_get_direct_chats(cache, current_user)
            await clear_cache_for_get_messages(cache, chat_guid)

        # Broadcast the file message to the chat.
        # Note: We send the original unencrypted file_data (Base64) to the WebSocket 
        # so active chat participants receive the file/image immediately.
        send_file_schema = SendFileSchema(
            type="new_file",
            message_guid=str(message.guid),
            chat_guid=chat_guid,
            user_guid=str(current_user.guid),
            file_data=file_data,  # original base64
            file_extension=file_extension,
            created_at=datetime.utcnow(),
            is_read=False,
            is_new=True,
            file_s3url=file_url
        )

        outgoing_message = send_file_schema.model_dump_json()
        logger.info(f"[new_file] Broadcasting file message to chat {outgoing_message[:150]}... (truncated)")

        await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)

    except Exception as e:
        logger.exception(f"[new_file] Unexpected error: {str(e)}")
        await db_session.rollback()
        await socket_manager.send_error(f"File upload failed: {str(e)}", websocket)

@socket_manager.handler("message_read")
async def message_read_handler(
    websocket: WebSocket,
    db_session: AsyncSession,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    cache: aioredis.Redis,
    cache_enabled: bool,
    **kwargs,
):
    message_read_schema = MessageReadSchema(**incoming_message)

    message_guid = str(message_read_schema.message_guid)
    message: Message | None = await get_message_by_guid(db_session, message_guid=message_guid)
    if not message:
        await socket_manager.send_error(
            f"[read_status] Message with provided guid [{message_guid}] does not exist", websocket
        )
    chat_guid = str(message_read_schema.chat_guid)
    if chat_guid not in chats:
        await socket_manager.send_error(
            f"[read_status] Chat with provided guid [{chat_guid}] does not exist", websocket
        )
        return
    chat_id = chats.get(chat_guid)

    # Mark message read for own user, if none is returned, message is already read
    read_status: ReadStatus | None = await mark_last_read_message(
        db_session, user_id=current_user.id, chat_id=chat_id, last_read_message_id=message.id
    )
    if read_status:
        outgoing_message = {
            "type": "message_read",
            "user_guid": str(current_user.guid),
            "chat_guid": str(chat_guid),
            "last_read_message_guid": str(message.guid),
            "last_read_message_created_at": str(message.created_at),
        }
        # change redis/send ws message showing status is online
        await mark_user_as_online(
            cache=cache, current_user=current_user, socket_manager=socket_manager, chat_guid=chat_guid
        )
        if cache_enabled:
            # clear cache for getting messages
            await clear_cache_for_get_messages(cache=cache, chat_guid=chat_guid)

        await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)


@socket_manager.handler("user_typing")
async def user_typing_handler(
    websocket: WebSocket,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    cache: aioredis.Redis,
    **kwargs,
):
    # TODO: Rate limit
    # TODO: Validate chat_guid and user_guid

    user_typing_schema = UserTypingSchema(**incoming_message)
    chat_guid: str = str(user_typing_schema.chat_guid)
    if chat_guid not in chats:
        await socket_manager.send_error(
            f"[user_typing] Chat with provided guid [{chat_guid}] does not exist", websocket
        )
        return

    await mark_user_as_online(
        cache=cache, current_user=current_user, socket_manager=socket_manager, chat_guid=chat_guid
    )

    outgoing_message: dict = user_typing_schema.model_dump_json()
    await socket_manager.broadcast_to_chat(chat_guid, outgoing_message)


@socket_manager.handler("add_user_to_chat")
async def add_user_to_chat_handler(
    websocket: WebSocket,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    cache: aioredis.Redis,
    **kwargs,
):
    """
    `add_user_to_chat` type is only received by non-initiator user active websockets
    it subscribes the user to the newly created chat and marks non-initiator user
    as active since he/she has an active websocket connection that received this message
    """
    add_user_to_chat_schema = AddUserToChatSchema(**incoming_message)

    chat_guid = add_user_to_chat_schema.chat_guid
    chat_id = add_user_to_chat_schema.chat_id

    await socket_manager.add_user_to_chat(chat_guid=chat_guid, websocket=websocket)
    # modify chats variable in websocket view
    chats[chat_guid] = chat_id

    await mark_user_as_online(
        cache=cache, current_user=current_user, socket_manager=socket_manager, chat_guid=chat_guid
    )


@socket_manager.handler("chat_deleted")
async def chat_deleted_handler(
    websocket: WebSocket,
    incoming_message: dict,
    chats: dict,
    current_user: User,
    **kwargs,
):
    """
    `chat_deleted` - sends ws notification to all active websocket connections to display
    a message that the chat has been deleted/actual deletion happens via HTTP request
    """

    notify_chat_removed_schema = NotifyChatRemovedSchema(**incoming_message)
    chat_guid = notify_chat_removed_schema.chat_guid
    if chat_guid not in chats:
        await socket_manager.send_error(
            f"[chat_deleted] Chat with provided guid [{chat_guid}] does not exist", websocket
        )
        return

    # get all websocket connections that belong to this chat (except for ws that sent this messsage)
    # and send notification that chat has been removed

    target_websockets: set[WebSocket] = socket_manager.chats.get(chat_guid)

    outgoing_message = {
        "type": "chat_deleted",
        "user_guid": str(current_user.guid),
        "user_name": current_user.first_name,
        "chat_guid": chat_guid,
    }

    if target_websockets:
        # Send the notification message to the target user concurrently
        # used to notify frontend
        await asyncio.gather(
            *[
                socket.send_json(jsonable_encoder(outgoing_message))
                for socket in target_websockets
                if socket != websocket
            ]
        )
