"""Debug script to trace the decrypt-uploaded flow and identify the InvalidTag issue."""
import json, sys, asyncio
sys.path.insert(0, '.')
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

enc_file_path = Path("app_storage/encrypted/1/1b47c69a64a1451ab79606399af2241d/ChatGPT Image Aug 6, 2026, 12_29_39 PM.png.enc")
key_file_path = Path("app_storage/encrypted/1/1b47c69a64a1451ab79606399af2241d/ChatGPT Image Aug 6, 2026, 12_29_39 PM.png.enc.key")

packaged_bytes = enc_file_path.read_bytes()
encrypted_aes_key = key_file_path.read_bytes()

print(f"Packaged .enc file size: {len(packaged_bytes)} bytes")
print(f"Encrypted AES key size: {len(encrypted_aes_key)} bytes")
print(f"Starts with CLNK: {packaged_bytes[:4] == b'CLNK'}")

header_len = int.from_bytes(packaged_bytes[4:8], byteorder='big')
header_json = packaged_bytes[8 : 8 + header_len]
raw_ciphertext = packaged_bytes[8 + header_len :]
metadata = json.loads(header_json.decode('utf-8'))

print(f"Header JSON length: {header_len} bytes")
print(f"Raw ciphertext size (after strip): {len(raw_ciphertext)} bytes")
print(f"Strategy: {metadata.get('encryption_strategy')}")
print(f"Nonce[0]: {metadata['nonces'][0][:24]}...")
print(f"Tag[0]: {metadata['auth_tags'][0][:24]}...")

from app.core.config import settings
from app.core.security import decrypt_private_key

async def debug():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select
    from app.models.models import EncryptionKey, EncryptedFile
    from uuid import UUID
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from app.services.encryption.ecc import ecc_decrypt_key

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        res = await db.execute(select(EncryptedFile).where(EncryptedFile.uuid == UUID('993526dd-2df2-45a8-895e-8b7496c7b6f1')))
        ef = res.scalar_one_or_none()
        print(f"\nDB: original_size={ef.original_size}, encrypted_size={ef.encrypted_size}, key_id={ef.encryption_key_id}")

        key_res = await db.execute(select(EncryptionKey).where(EncryptionKey.id == ef.encryption_key_id))
        ecc_key = key_res.scalar_one_or_none()
        priv_bytes = decrypt_private_key(ecc_key.encrypted_private_key)
        priv_hex = priv_bytes.hex()
        print(f"Private key (first 16 hex): {priv_hex[:16]}...")

        aes_key = ecc_decrypt_key(encrypted_aes_key, priv_hex)
        print(f"Decrypted AES key: {aes_key.hex()[:16]}... ({len(aes_key)} bytes)")

        nonce = bytes.fromhex(metadata['nonces'][0])
        tag = bytes.fromhex(metadata['auth_tags'][0])
        print(f"Ciphertext={len(raw_ciphertext)}B, nonce={len(nonce)}B, tag={len(tag)}B")
        print(f"ct matches original_size: {len(raw_ciphertext) == ef.original_size}")
        print(f"ct matches encrypted_size: {len(raw_ciphertext) == ef.encrypted_size}")

        aesgcm = AESGCM(aes_key)
        try:
            pt = aesgcm.decrypt(nonce, raw_ciphertext + tag, None)
            print(f"\n[OK] DECRYPTION SUCCESS! Plaintext: {len(pt)} bytes")
        except Exception as e:
            print(f"\n[FAIL] DECRYPTION FAILED: {e}")
            try:
                pt2 = aesgcm.decrypt(nonce, raw_ciphertext, None)
                print(f"[OK] Works WITHOUT appending tag! pt={len(pt2)}B")
            except:
                print(f"[FAIL] Also failed without appending tag")
    await engine.dispose()

asyncio.run(debug())
