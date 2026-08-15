<template>
  <div>
    <h1 style="font-weight: 800; font-size: 1.75rem;" class="mb-2">Encrypt & Decrypt</h1>
    <p class="text-secondary mb-8">Upload a file to see CipherLink's adaptive encryption in action</p>

    <v-row>
      <!-- Upload Section -->
      <v-col cols="12" md="6">
        <v-card class="glass-card pa-6">
          <h3 class="mb-4"><v-icon color="cyan" class="mr-2">mdi-upload</v-icon>Upload & Encrypt</h3>

          <div class="upload-zone" @click="fileInput?.click()" @drop.prevent="handleDrop" @dragover.prevent>
            <v-icon size="48" color="cyan" class="mb-3">mdi-cloud-upload</v-icon>
            <p>Click or drag a file here</p>
            <p class="text-secondary" style="font-size: 0.8rem;">Supports images, documents, and media files</p>
          </div>
          <input ref="fileInput" type="file" hidden @change="handleFileSelect" />

          <!-- File Preview -->
          <div v-if="selectedFile" class="mt-4">
            <div class="glass-card pa-4">
              <div class="d-flex align-center mb-3">
                <v-icon color="cyan" class="mr-3">mdi-file</v-icon>
                <div>
                  <strong>{{ selectedFile.name }}</strong>
                  <p class="text-secondary" style="font-size: 0.8rem;">{{ formatSize(selectedFile.size) }}</p>
                </div>
              </div>

              <div class="strategy-preview pa-3 mb-3">
                <div class="d-flex align-center">
                  <v-icon :color="predictedStrategy.color" class="mr-2">{{ predictedStrategy.icon }}</v-icon>
                  <div>
                    <strong>{{ predictedStrategy.name }}</strong>
                    <p class="text-secondary" style="font-size: 0.75rem;">{{ predictedStrategy.desc }}</p>
                  </div>
                </div>
              </div>

              <!-- Image preview -->
              <img v-if="previewUrl && selectedFile.type?.startsWith('image/')" :src="previewUrl"
                   style="max-width: 100%; border-radius: 8px; margin-bottom: 16px;" />

              <v-btn block color="primary" size="large" @click="encryptFile" :loading="encrypting">
                <v-icon start>mdi-lock</v-icon> Encrypt & Download
              </v-btn>
            </div>
          </div>
        </v-card>
      </v-col>

      <!-- Result Section -->
      <v-col cols="12" md="6">
        <v-card class="glass-card pa-6" v-if="encryptionResult">
          <h3 class="mb-4">
            <v-icon color="green" class="mr-2">mdi-check-circle</v-icon>Encryption Complete
          </h3>

          <div class="result-grid mb-4">
            <div class="result-item" v-for="item in resultItems" :key="item.label">
              <span class="result-label">{{ item.label }}</span>
              <span class="result-value font-mono">{{ item.value }}</span>
            </div>
          </div>

          <!-- Download Raw Encrypted (.enc) File -->
          <v-btn block color="cyan" variant="outlined" size="large" class="mb-3" @click="downloadEncryptedFile" :loading="downloading">
            <v-icon start>mdi-download</v-icon> Download Encrypted File (.enc)
          </v-btn>

          <v-btn block color="secondary" size="large" @click="decryptFile" :loading="decrypting">
            <v-icon start>mdi-lock-open</v-icon> Retrieve & Decrypt
          </v-btn>
        </v-card>

        <!-- Decrypt Uploaded (.enc) File Section -->
        <v-card class="glass-card pa-6 mt-4">
          <h3 class="mb-3">
            <v-icon color="purple" class="mr-2">mdi-file-key</v-icon>Decrypt External .enc File
          </h3>
          <p class="text-caption text-secondary mb-4">
            Upload an encrypted file (.enc) and enter its File ID. Decryption validates that you are the owner and decrypts the AES key with your ECC private key first.
          </p>

          <v-text-field v-model="decryptFileId" label="File ID (UUID) — Auto-detected" placeholder="Optional if file is uploaded" prepend-inner-icon="mdi-identifier" class="mb-2" density="compact" />
          
          <v-file-input v-model="encUploadFile" @update:model-value="handleEncFileSelect" label="Upload .enc File" prepend-icon="mdi-lock" class="mb-3" density="compact" show-size />

          <v-alert v-if="uploadDecryptError" type="error" variant="tonal" class="mb-3" density="compact" closable @click:close="uploadDecryptError = ''">
            {{ uploadDecryptError }}
          </v-alert>

          <v-btn block color="purple" :loading="uploadDecrypting" @click="decryptUploadedEncFile" :disabled="!encUploadFile && !decryptFileId">
            <v-icon start>mdi-key-decrypt</v-icon> Validate User & Decrypt File
          </v-btn>
        </v-card>

        <!-- Decrypted Result -->
        <v-card class="glass-card pa-6 mt-4" v-if="decryptedUrl">
          <div class="d-flex align-center justify-space-between mb-4 flex-wrap" style="gap: 8px;">
            <h3 class="d-flex align-center">
              <v-icon color="green" class="mr-2">mdi-shield-check</v-icon>Decrypted Original File
            </h3>
            <v-chip v-if="decryptedFileName" size="small" color="success" variant="tonal" class="font-mono text-truncate" style="max-width: 220px;">
              <v-icon start size="14">mdi-file-outline</v-icon>
              <span class="text-truncate">{{ decryptedFileName }}</span>
            </v-chip>
          </div>

          <div v-if="isDecryptedImage" class="mb-4 text-center">
            <img :src="decryptedUrl" style="max-width: 100%; max-height: 400px; border-radius: 12px; border: 1px solid var(--cl-border); object-fit: contain;" />
          </div>

          <v-btn block color="success" size="large" class="mb-3 text-none" @click="downloadDecryptedFile" :loading="downloadingDecrypted">
            <v-icon start>mdi-download</v-icon> Download Decrypted File
          </v-btn>

          <p class="text-secondary" style="font-size: 0.85rem; line-height: 1.4;">
            Successfully verified user ownership, decrypted AES key with ECC private key, and decrypted original file.
          </p>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '@/services/api'

