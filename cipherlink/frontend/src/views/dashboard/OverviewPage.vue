<template>
  <div>
    <h1 class="mb-2" style="font-weight: 800; font-size: 1.75rem;">Dashboard</h1>
    <p class="text-secondary mb-8">Encryption platform overview</p>

    <!-- Stat Cards -->
    <v-row>
      <v-col v-for="stat in stats" :key="stat.label" cols="12" sm="6" md="4" lg="2">
        <div class="stat-card">
          <v-icon :color="stat.color" size="24" class="mb-2">{{ stat.icon }}</v-icon>
          <div class="stat-value" :style="{ color: stat.hex }">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </v-col>
    </v-row>

    <!-- Charts Row -->
    <v-row class="mt-6">
      <v-col cols="12" md="8">
        <v-card class="glass-card pa-6">
          <h3 class="mb-4">Encryption Strategy Distribution</h3>
          <div class="strategy-bars">
            <div v-for="s in strategyData" :key="s.name" class="strategy-bar-row">
              <div class="sb-label">{{ s.name }}</div>
              <div class="sb-track">
                <div class="sb-fill" :style="{ width: s.pct + '%', background: s.color }"></div>
              </div>
              <div class="sb-pct">{{ s.pct }}%</div>
            </div>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card class="glass-card pa-6" style="height: 100%;">
          <h3 class="mb-4">Quick Actions</h3>
          <v-btn block color="primary" variant="tonal" class="mb-3" @click="$router.push('/dashboard/encryption')">
            <v-icon start>mdi-lock-plus</v-icon> Encrypt File
          </v-btn>
          <v-btn block color="secondary" variant="tonal" class="mb-3" @click="$router.push('/dashboard/keys')">
            <v-icon start>mdi-key-plus</v-icon> Create Key
          </v-btn>
          <v-btn block color="success" variant="tonal" class="mb-3" @click="$router.push('/dashboard/applications')">
            <v-icon start>mdi-plus-circle</v-icon> Register App
          </v-btn>
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent Operations -->
    <v-row class="mt-6">
      <v-col cols="12">
        <v-card class="glass-card pa-6">
          <h3 class="mb-4">Recent Operations</h3>
          <v-table density="comfortable" class="bg-transparent">
            <thead>
              <tr>
                <th>Type</th><th>Strategy</th><th>Size</th><th>Duration</th><th>Status</th><th>Time</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="op in usage?.recent_operations || []" :key="op.uuid">
                <td>
                  <v-chip size="x-small" :color="op.type === 'encrypt' ? 'cyan' : 'purple'" variant="tonal">
                    {{ op.type }}
                  </v-chip>
                </td>
                <td class="font-mono" style="font-size: 0.8rem;">{{ op.strategy || '—' }}</td>
                <td>{{ formatSize(op.file_size) }}</td>
                <td>{{ op.duration_ms ? op.duration_ms.toFixed(1) + 'ms' : '—' }}</td>
                <td><span :class="'status-badge status-' + (op.status === 'success' ? 'active' : 'revoked')">{{ op.status }}</span></td>
                <td class="text-secondary" style="font-size: 0.8rem;">{{ formatDate(op.created_at) }}</td>
              </tr>
              <tr v-if="!usage?.recent_operations?.length">
                <td colspan="6" class="text-center text-secondary pa-8">No operations yet. Encrypt your first file!</td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/services/api'

const usage = ref(null)

onMounted(async () => {
  try {
    const { data } = await api.get('/api/v1/usage')
    if (data.success) usage.value = data.data
  } catch { /* empty state */ }
})

const stats = computed(() => {
  const u = usage.value || {}
  return [
    { label: 'Applications', value: u.total_applications || 0, icon: 'mdi-apps', color: 'cyan', hex: '#06b6d4' },
    { label: 'Encrypted Files', value: u.total_files_encrypted || 0, icon: 'mdi-file-lock', color: 'purple', hex: '#8b5cf6' },
    { label: 'Operations', value: u.total_encryption_operations || 0, icon: 'mdi-cog', color: 'green', hex: '#10b981' },
    { label: 'Storage Used', value: formatSize(u.total_storage_used_bytes || 0), icon: 'mdi-database', color: 'amber', hex: '#f59e0b' },
    { label: 'API Requests', value: u.total_api_requests || 0, icon: 'mdi-api', color: 'blue', hex: '#3b82f6' },
    { label: 'Failed', value: u.total_failed_requests || 0, icon: 'mdi-alert-circle', color: 'red', hex: '#ef4444' },
  ]
})

const strategyData = computed(() => {
  const dist = usage.value?.encryption_strategy_distribution || {}
  const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1
  return [
    { name: 'AES-256', pct: Math.round((dist.STANDARD_AES || 0) / total * 100), color: '#06b6d4' },
    { name: 'Hybrid AES+ECC', pct: Math.round((dist.HYBRID_AES_ECC || 0) / total * 100), color: '#8b5cf6' },
    { name: 'Chunked', pct: Math.round((dist.CHUNKED_AES || 0) / total * 100), color: '#f59e0b' },
  ]
})

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i]
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString()
}
</script>

<style scoped>
.strategy-bars { display: flex; flex-direction: column; gap: 16px; }
.strategy-bar-row { display: flex; align-items: center; gap: 12px; }
.sb-label { width: 120px; font-size: 0.85rem; font-weight: 600; }
.sb-track { flex: 1; height: 24px; background: rgba(30, 41, 59, 0.8); border-radius: 12px; overflow: hidden; }
.sb-fill { height: 100%; border-radius: 12px; transition: width 1s ease; }
.sb-pct { width: 50px; text-align: right; font-weight: 700; font-family: var(--cl-font-mono); font-size: 0.9rem; }
</style>
