<template>
  <div>
    <h1 style="font-weight: 800; font-size: 1.75rem;" class="mb-2">Usage Analytics</h1>
    <p class="text-secondary mb-8">Platform usage and encryption statistics</p>
    <v-row>
      <v-col v-for="s in stats" :key="s.label" cols="12" sm="6" md="3">
        <div class="stat-card">
          <v-icon :color="s.color" size="24" class="mb-2">{{ s.icon }}</v-icon>
          <div class="stat-value" :style="{color: s.hex}">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </v-col>
    </v-row>
    <v-row class="mt-6">
      <v-col cols="12" md="6">
        <v-card class="glass-card pa-6">
          <h3 class="mb-4">Encryption Strategy Distribution</h3>
          <div v-for="s in strategyBars" :key="s.name" class="d-flex align-center mb-3">
            <span style="width:130px;font-size:0.85rem;font-weight:600;">{{ s.name }}</span>
            <div style="flex:1;height:20px;background:rgba(30,41,59,0.8);border-radius:10px;overflow:hidden;">
              <div :style="{width:s.pct+'%',background:s.color,height:'100%',borderRadius:'10px',transition:'width 1s ease'}"></div>
            </div>
            <span class="font-mono ml-3" style="width:50px;text-align:right;font-weight:700;">{{ s.pct }}%</span>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card class="glass-card pa-6">
          <h3 class="mb-4">Recent Activity</h3>
          <div v-for="op in usage?.recent_operations?.slice(0,5) || []" :key="op.uuid" class="d-flex align-center pa-2 mb-2" style="background:rgba(30,41,59,0.4);border-radius:8px;">
            <v-icon size="16" :color="op.type==='encrypt'?'cyan':'purple'" class="mr-3">{{ op.type==='encrypt'?'mdi-lock':'mdi-lock-open' }}</v-icon>
            <div style="flex:1"><strong style="font-size:0.85rem;">{{ op.type }}</strong><span class="text-secondary ml-2" style="font-size:0.75rem;">{{ op.strategy }}</span></div>
            <span :class="'status-badge status-'+(op.status==='success'?'active':'revoked')" style="font-size:0.65rem;">{{ op.status }}</span>
          </div>
          <p v-if="!usage?.recent_operations?.length" class="text-center text-secondary pa-4">No activity yet.</p>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>
<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/services/api'
const usage = ref(null)
onMounted(async () => { try { const { data } = await api.get('/api/v1/usage'); if (data.success) usage.value = data.data } catch {} })
const stats = computed(() => {
  const u = usage.value || {}
  return [
    { label: 'Total Operations', value: u.total_encryption_operations || 0, icon: 'mdi-cog', color: 'cyan', hex: '#06b6d4' },
    { label: 'Files Encrypted', value: u.total_files_encrypted || 0, icon: 'mdi-file-lock', color: 'purple', hex: '#8b5cf6' },
    { label: 'Storage Used', value: fmtSize(u.total_storage_used_bytes || 0), icon: 'mdi-database', color: 'amber', hex: '#f59e0b' },
    { label: 'Failed Ops', value: u.total_failed_requests || 0, icon: 'mdi-alert', color: 'red', hex: '#ef4444' },
  ]
})
const strategyBars = computed(() => {
  const d = usage.value?.encryption_strategy_distribution || {}
  const t = Object.values(d).reduce((a,b)=>a+b,0) || 1
  return [
    { name: 'AES-256', pct: Math.round((d.STANDARD_AES||0)/t*100), color: '#06b6d4' },
    { name: 'Hybrid', pct: Math.round((d.HYBRID_AES_ECC||0)/t*100), color: '#8b5cf6' },
    { name: 'Chunked', pct: Math.round((d.CHUNKED_AES||0)/t*100), color: '#f59e0b' },
  ]
})
function fmtSize(b) { if (!b) return '0 B'; const u = ['B','KB','MB','GB']; const i = Math.floor(Math.log(b)/Math.log(1024)); return (b/Math.pow(1024,i)).toFixed(1)+' '+u[i] }
</script>
