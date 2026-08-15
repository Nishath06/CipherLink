<template>
  <v-app>
    <!-- Sidebar Navigation -->
    <v-navigation-drawer v-model="drawer" :rail="rail" permanent class="dashboard-nav" color="transparent">
      <div class="nav-header pa-4">
        <div class="d-flex align-center" :class="{ 'justify-center': rail }">
          <v-icon color="cyan" size="28">mdi-shield-lock</v-icon>
          <span v-if="!rail" class="gradient-text ml-3" style="font-size: 1.1rem; font-weight: 700;">CipherLink</span>
        </div>
      </div>

      <v-divider class="mx-3 mb-2" style="border-color: var(--cl-border);" />

      <v-list density="compact" nav class="px-2">
        <v-list-item
          v-for="item in navItems" :key="item.route"
          :to="item.route"
          :prepend-icon="item.icon"
          :title="item.title"
          rounded="lg"
          class="nav-item mb-1"
          :class="{ 'nav-active': $route.path === item.route }"
        />
      </v-list>

      <template #append>
        <v-list density="compact" nav class="px-2 mb-2">
          <v-list-item
            prepend-icon="mdi-chevron-left"
            :title="rail ? '' : 'Collapse'"
            @click="rail = !rail"
            rounded="lg"
            class="nav-item"
          />
          <v-list-item
            prepend-icon="mdi-logout"
            title="Logout"
            @click="handleLogout"
            rounded="lg"
            class="nav-item"
          />
        </v-list>
      </template>
    </v-navigation-drawer>

    <!-- Top Bar -->
    <v-app-bar flat color="transparent" class="dashboard-topbar">
      <v-toolbar-title>
        <span class="text-secondary" style="font-size: 0.85rem;">Organization:</span>
        <span class="ml-2 font-weight-bold">{{ auth.organizationName }}</span>
      </v-toolbar-title>
      <v-spacer />
      <v-chip variant="tonal" color="cyan" size="small" class="mr-4">
        <v-icon start size="14">mdi-account</v-icon>
        {{ auth.user?.username }}
      </v-chip>
    </v-app-bar>

    <!-- Main Content -->
    <v-main class="dashboard-main">
      <v-container fluid class="pa-6">
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const drawer = ref(true)
const rail = ref(false)

const navItems = [
  { title: 'Overview', icon: 'mdi-view-dashboard', route: '/dashboard' },
  { title: 'Applications', icon: 'mdi-apps', route: '/dashboard/applications' },
  { title: 'Keys', icon: 'mdi-key-chain', route: '/dashboard/keys' },
  { title: 'Encryption', icon: 'mdi-shield-lock', route: '/dashboard/encryption' },
  { title: 'Files', icon: 'mdi-file-lock', route: '/dashboard/files' },
  { title: 'Audit Logs', icon: 'mdi-clipboard-text-clock', route: '/dashboard/audit' },
  { title: 'Usage', icon: 'mdi-chart-line', route: '/dashboard/usage' },
  { title: 'API Docs', icon: 'mdi-code-braces', route: '/dashboard/api-docs' },
]

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.dashboard-nav {
  background: rgba(17, 24, 39, 0.95) !important;
  border-right: 1px solid var(--cl-border) !important;
}
.nav-header {
  min-height: 64px;
  display: flex;
  align-items: center;
}
.nav-item {
  color: var(--cl-text-secondary) !important;
  transition: all 0.2s ease;
}
.nav-item:hover {
  color: var(--cl-text-primary) !important;
  background: rgba(6, 182, 212, 0.08) !important;
}
.nav-active {
  color: #06b6d4 !important;
  background: rgba(6, 182, 212, 0.12) !important;
}
.dashboard-topbar {
  border-bottom: 1px solid var(--cl-border) !important;
  background: rgba(10, 14, 26, 0.8) !important;
  backdrop-filter: blur(20px);
}
.dashboard-main {
  background: var(--cl-bg-primary);
}
</style>
