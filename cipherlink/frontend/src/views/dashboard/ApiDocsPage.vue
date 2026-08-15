<template>
  <div>
    <h1 style="font-weight: 800; font-size: 1.75rem;" class="mb-2">API Documentation</h1>
    <p class="text-secondary mb-8">Integrate CipherLink into your application</p>

    <v-row>
      <v-col cols="12" md="4">
        <v-card class="glass-card pa-5 mb-4">
          <h3 class="mb-3"><v-icon color="cyan" class="mr-2">mdi-link</v-icon>Base URL</h3>
          <div class="code-block pa-3 font-mono" style="font-size: 0.85rem;">{{ baseUrl }}</div>
        </v-card>
        <v-card class="glass-card pa-5 mb-4">
          <h3 class="mb-3"><v-icon color="purple" class="mr-2">mdi-key</v-icon>Authentication</h3>
          <p class="text-secondary mb-3" style="font-size: 0.85rem;">Use OAuth2 Client Credentials to obtain an access token.</p>
          <div class="code-block pa-3 font-mono" style="font-size: 0.75rem;">
POST /api/v1/auth/token
{
  "client_id": "cl_app_...",
  "client_secret": "cl_secret_..."
}
          </div>
        </v-card>
        <v-card class="glass-card pa-5">
          <h3 class="mb-3"><v-icon color="green" class="mr-2">mdi-book-open</v-icon>Full Docs</h3>
          <v-btn block color="primary" variant="tonal" href="/docs" target="_blank">
            <v-icon start>mdi-open-in-new</v-icon> Swagger UI
          </v-btn>
          <v-btn block color="secondary" variant="tonal" class="mt-2" href="/redoc" target="_blank">
            <v-icon start>mdi-open-in-new</v-icon> ReDoc
          </v-btn>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <v-card class="glass-card pa-5 mb-4">
          <h3 class="mb-4">Quick Start — Python</h3>
          <div class="code-block pa-4 font-mono" style="font-size: 0.8rem; white-space: pre; overflow-x: auto;">
<span style="color:#ff7b72;">import</span> requests

<span style="color:#8b949e;"># 1. Get access token</span>
token_resp = requests.post(
    <span style="color:#a5d6ff;">"{{ baseUrl }}/api/v1/auth/token"</span>,
    json={
        <span style="color:#a5d6ff;">"client_id"</span>: <span style="color:#a5d6ff;">"cl_app_xxx"</span>,
        <span style="color:#a5d6ff;">"client_secret"</span>: <span style="color:#a5d6ff;">"cl_secret_xxx"</span>
    }
)
token = token_resp.json()[<span style="color:#a5d6ff;">"data"</span>][<span style="color:#a5d6ff;">"access_token"</span>]

<span style="color:#8b949e;"># 2. Encrypt a file</span>
enc_resp = requests.post(
    <span style="color:#a5d6ff;">"{{ baseUrl }}/api/v1/encryption/encrypt"</span>,
    headers={<span style="color:#a5d6ff;">"Authorization"</span>: <span style="color:#a5d6ff;">f"Bearer {token}"</span>},
    files={<span style="color:#a5d6ff;">"file"</span>: open(<span style="color:#a5d6ff;">"photo.jpg"</span>, <span style="color:#a5d6ff;">"rb"</span>)}
)
file_id = enc_resp.json()[<span style="color:#a5d6ff;">"data"</span>][<span style="color:#a5d6ff;">"file_id"</span>]

<span style="color:#8b949e;"># 3. Decrypt</span>
dec_resp = requests.post(
    <span style="color:#a5d6ff;">f"{{ baseUrl }}/api/v1/encryption/decrypt/{file_id}"</span>,
    headers={<span style="color:#a5d6ff;">"Authorization"</span>: <span style="color:#a5d6ff;">f"Bearer {token}"</span>}
)
          </div>
        </v-card>

        <v-card class="glass-card pa-5 mb-4">
          <h3 class="mb-4">Quick Start — cURL</h3>
          <div class="code-block pa-4 font-mono" style="font-size: 0.8rem; white-space: pre; overflow-x: auto;">
<span style="color:#8b949e;"># Get token</span>
curl -X POST {{ baseUrl }}/api/v1/auth/token \
  -H <span style="color:#a5d6ff;">"Content-Type: application/json"</span> \
  -d <span style="color:#a5d6ff;">'{"client_id":"...","client_secret":"..."}'</span>

<span style="color:#8b949e;"># Encrypt file</span>
curl -X POST {{ baseUrl }}/api/v1/encryption/encrypt \
  -H <span style="color:#a5d6ff;">"Authorization: Bearer $TOKEN"</span> \
  -F <span style="color:#a5d6ff;">"file=@photo.jpg"</span>
          </div>
        </v-card>

        <v-card class="glass-card pa-5">
          <h3 class="mb-4">API Scopes</h3>
          <v-table density="compact" class="bg-transparent">
            <thead><tr><th>Scope</th><th>Description</th></tr></thead>
            <tbody>
              <tr v-for="s in scopes" :key="s.name">
                <td class="font-mono" style="font-size: 0.8rem; color: #06b6d4;">{{ s.name }}</td>
                <td class="text-secondary">{{ s.desc }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>
<script setup>
const baseUrl = window.location.origin
const scopes = [
  { name: 'media:encrypt', desc: 'Encrypt files through CipherLink' },
  { name: 'media:decrypt', desc: 'Decrypt files through CipherLink' },
  { name: 'keys:read', desc: 'Read encryption key metadata' },
  { name: 'keys:use', desc: 'Use encryption keys for operations' },
  { name: 'storage:write', desc: 'Upload to configured storage' },
  { name: 'storage:read', desc: 'Download from configured storage' },
  { name: 'audit:read', desc: 'Read audit logs' },
]
</script>
