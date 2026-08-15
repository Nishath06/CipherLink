# 🔐 CipherLink: Hybrid ECC-AES Encrypted Chat Application

CipherLink is a high-performance, real-time messaging application designed with **multi-level hybrid encryption** (ECC + AES) to ensure that file attachments, media, and communication remain end-to-end secure.

---

## 🏗️ Architecture & Technology Stack

* **Frontend**: Vue 3, Vuetify 3, Pinia Store, Vite
* **Backend**: Python 3.11, FastAPI, Uvicorn, WebSockets, SQLAlchemy (Async), Alembic
* **Cryptography Core**: `coincurve` (secp256k1 ECC curve), `eciespy`, `cryptography` (AES-256-CFB)
* **Database**: PostgreSQL 15 (Schema: `chat`)
* **Storage**: AWS S3 Bucket
* **Cache / PubSub**: Redis
* **Reverse Proxy / Container**: Nginx, Docker

---

## 🔐 Comprehensive Encryption Workflow

The application uses a **Hybrid Cryptographic Architecture**:
* **AES-256-CFB**: Provides fast, symmetric encryption for large data (file attachments & images).
* **ECC secp256k1 (ECIES)**: Asymmetric Elliptic Curve Cryptography used to securely wrap and exchange symmetric AES keys per user.

```
       [ Client A (Sender) ]                             [ Client B (Recipient) ]
                │                                                   │
                ▼                                                   │
     1. Send File (Base64)                                          │
                │                                                   │
                ▼                                                   │
  2. Generate Random AES Key (32 bytes)                             │
                │                                                   │
    ┌───────────┴───────────┐                                       │
    ▼                       ▼                                       │
3. Encrypt File          4. Encrypt AES Key                         │
 (AES-256-CFB)            with Recipient's                           │
    │                      ECC Public Key                           │
    │                       │                                       │
    ▼                       ▼                                       │
5. Upload Encrypted     6. Save Encrypted Key                       │
 Payload to S3            in DB (chat.encrypted_files)             │
                            │                                       │
                            └───────────────────┬───────────────────┘
                                                │
                                                ▼
                                   7. Client B Fetch Messages
                                                │
                                                ▼
                                    8. Get Encrypted File from S3
                                    9. Decrypt AES Key using
                                       Recipient's ECC Private Key
                                   10. Decrypt File Payload using AES
                                                │
                                                ▼
                                  11. Render Image / File in UI
```

---

### Step-by-Step Encryption Flow Details

#### 1. Key Generation & Registration
* Upon user initialization/registration, an **Elliptic Curve Cryptography (ECC)** key pair based on the `secp256k1` curve is assigned.
* **Public Key**: Registered in the `chat.ecc_keys` database table and made accessible to message senders.
* **Private Key**: Stored securely in `chat.ecc_keys` to perform decryption for incoming encrypted keys.

#### 2. File Upload & Hybrid Encryption (`new_file` Event)
When a user uploads an image or file attachment:
1. **AES Key Generation**: The server generates a unique, cryptographically random 32-byte (256-bit) AES key (`os.urandom(32)`).
2. **Symmetric Payload Encryption**: The raw file binary is encrypted using **AES-256-CFB** mode (`aes_encrypt`).
3. **Asymmetric Key Encryption**: The 32-byte AES key is encrypted with the recipient's **ECC Public Key** (`ecc_encrypt`).
4. **Cloud Storage**: The encrypted binary file is stored in **AWS S3**.
5. **Database Metadata Storage**: An entry is created in `chat.encrypted_files` associating the S3 filename (`uploads/UUID_filename`), recipient's `user_guid`, and the `encrypted_key`.

