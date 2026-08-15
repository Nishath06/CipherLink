<template>
  <div class="auth-page">
    <div class="auth-bg-grid"></div>
    <v-container class="fill-height">
      <v-row justify="center" align="center">
        <v-col cols="12" sm="8" md="5" lg="4">
          <div class="text-center mb-8">
            <v-icon color="cyan" size="48" class="mb-4">mdi-shield-lock</v-icon>
            <h1 class="gradient-text" style="font-size: 2rem; font-weight: 800;">CipherLink</h1>
            <p class="text-secondary mt-2">Sign in to your account</p>
          </div>

          <v-card class="glass-card pa-8">
            <v-form @submit.prevent="handleLogin" ref="form">
              <v-text-field
                id="login-email"
                v-model="email"
                label="Email"
                type="email"
                prepend-inner-icon="mdi-email-outline"
                :rules="[v => !!v || 'Required', v => /.+@.+/.test(v) || 'Invalid email']"
                class="mb-2"
              />
              <v-text-field
                id="login-password"
                v-model="password"
                label="Password"
                :type="showPass ? 'text' : 'password'"
                prepend-inner-icon="mdi-lock-outline"
                :append-inner-icon="showPass ? 'mdi-eye-off' : 'mdi-eye'"
                @click:append-inner="showPass = !showPass"
                :rules="[v => !!v || 'Required']"
                class="mb-4"
              />

              <v-alert v-if="error" type="error" variant="tonal" class="mb-4" density="compact">
                {{ error }}
              </v-alert>

              <v-btn
                id="login-submit"
                type="submit"
                block
                size="large"
                color="primary"
                :loading="loading"
                class="mb-4"
              >
                <v-icon start>mdi-login</v-icon>
                Sign In
              </v-btn>

              <p class="text-center text-secondary" style="font-size: 0.9rem;">
                Don't have an account?
                <router-link to="/register" class="gradient-text" style="font-weight: 600;">
                  Create one
                </router-link>
              </p>
            </v-form>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const showPass = ref(false)
const loading = ref(false)
const error = ref('')

const form = ref(null)

async function handleLogin() {
  error.value = ''
  if (form.value) {
    const { valid } = await form.value.validate()
    if (!valid) return
  }

  loading.value = true
  try {
    const result = await auth.login(email.value, password.value)
    if (result && result.success) {
      const redirectPath = route.query.redirect || '/dashboard'
      window.location.href = redirectPath
    } else {
      error.value = result?.error?.message || 'Login failed'
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.response?.data?.error?.message || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  position: relative;
  background: var(--cl-bg-primary);
}
.auth-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(6, 182, 212, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(6, 182, 212, 0.02) 1px, transparent 1px);
  background-size: 50px 50px;
}
</style>
