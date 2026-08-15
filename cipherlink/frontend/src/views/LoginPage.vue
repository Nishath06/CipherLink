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
                class="mb-3"
              >
                <v-icon start>mdi-login</v-icon>
                Sign In
              </v-btn>

              <v-divider class="my-4 text-secondary" text="OR CONTINUE WITH"></v-divider>

              <v-btn
                id="google-login-btn"
                block
                size="large"
                variant="outlined"
                color="secondary"
                class="text-none mb-4"
                :loading="googleLoading"
                @click="handleGoogleSignIn"
                style="border-color: rgba(255, 255, 255, 0.2); font-weight: 600;"
              >
                <svg class="mr-2" width="18" height="18" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                Sign in with Google
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
const googleLoading = ref(false)
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

const GOOGLE_CLIENT_ID = '324594671504-acvi8b855v595drr2vba8npqhu9n9knj.apps.googleusercontent.com'

async function handleGoogleSignIn() {
  error.value = ''
  googleLoading.value = true

  try {
    if (window.google?.accounts?.oauth2) {
      const client = window.google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: 'openid email profile',
        prompt: 'select_account',
        callback: async (tokenResponse) => {
          if (tokenResponse.error) {
            error.value = 'Google sign-in cancelled or closed.'
            googleLoading.value = false
            return
          }
          try {
            const result = await auth.loginWithGoogle({
              credential: tokenResponse.access_token,
            })
            if (result && result.success) {
              const redirectPath = route.query.redirect || '/dashboard'
              window.location.href = redirectPath
            } else {
              error.value = result?.error?.message || 'Google login failed'
            }
          } catch (err) {
            error.value = err.response?.data?.detail || 'Google login failed'
          } finally {
            googleLoading.value = false
          }
        },
      })
      client.requestAccessToken({ prompt: 'select_account' })
    } else {
      await promptFallback()
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.response?.data?.error?.message || 'Google login failed'
    googleLoading.value = false
  }
}

async function promptFallback() {
  try {
    let userEmail = prompt('Enter your Google email for OAuth SSO:', 'user@google.com')
    if (!userEmail) {
      googleLoading.value = false
      return
    }

    const result = await auth.loginWithGoogle({
      email: userEmail,
      full_name: userEmail.split('@')[0],
      credential: 'google_oauth_token_' + Date.now(),
    })

    if (result && result.success) {
      const redirectPath = route.query.redirect || '/dashboard'
      window.location.href = redirectPath
    } else {
      error.value = result?.error?.message || 'Google authentication failed'
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.response?.data?.error?.message || 'Google login failed'
  } finally {
    googleLoading.value = false
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
