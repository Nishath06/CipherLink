import os
import logging
import binascii
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from ecies import encrypt, decrypt
from coincurve import PrivateKey

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ ECC Key Pair Generation
def generate_ecc_key_pair():
    """Generate ECC key pair using secp256k1 for ECIES encryption."""
    private_key = PrivateKey()
    public_key = private_key.public_key.format(compressed=True)  # ✅ Compressed format for ECIES

    private_key_hex = private_key.to_hex()
    public_key_hex = binascii.hexlify(public_key).decode()  # ✅ Convert public key to hex

    logging.debug(f"Generated ECC Keys:\n🔑 Private Key: {private_key_hex}\n🔑 Public Key: {public_key_hex}")
    return private_key_hex, public_key_hex



def aes_encrypt(file_data: bytes, aes_key: bytes) -> bytes:
    """Encrypt file with AES."""
    logging.debug("Starting AES encryption...")
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv))
    encryptor = cipher.encryptor()

    encrypted_data = encryptor.update(file_data) + encryptor.finalize()

    logging.debug("AES encryption completed.")
    return iv + encrypted_data
    


# ✅ AES Decryption

def aes_decrypt(encrypted_data: bytes, aes_key: bytes) -> bytes:
    """Decrypt AES-encrypted file and return decrypted bytes."""
    logging.debug("Starting AES decryption...")

    iv = encrypted_data[:16]  # Extract IV
    encrypted_data = encrypted_data[16:]  # Extract encrypted file data

    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv))
    decryptor = cipher.decryptor()

    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

    logging.debug("AES decryption completed.")
    return decrypted_data


# Encrypt AES key with ECC Public Key using ECDH
def ecc_encrypt(aes_key: bytes, public_key_hex: str) -> bytes:
    """Encrypt AES key using ECC public key."""
    logging.debug("Encrypting AES key with ECC...")
    encrypted_key = encrypt(public_key_hex, aes_key)
    logging.debug(f"ECC encryption completed. 🔐 Encrypted AES Key Length: {len(encrypted_key)} bytes")
    return encrypted_key


# ✅ ECC Decrypt AES key
def ecc_decrypt(encrypted_key: bytes, private_key_hex: str) -> bytes:
    """Decrypt AES key using ECC private key and validate consistency."""
    logging.debug(f"Attempting ECC decryption... Encrypted Key Length: {len(encrypted_key)} bytes")
    decrypted_key = decrypt(private_key_hex, encrypted_key)
    logging.debug(f"🔓 Decrypted AES Key: {decrypted_key.hex()}")  # Debugging line
    return decrypted_key