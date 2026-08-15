<template>
  <div>
    <div class="d-flex align-center mb-6">
      <div>
        <h1 style="font-weight: 800; font-size: 1.75rem;">Encryption Keys</h1>
        <p class="text-secondary">Manage your organization's ECC & AES key pairs</p>
      </div>
      <v-spacer />
      <v-btn
        color="primary"
        @click="openCreateDialog"
        :disabled="hasActiveEccKey"
      >
        <v-icon start>mdi-key-plus</v-icon> Generate Key
      </v-btn>
    </div>

    <v-alert v-if="hasActiveEccKey" type="info" variant="tonal" class="mb-4" density="compact">
      <v-icon start size="18">mdi-shield-check</v-icon>
      You already have an active ECC Key Pair. To create a new key pair, you must first revoke/delete your existing key.
    </v-alert>

    <v-alert v-if="createError" type="error" variant="tonal" class="mb-4" density="compact" closable @click:close="createError = ''">
      {{ createError }}
    </v-alert>

    <v-table density="comfortable" class="glass-card">
      <thead>
        <tr><th>Key ID</th><th>Type</th><th>Algorithm</th><th>Status</th><th>Label</th><th>Created</th><th>Actions</th></tr>
      </thead>
      <tbody>
        <tr v-for="k in keys" :key="k.uuid">
          <td class="font-mono" style="font-size: 0.8rem;">{{ k.uuid.substring(0, 8) }}...</td>
          <td><v-chip size="x-small" :color="k.key_type === 'ecc' ? 'cyan' : 'purple'" variant="tonal">{{ k.key_type.toUpperCase() }}</v-chip></td>
          <td class="font-mono" style="font-size: 0.8rem;">{{ k.algorithm }}</td>
          <td><span :class="'status-badge status-' + k.status">{{ k.status }}</span></td>
          <td>{{ k.label || '—' }}</td>
          <td class="text-secondary" style="font-size: 0.8rem;">{{ new Date(k.created_at).toLocaleDateString() }}</td>
          <td>
            <v-btn size="x-small" variant="text" color="error" @click="confirmRevoke(k)" v-if="k.status === 'active'" title="Revoke/Delete Key">
              <v-icon size="16">mdi-delete</v-icon>
              Revoke & Delete
            </v-btn>
          </td>
        </tr>
        <tr v-if="!keys.length">
          <td colspan="7" class="text-center pa-8 text-secondary">No keys yet. Generate your first encryption key.</td>
        </tr>
      </tbody>
    </v-table>

    <!-- Create Dialog -->
    <v-dialog v-model="showCreate" max-width="440">
      <v-card class="glass-card pa-6">
        <h3 class="mb-4">Generate Encryption Key</h3>
        <v-alert v-if="dialogError" type="error" variant="tonal" class="mb-4" density="compact">
          {{ dialogError }}
        </v-alert>
        <v-form @submit.prevent="createKey">
          <v-text-field v-model="form.label" label="Key Label (optional)" placeholder="e.g. Primary ECC Key" class="mb-4" />
          <v-btn type="submit" color="primary" block :loading="creating">Generate ECC Key Pair</v-btn>
        </v-form>
      </v-card>
    </v-dialog>

    <!-- Confirm Revoke / Delete Dialog -->
    <v-dialog v-model="showRevokeConfirm" max-width="500" persistent>
      <v-card class="glass-card pa-6">
        <div class="d-flex align-center mb-3 text-error">
          <v-icon color="error" size="32" class="mr-3">mdi-alert</v-icon>
          <h3 style="color: var(--cl-text-primary);">Warning: Irreversible Key Deletion</h3>
        </div>
        <p class="text-body-2 mb-4" style="color: #f87171; line-height: 1.5; font-weight: 500;">
          ⚠️ <strong>WARNING:</strong> If you delete/revoke this key, all documents encrypted using this key will become permanently inaccessible and cannot be decrypted!
        </p>
        <p class="text-caption text-secondary mb-4">
          Key UUID: <code class="font-mono">{{ keyToRevoke?.uuid }}</code>
        </p>
        <div class="d-flex justify-end gap-2" style="gap: 12px;">
          <v-btn variant="outlined" color="secondary" @click="showRevokeConfirm = false">Cancel</v-btn>
          <v-btn color="error" :loading="revoking" @click="executeRevoke">Yes, Revoke & Invalidate Key</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/services/api'

const keys = ref([])
const showCreate = ref(false)
const showPrivateKey = ref(false)
const showRevokeConfirm = ref(false)
const keyToRevoke = ref(null)
const revoking = ref(false)
const newPrivateKey = ref('')
const newPublicKey = ref('')
const creating = ref(false)
const createError = ref('')
const dialogError = ref('')
const form = ref({ key_type: 'ecc', label: '' })

const hasActiveEccKey = computed(() => {
  return keys.value.some(k => k.key_type === 'ecc' && k.status === 'active')
})

function openCreateDialog() {
  dialogError.value = ''
  showCreate.value = true
}

async function loadKeys() {
  try {
    const { data } = await api.get('/api/v1/keys')
    if (data.success) keys.value = data.data
  } catch {}
}

async function createKey() {
  dialogError.value = ''
  creating.value = true
  try {
    const { data } = await api.post('/api/v1/keys', form.value)
    if (data.success) {
      showCreate.value = false
      form.value = { key_type: 'ecc', label: '' }
      await loadKeys()
    }
  } catch (e) {
    dialogError.value = e.response?.data?.detail || 'Failed to generate key'
  } finally {
    creating.value = false
  }
}

function confirmRevoke(key) {
  keyToRevoke.value = key
  showRevokeConfirm.value = true
}

async function executeRevoke() {
  if (!keyToRevoke.value) return
  revoking.value = true
  try {
    const { data } = await api.post(`/api/v1/keys/${keyToRevoke.value.uuid}/revoke`)
    if (data.success) {
      showRevokeConfirm.value = false
      keyToRevoke.value = null
      await loadKeys()
    }
  } catch (e) {
    createError.value = e.response?.data?.detail || 'Key revocation failed'
  } finally {
    revoking.value = false
  }
}

onMounted(loadKeys)
</script>
