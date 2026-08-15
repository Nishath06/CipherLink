import { defineStore } from 'pinia'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('cl_user') || 'null'),
    accessToken: localStorage.getItem('cl_access_token') || null,
    refreshToken: localStorage.getItem('cl_refresh_token') || null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.accessToken,
    organizationName: (state) => state.user?.organization_name || '',
    userRole: (state) => state.user?.role || '',
  },

  actions: {
    async register(payload) {
      const { data } = await api.post('/api/v1/auth/register', payload)
      if (data.success) {
        this.setAuth(data.data.user, data.data.tokens)
      }
      return data
    },

    async login(email, password) {
      const { data } = await api.post('/api/v1/auth/login', { email, password })
      if (data.success) {
        this.setAuth(data.data.user, data.data.tokens)
      }
      return data
    },

    async loginWithGoogle(payload) {
      const { data } = await api.post('/api/v1/auth/google', payload)
      if (data.success) {
        this.setAuth(data.data.user, data.data.tokens)
      }
      return data
    },

    setAuth(user, tokens) {
      this.user = user
      this.accessToken = tokens.access_token
      this.refreshToken = tokens.refresh_token
      localStorage.setItem('cl_user', JSON.stringify(user))
      localStorage.setItem('cl_access_token', tokens.access_token)
      localStorage.setItem('cl_refresh_token', tokens.refresh_token)
    },

    logout() {
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      localStorage.removeItem('cl_user')
      localStorage.removeItem('cl_access_token')
      localStorage.removeItem('cl_refresh_token')
    },

    async refreshAccessToken() {
      try {
        const { data } = await api.post('/api/v1/auth/refresh', {
          refresh_token: this.refreshToken,
        })
        if (data.success) {
          this.accessToken = data.data.access_token
          localStorage.setItem('cl_access_token', data.data.access_token)
        }
      } catch {
        this.logout()
      }
    },
  },
})