#### 3. File Retrieval & Hybrid Decryption (`get_chat_messages`)
When a recipient opens a chat window or loads historical messages:
1. **Fetch Encrypted Blob**: The encrypted file payload is downloaded from **AWS S3**.
2. **Lookup Key Record**: The backend queries `chat.encrypted_files` using the S3 object key and the recipient's `user_guid`.
3. **ECC Decryption**: The recipient's **ECC Private Key** decrypts the stored `encrypted_key` blob to recover the 32-byte symmetric `aes_key`.
4. **AES Payload Decryption**: The `aes_key` decrypts the binary payload from S3 back to original raw file bytes (`aes_decrypt`).
5. **UI Rendering**: The raw bytes are encoded as Base64/Blob URL and rendered inline (image viewer or file download button).

---

## 🗄️ Database Schema (`chat` Schema)

The database runs on **PostgreSQL 15** inside the `chat` schema.

```
 +------------------+        +-----------------------+        +-------------------+
 |    chat.users    |        |     chat.ecc_keys     |        |   chat.messages   |
 +------------------+        +-----------------------+        +-------------------+
 | id (PK)          |<-------| id (PK)               |        | id (PK)           |
 | guid (UUID)      |        | user_guid (FK)        |        | guid (UUID)       |
 | email            |        | public_key (TEXT)     |        | message_type      |
 | username         |        | private_key (TEXT)    |        | content           |
 | hashed_password  |        | created_at            |        | file_name         |
 +------------------+        +-----------------------+        | file_path (S3)    |
         │                                                    | user_id (FK)      |
         │                   +-----------------------+        | chat_id (FK)      |
         │                   | chat.encrypted_files  |        +-------------------+
         │                   +-----------------------+
         └------------------>| id (PK)               |
                             | filename (S3 key)     |
                             | user_guid (FK)        |
                             | encrypted_key (BYTEA) |
                             | created_at            |
                             +-----------------------+
```

---

### Table Specifications

#### 1. `chat.ecc_keys` (Elliptic Curve Key Pairs)
Stores public and private keypairs for hybrid key exchange.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY`, `AUTOINCREMENT` | Internal table ID |
| `user_guid` | `UUID` | `NOT NULL`, `UNIQUE` | User identifier |
| `public_key` | `TEXT` | `NOT NULL` | Hex-encoded secp256k1 Public Key |
| `private_key` | `TEXT` | `NOT NULL` | Hex-encoded secp256k1 Private Key |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Creation timestamp |

#### 2. `chat.encrypted_files` (Encrypted Symmetric Keys)
Stores the AES symmetric key encrypted specifically for each recipient user.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY`, `AUTOINCREMENT` | Internal record ID |
| `filename` | `VARCHAR(255)` | `NOT NULL` | S3 Key (e.g. `uploads/uuid_file.png`) |
| `user_guid` | `UUID` | `NOT NULL` | Recipient user identifier |
| `encrypted_key`| `BYTEA` | `NOT NULL` | AES key encrypted with recipient ECC Public Key |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Creation timestamp |

#### 3. `chat.messages` (Message Records)
Stores chat messages and metadata.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY` | Message ID |
| `guid` | `UUID` | `UNIQUE` | Unique message identifier |
| `message_type` | `VARCHAR` | `NOT NULL` | Enum: `text` or `file` |
| `content` | `TEXT` | `NULLABLE` | Text content (empty for file messages) |
| `file_name` | `VARCHAR(45)` | `NULLABLE` | Attachment file name |
| `file_path` | `TEXT` | `NULLABLE` | AWS S3 object URL |
| `user_id` | `INTEGER` | `FK (chat.users.id)` | Sender ID |
| `chat_id` | `INTEGER` | `FK (chat.chats.id)` | Chat room ID |

---

## 🚀 Quick Start / Running the Application

### Running with Docker & Docker Compose (All-in-One)

1. **Build and Start Container**:
   ```bash
   docker compose up -d --build
   ```

2. **Access Web Application**:
   * **Chat UI**: [http://localhost](http://localhost)
   * **Swagger API Docs**: [http://localhost/docs](http://localhost/docs)

For detailed container management and deployment guides, refer to [DOCKER_GUIDE.md](file:///e:/wd/wd/Akatsuki/DOCKER_GUIDE.md).