const fileInput = ref(null)
const selectedFile = ref(null)
const previewUrl = ref(null)
const encrypting = ref(false)
const decrypting = ref(false)
const downloading = ref(false)
const encryptionResult = ref(null)
const decryptedUrl = ref(null)
const decryptedFileName = ref('')
const downloadingDecrypted = ref(false)

const decryptFileId = ref('')
const encUploadFile = ref(null)
const uploadDecrypting = ref(false)
const uploadDecryptError = ref('')
const decryptedMime = ref('')

const isDecryptedImage = computed(() => {
  return decryptedMime.value?.startsWith('image/') || decryptedUrl.value?.match(/\.(png|jpg|jpeg|gif|webp)$/i)
})

const ONE_MB = 1024 * 1024
const TEN_MB = 10 * 1024 * 1024

const predictedStrategy = computed(() => {
  if (!selectedFile.value) return {}
  const size = selectedFile.value.size
  if (size < ONE_MB) return { name: 'Standard AES-256-GCM', icon: 'mdi-lightning-bolt', color: 'cyan', desc: 'Fast single-pass encryption for small files' }
  if (size <= TEN_MB) return { name: 'Hybrid AES + ECC', icon: 'mdi-shield-half-full', color: 'purple', desc: 'AES encryption with ECC key wrapping' }
  return { name: 'Chunked Parallel', icon: 'mdi-view-grid', color: 'amber', desc: 'Parallel chunk encryption for large files' }
})

const resultItems = computed(() => {
  if (!encryptionResult.value) return []
  const r = encryptionResult.value
  return [
    { label: 'File ID', value: r.file_id },
    { label: 'Strategy', value: r.strategy },
    { label: 'Algorithm', value: r.algorithm },
    { label: 'Key Protection', value: r.key_wrap || 'ECC' },
    { label: 'Original Size', value: formatSize(r.original_size) },
    { label: 'Encrypted Size', value: formatSize(r.encrypted_size) },
    { label: 'Storage', value: r.storage_provider },
    { label: 'Chunked', value: r.is_chunked ? `Yes (${r.chunk_count} chunks)` : 'No' },
  ]
})

function handleFileSelect(e) {
  const file = e.target?.files?.[0]
  if (file) setFile(file)
}

function handleEncFileSelect(e) {
  let file = null
  if (Array.isArray(e)) {
    file = e[0]
  } else if (e?.target?.files) {
    file = e.target.files[0]
  } else {
    file = e
  }
  
  if (file) {
    encUploadFile.value = file
    // Auto-populate File ID if active result exists
    if (encryptionResult.value?.file_id) {
      decryptFileId.value = encryptionResult.value.file_id
    }
  }
}

function handleDrop(e) {
  const file = e.dataTransfer?.files?.[0]
  if (file) setFile(file)
}

