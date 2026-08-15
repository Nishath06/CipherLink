<template>
  <div>
    <div class="d-flex align-center mb-6">
      <div>
        <h1 style="font-weight: 800; font-size: 1.75rem;">Applications</h1>
        <p class="text-secondary">Manage registered external applications</p>
      </div>
      <v-spacer />
      <v-btn color="primary" @click="showCreate = true">
        <v-icon start>mdi-plus</v-icon> Register Application
      </v-btn>
    </div>

    <v-row>
      <v-col v-for="app in apps" :key="app.uuid" cols="12" md="6" lg="4">
        <v-card class="glass-card pa-5">
          <div class="d-flex align-center mb-3">
            <v-icon color="cyan" size="28" class="mr-3">mdi-apps</v-icon>
            <div>
              <h3 style="font-weight: 700;">{{ app.name }}</h3>
              <span class="text-secondary" style="font-size: 0.8rem;">{{ app.environment }}</span>
            </div>
            <v-spacer />
            <span :class="'status-badge ' + (app.is_active ? 'status-active' : 'status-revoked')">
              {{ app.is_active ? 'Active' : 'Revoked' }}
            </span>
          </div>
          <p v-if="app.description" class="text-secondary mb-3" style="font-size: 0.85rem;">{{ app.description }}</p>
          <div class="font-mono code-block pa-3 mb-3" style="font-size: 0.75rem;">
            Client ID: {{ app.client_id }}
          </div>
          <div class="mb-3">
            <v-chip v-for="s in app.scopes" :key="s" size="x-small" variant="tonal" color="purple" class="mr-1 mb-1">{{ s }}</v-chip>
          </div>
          <div class="d-flex gap-2">
            <v-btn size="small" variant="tonal" color="warning" @click="rotateSecret(app.uuid)">
              <v-icon start size="14">mdi-refresh</v-icon> Rotate Secret
            </v-btn>
            <v-btn size="small" variant="tonal" color="error" @click="revokeApp(app.uuid)" v-if="app.is_active">
              <v-icon start size="14">mdi-cancel</v-icon> Revoke
            </v-btn>
          </div>
        </v-card>
      </v-col>
      <v-col v-if="!apps.length" cols="12">
        <v-card class="glass-card pa-12 text-center">
          <v-icon size="64" color="grey" class="mb-4">mdi-apps</v-icon>
          <h3>No Applications Yet</h3>
          <p class="text-secondary mt-2">Register your first application to start using CipherLink.</p>
        </v-card>
      </v-col>
    </v-row>

    <!-- Create Dialog -->
    <v-dialog v-model="showCreate" max-width="520">
      <v-card class="glass-card pa-6">
        <h3 class="mb-4">Register Application</h3>
        <v-form @submit.prevent="createApp">
          <v-text-field v-model="form.name" label="Application Name" class="mb-2" />
          <v-textarea v-model="form.description" label="Description" rows="2" class="mb-2" />
          <v-select v-model="form.environment" :items="['development','staging','production']" label="Environment" class="mb-4" />
          <v-btn type="submit" color="primary" block :loading="creating">Create</v-btn>
        </v-form>
      </v-card>
    </v-dialog>

    <!-- Secret Display Dialog -->
    <v-dialog v-model="showSecret" max-width="520" persistent>
      <v-card class="glass-card pa-6">
        <v-icon color="warning" size="40" class="mb-3">mdi-alert</v-icon>
        <h3 class="mb-2">Save Your Client Secret</h3>
        <p class="text-secondary mb-4" style="font-size: 0.9rem;">This secret will only be shown once. Copy it now.</p>
        <div class="code-block pa-4 mb-4 font-mono" style="font-size: 0.8rem; word-break: break-all;">
          {{ newSecret }}
        </div>
        <v-btn color="primary" block @click="showSecret = false">I've Saved It</v-btn>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const apps = ref([])
const showCreate = ref(false)
const showSecret = ref(false)
const newSecret = ref('')
const creating = ref(false)
const form = ref({ name: '', description: '', environment: 'production' })

async function loadApps() {
  try {
    const { data } = await api.get('/api/v1/applications')
    if (data.success) apps.value = data.data
  } catch {}
}

async function createApp() {
  creating.value = true
  try {
    const { data } = await api.post('/api/v1/applications', form.value)
    if (data.success) {
      newSecret.value = data.data.client_secret
      showCreate.value = false
      showSecret.value = true
      form.value = { name: '', description: '', environment: 'production' }
      await loadApps()
    }
  } catch {} finally { creating.value = false }
}

async function rotateSecret(uuid) {
  try {
    const { data } = await api.post(`/api/v1/applications/${uuid}/rotate-secret`)
    if (data.success) {
      newSecret.value = data.data.client_secret
      showSecret.value = true
    }
  } catch {}
}

async function revokeApp(uuid) {
  try {
    await api.post(`/api/v1/applications/${uuid}/revoke`)
    await loadApps()
  } catch {}
}

onMounted(loadApps)
</script>

<style scoped>
.gap-2 { gap: 8px; }
</style>
