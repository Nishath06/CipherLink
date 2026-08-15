import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const cipherLinkTheme = {
  dark: true,
  colors: {
    background: '#0a0e1a',
    surface: '#111827',
    'surface-bright': '#1a2332',
    'surface-variant': '#1e293b',
    primary: '#06b6d4',
    'primary-darken-1': '#0891b2',
    secondary: '#8b5cf6',
    'secondary-darken-1': '#7c3aed',
    accent: '#22d3ee',
    error: '#ef4444',
    warning: '#f59e0b',
    info: '#3b82f6',
    success: '#10b981',
    'on-background': '#e2e8f0',
    'on-surface': '#e2e8f0',
  },
}

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'cipherLinkTheme',
    themes: { cipherLinkTheme },
  },
  defaults: {
    VCard: { rounded: 'lg', elevation: 0 },
    VBtn: { rounded: 'lg' },
    VTextField: { variant: 'outlined', density: 'comfortable' },
    VSelect: { variant: 'outlined', density: 'comfortable' },
  },
})