function setFile(file) {
  selectedFile.value = file
  encryptionResult.value = null
  decryptedUrl.value = null
  decryptedFileName.value = ''
  if (file.type?.startsWith('image/')) {
    previewUrl.value = URL.createObjectURL(file)
  } else {
    previewUrl.value = null
  }
}

async function encryptFile() {
  if (!selectedFile.value) return
  encrypting.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    const { data } = await api.post('/api/v1/encryption/encrypt', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (data.success) {
      encryptionResult.value = data.data
      decryptFileId.value = data.data.file_id
    }
  } catch (e) {
    alert(e.response?.data?.detail || 'Encryption failed')
  } finally {
    encrypting.value = false
  }
}

async function downloadEncryptedFile() {
  if (!encryptionResult.value?.encrypted_download_url) return
  downloading.value = true
  try {
    const response = await api.get(encryptionResult.value.encrypted_download_url, {
      responseType: 'blob',
    })
    // Extract filename from Content-Disposition header or use fallback
    const contentDisp = response.headers['content-disposition']
    let filename = 'encrypted_file.enc'
    if (contentDisp) {
      const match = contentDisp.match(/filename="?([^"]+)"?/)
      if (match) filename = match[1]
    }
    // Create blob download
    const blob = new Blob([response.data], { type: 'application/octet-stream' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    alert(e.response?.data?.detail || 'Download failed')
  } finally {
    downloading.value = false
  }
}

async function decryptFile() {
  if (!encryptionResult.value?.file_id) return
  decrypting.value = true
  try {
    const { data } = await api.post(`/api/v1/encryption/decrypt/${encryptionResult.value.file_id}`)
    if (data.success && data.data.download_url) {
      decryptedUrl.value = data.data.download_url
      decryptedMime.value = data.data.mime_type || ''
      decryptedFileName.value = data.data.original_filename || 'decrypted_file'
    }
  } catch (e) {
    alert(e.response?.data?.detail || 'Decryption failed')
  } finally {
    decrypting.value = false
  }
}

async function decryptUploadedEncFile() {
  uploadDecryptError.value = ''
  if (!encUploadFile.value && !decryptFileId.value) return
  uploadDecrypting.value = true

  try {
    const formData = new FormData()
    if (decryptFileId.value && decryptFileId.value.trim()) {
      formData.append('file_id', decryptFileId.value.trim())
    }
    
    let targetFile = encUploadFile.value
    if (Array.isArray(targetFile)) {
      targetFile = targetFile[0]
    }
    
    if (targetFile) {
      formData.append('file', targetFile)
    }

    const { data } = await api.post('/api/v1/encryption/decrypt-uploaded', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    if (data.success && data.data.download_url) {
      decryptedUrl.value = data.data.download_url
      decryptedMime.value = data.data.mime_type || ''
      let fallbackName = 'decrypted_file'
      if (encUploadFile.value?.name) {
        fallbackName = encUploadFile.value.name.replace(/\.enc$/i, '')
      }
      decryptedFileName.value = data.data.original_filename || fallbackName
    } else {
      uploadDecryptError.value = data.error?.message || 'Decryption failed'
    }
  } catch (e) {
    uploadDecryptError.value = e.response?.data?.detail || e.response?.data?.error?.message || 'Decryption failed. Ensure you are logged in as the file owner.'
  } finally {
    uploadDecrypting.value = false
  }
}

async function downloadDecryptedFile() {
  if (!decryptedUrl.value) return
  downloadingDecrypted.value = true
  try {
    const response = await api.get(decryptedUrl.value, {
      responseType: 'blob',
    })
    const blob = new Blob([response.data], { type: decryptedMime.value || 'application/octet-stream' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = decryptedFileName.value || 'decrypted_file'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    const a = document.createElement('a')
    a.href = decryptedUrl.value
    a.download = decryptedFileName.value || 'decrypted_file'
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  } finally {
    downloadingDecrypted.value = false
  }
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i]
}
</script>

<style scoped>
.upload-zone {
  border: 2px dashed var(--cl-border);
  border-radius: 16px;
  padding: 48px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}
.upload-zone:hover {
  border-color: #06b6d4;
  background: rgba(6, 182, 212, 0.05);
}
.strategy-preview {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid var(--cl-border);
  border-radius: 12px;
}
.result-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.result-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.result-label {
  font-size: 0.75rem;
  color: var(--cl-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.result-value {
  font-size: 0.85rem;
  font-weight: 600;
}
</style>
