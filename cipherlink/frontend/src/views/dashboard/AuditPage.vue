<template>
  <div>
    <h1 style="font-weight: 800; font-size: 1.75rem;" class="mb-2">Audit Logs</h1>
    <p class="text-secondary mb-6">Security event history</p>
    <v-table density="comfortable" class="glass-card">
      <thead><tr><th>Event</th><th>Resource</th><th>IP</th><th>Status</th><th>Time</th></tr></thead>
      <tbody>
        <tr v-for="l in logs" :key="l.uuid">
          <td><v-chip size="x-small" variant="tonal" :color="eventColor(l.event_type)">{{ l.event_type }}</v-chip></td>
          <td class="font-mono" style="font-size: 0.8rem;">{{ l.resource_type ? l.resource_type + ':' + (l.resource_id?.substring(0,8) || '') : '—' }}</td>
          <td class="text-secondary" style="font-size: 0.8rem;">{{ l.ip_address || '—' }}</td>
          <td><span :class="'status-badge status-' + (l.status === 'success' ? 'active' : 'revoked')">{{ l.status }}</span></td>
          <td class="text-secondary" style="font-size: 0.8rem;">{{ new Date(l.created_at).toLocaleString() }}</td>
        </tr>
        <tr v-if="!logs.length"><td colspan="5" class="text-center pa-8 text-secondary">No audit events.</td></tr>
      </tbody>
    </v-table>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'
const logs = ref([])
async function load() { try { const { data } = await api.get('/api/v1/audit/logs'); if (data.success) logs.value = data.data.logs } catch {} }
function eventColor(t) { if (t.includes('FAILED')) return 'error'; if (t.includes('KEY')) return 'purple'; if (t.includes('FILE')) return 'cyan'; return 'grey' }
onMounted(load)
</script>
