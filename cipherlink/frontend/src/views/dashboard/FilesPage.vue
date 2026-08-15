<template>
  <div>
    <h1 style="font-weight: 800; font-size: 1.75rem;" class="mb-2">Encrypted Files</h1>
    <p class="text-secondary mb-6">All encrypted files stored through CipherLink</p>
    <v-table density="comfortable" class="glass-card">
      <thead><tr><th>Filename</th><th>Strategy</th><th>Size</th><th>Encrypted</th><th>Storage</th><th>Date</th><th>Actions</th></tr></thead>
      <tbody>
        <tr v-for="f in files" :key="f.uuid">
          <td><v-icon size="16" color="cyan" class="mr-2">mdi-file-lock</v-icon>{{ f.original_filename }}</td>
          <td><v-chip size="x-small" variant="tonal" :color="stratColor(f.strategy)">{{ f.strategy }}</v-chip></td>
          <td class="font-mono" style="font-size: 0.8rem;">{{ fmtSize(f.original_size) }}</td>
          <td class="font-mono" style="font-size: 0.8rem;">{{ fmtSize(f.encrypted_size) }}</td>
          <td>{{ f.storage_provider }}</td>
          <td class="text-secondary" style="font-size: 0.8rem;">{{ new Date(f.created_at).toLocaleDateString() }}</td>
          <td><v-btn size="x-small" variant="text" color="error" @click="deleteFile(f.uuid)"><v-icon size="16">mdi-delete</v-icon></v-btn></td>
        </tr>
        <tr v-if="!files.length"><td colspan="7" class="text-center pa-8 text-secondary">No files encrypted yet.</td></tr>
      </tbody>
    </v-table>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'
const files = ref([])
async function load() { try { const { data } = await api.get('/api/v1/files'); if (data.success) files.value = data.data } catch {} }
async function deleteFile(uuid) { try { await api.delete(`/api/v1/files/${uuid}`); await load() } catch {} }
function fmtSize(b) { if (!b) return '0 B'; const u = ['B','KB','MB','GB']; const i = Math.floor(Math.log(b)/Math.log(1024)); return (b/Math.pow(1024,i)).toFixed(1)+' '+u[i] }
function stratColor(s) { return s === 'STANDARD_AES' ? 'cyan' : s === 'HYBRID_AES_ECC' ? 'purple' : 'amber' }
onMounted(load)
</script>
