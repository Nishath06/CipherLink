<template>
  <div class="landing-page">
    <!-- Hero Section -->
    <section class="hero-section">
      <div class="hero-bg-grid"></div>
      <v-container class="hero-content">
        <v-row align="center" justify="center">
          <v-col cols="12" md="8" class="text-center">
            <div class="hero-badge animate-fade-in-up" style="animation-delay: 0.1s">
              <v-icon size="16" color="cyan">mdi-shield-lock</v-icon>
              <span>Enterprise Encryption Platform</span>
            </div>
            <h1 class="hero-title animate-fade-in-up" style="animation-delay: 0.2s">
              <span class="gradient-text">CipherLink</span>
            </h1>
            <p class="hero-subtitle animate-fade-in-up" style="animation-delay: 0.3s">
              Secure media across applications using<br/>
              <strong>adaptive hybrid ECC-AES encryption</strong>
            </p>
            <p class="hero-tagline animate-fade-in-up" style="animation-delay: 0.4s">
              Secure Once. Access Everywhere. Integrate Anywhere. Trust Always.
            </p>
            <div class="hero-actions animate-fade-in-up" style="animation-delay: 0.5s">
              <v-btn size="x-large" color="primary" class="mr-4 hero-btn" @click="$router.push('/register')">
                <v-icon start>mdi-rocket-launch</v-icon>
                Get Started
              </v-btn>
              <v-btn size="x-large" variant="outlined" color="white" class="hero-btn" @click="scrollToWorkflow">
                <v-icon start>mdi-play-circle</v-icon>
                See How It Works
              </v-btn>
            </div>
          </v-col>
        </v-row>
      </v-container>
    </section>

    <!-- Encryption Workflow Visualization -->
    <section id="workflow" class="workflow-section">
      <v-container>
        <h2 class="section-title text-center gradient-text">Adaptive Encryption Engine</h2>
        <p class="section-subtitle text-center">CipherLink automatically selects the optimal encryption strategy</p>

        <div class="workflow-viz">
          <!-- Upload Node -->
          <div class="wf-node wf-upload animate-fade-in-up" style="animation-delay: 0.1s">
            <div class="wf-icon"><v-icon size="32" color="cyan">mdi-cloud-upload</v-icon></div>
            <div class="wf-label">Original File</div>
          </div>
          <div class="wf-connector"><div class="wf-line"></div></div>

          <!-- Analysis -->
          <div class="wf-node wf-engine animate-fade-in-up" style="animation-delay: 0.3s">
            <div class="wf-icon animate-pulse-glow"><v-icon size="36" color="purple">mdi-cog</v-icon></div>
            <div class="wf-label">CipherLink Adaptive Engine</div>
            <div class="wf-sublabel">File Size Analysis</div>
          </div>
          <div class="wf-connector"><div class="wf-line"></div></div>

          <!-- Strategy Selection -->
          <div class="wf-strategies animate-fade-in-up" style="animation-delay: 0.5s">
            <div class="strategy-card" v-for="s in strategies" :key="s.name"
                 :class="{ 'active': activeStrategy === s.name }"
                 @mouseenter="activeStrategy = s.name">
              <div class="strategy-size">{{ s.size }}</div>
              <v-icon :color="s.color" size="28">{{ s.icon }}</v-icon>
              <div class="strategy-name">{{ s.name }}</div>
              <div class="strategy-desc">{{ s.desc }}</div>
            </div>
          </div>
          <div class="wf-connector"><div class="wf-line"></div></div>

          <!-- Encrypted Output -->
          <div class="wf-node wf-output animate-fade-in-up" style="animation-delay: 0.7s">
            <div class="wf-icon"><v-icon size="32" color="green">mdi-lock-check</v-icon></div>
            <div class="wf-label">Encrypted Media</div>
          </div>
          <div class="wf-connector"><div class="wf-line"></div></div>

          <!-- Cloud Storage -->
          <div class="wf-node wf-storage animate-fade-in-up" style="animation-delay: 0.9s">
            <div class="wf-icon"><v-icon size="32" color="amber">mdi-cloud</v-icon></div>
            <div class="wf-label">Cloud Storage</div>
            <div class="wf-sublabel">AWS S3 / Azure / Local</div>
          </div>
        </div>
      </v-container>
    </section>

    <!-- Features -->
    <section class="features-section">
      <v-container>
        <h2 class="section-title text-center gradient-text">Why CipherLink?</h2>
        <v-row class="mt-8">
          <v-col v-for="f in features" :key="f.title" cols="12" md="4">
            <div class="feature-card glass-card pa-6">
              <v-icon :color="f.color" size="40">{{ f.icon }}</v-icon>
              <h3 class="mt-4 mb-2">{{ f.title }}</h3>
              <p class="text-secondary">{{ f.desc }}</p>
            </div>
          </v-col>
        </v-row>
      </v-container>
    </section>

    <!-- Integration Section -->
    <section class="integration-section">
      <v-container>
        <h2 class="section-title text-center gradient-text">Integrate in Minutes</h2>
        <v-row align="center" class="mt-8">
          <v-col cols="12" md="6">
            <div class="code-block">
              <div class="code-header">
                <span class="code-dot red"></span>
                <span class="code-dot yellow"></span>
                <span class="code-dot green"></span>
                <span class="code-lang">Python</span>
              </div>
              <pre><code><span class="code-kw">import</span> requests

response = requests.post(
    <span class="code-str">"https://api.cipherlink.io/api/v1/encryption/encrypt"</span>,
    headers={
        <span class="code-str">"Authorization"</span>: <span class="code-str">f"Bearer </span>{ACCESS_TOKEN}<span class="code-str">"</span>
    },
    files={
        <span class="code-str">"file"</span>: open(<span class="code-str">"image.jpg"</span>, <span class="code-str">"rb"</span>)
    }
)

result = response.json()
<span class="code-comment"># Strategy: HYBRID_AES_ECC</span>
<span class="code-comment"># Algorithm: AES-256-GCM</span></code></pre>
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <h3 class="mb-4">Simple REST API</h3>
            <div class="integration-steps">
              <div class="int-step" v-for="(step, i) in integrationSteps" :key="i">
                <div class="int-num">{{ i + 1 }}</div>
                <div>
                  <strong>{{ step.title }}</strong>
                  <p class="text-secondary">{{ step.desc }}</p>
                </div>
              </div>
            </div>
          </v-col>
        </v-row>
      </v-container>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <v-container class="text-center">
        <h2 class="section-title gradient-text">Ready to Secure Your Application?</h2>
        <p class="section-subtitle mb-6">Create your organization and start encrypting in minutes.</p>
        <v-btn size="x-large" color="primary" @click="$router.push('/register')">
          <v-icon start>mdi-shield-check</v-icon>
          Create Free Account
        </v-btn>
      </v-container>
    </section>

    <!-- Footer -->
    <footer class="landing-footer">
      <v-container>
        <v-row>
          <v-col cols="12" md="4">
            <div class="footer-brand">
              <v-icon color="cyan" size="24" class="mr-2">mdi-shield-lock</v-icon>
              <span class="gradient-text" style="font-size: 1.25rem; font-weight: 700;">CipherLink</span>
            </div>
            <p class="text-secondary mt-2">Enterprise Encryption-as-a-Service</p>
          </v-col>
          <v-col cols="12" md="4">
            <h4 class="mb-3">Platform</h4>
            <div class="footer-links">
              <a href="/login">Login</a>
              <a href="/register">Register</a>
              <a href="/dashboard">Dashboard</a>
            </div>
          </v-col>
          <v-col cols="12" md="4">
            <h4 class="mb-3">Security</h4>
            <div class="footer-links">
              <span>AES-256-GCM</span>
              <span>ECC secp256k1</span>
              <span>ECIES Key Wrapping</span>
            </div>
          </v-col>
        </v-row>
        <v-divider class="my-6" />
        <p class="text-center text-secondary" style="font-size: 0.85rem;">
          © 2026 CipherLink. Encryption-as-a-Service Platform.
        </p>
      </v-container>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const activeStrategy = ref('Hybrid')

const strategies = [
  { name: 'AES-256', size: '< 1 MB', icon: 'mdi-lightning-bolt', color: 'cyan', desc: 'Fast single-pass encryption' },
  { name: 'Hybrid', size: '1–10 MB', icon: 'mdi-shield-half-full', color: 'purple', desc: 'AES + ECC key wrapping' },
  { name: 'Chunked', size: '> 10 MB', icon: 'mdi-view-grid', color: 'amber', desc: 'Parallel chunk encryption' },
]

const features = [
  { icon: 'mdi-shield-lock', color: 'cyan', title: 'Adaptive Encryption', desc: 'Automatically selects the optimal strategy based on file size — AES for speed, hybrid for security, chunked for scale.' },
  { icon: 'mdi-key-chain', color: 'purple', title: 'ECC Key Management', desc: 'Generate, rotate, and revoke secp256k1 encryption keys. Private keys never stored as plaintext.' },
  { icon: 'mdi-api', color: 'green', title: 'REST API First', desc: 'Clean versioned REST API with OAuth2 authentication, scoped permissions, and comprehensive documentation.' },
  { icon: 'mdi-domain', color: 'amber', title: 'Multi-Tenant', desc: 'Full organization isolation. Each tenant has independent keys, applications, storage, and audit logs.' },
  { icon: 'mdi-cloud-sync', color: 'blue', title: 'Storage Abstraction', desc: 'Pluggable storage providers — AWS S3, Azure Blob, or local. Switch without changing encryption logic.' },
  { icon: 'mdi-chart-line', color: 'pink', title: 'Audit & Analytics', desc: 'Complete audit trail of every encryption operation. Real-time usage dashboards and security monitoring.' },
]

const integrationSteps = [
  { title: 'Register Your Application', desc: 'Create an organization and register your app to receive API credentials.' },
  { title: 'Authenticate', desc: 'Use client_id and client_secret to obtain a scoped access token.' },
  { title: 'Encrypt', desc: 'Send files to CipherLink. We handle strategy selection, encryption, and storage.' },
  { title: 'Decrypt', desc: 'Retrieve and decrypt files through authorized API calls.' },
]

function scrollToWorkflow() {
  document.getElementById('workflow')?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<style scoped>
.landing-page {
  min-height: 100vh;
}

/* ── Hero ──────────────────────────────────────────────────────────── */
.hero-section {
  position: relative;
  min-height: 90vh;
  display: flex;
  align-items: center;
  overflow: hidden;
}
.hero-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(6, 182, 212, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(6, 182, 212, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
}
.hero-content {
  position: relative;
  z-index: 1;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background: rgba(6, 182, 212, 0.1);
  border: 1px solid rgba(6, 182, 212, 0.2);
  border-radius: 40px;
  font-size: 0.85rem;
  color: #06b6d4;
  margin-bottom: 24px;
}
.hero-title {
  font-size: clamp(3rem, 8vw, 6rem);
  font-weight: 900;
  line-height: 1;
  margin-bottom: 20px;
}
.hero-subtitle {
  font-size: 1.25rem;
  color: var(--cl-text-secondary);
  line-height: 1.6;
  margin-bottom: 12px;
}
.hero-tagline {
  font-size: 1rem;
  color: var(--cl-text-muted);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 40px;
}
.hero-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}
.hero-btn {
  text-transform: none;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* ── Sections ─────────────────────────────────────────────────────── */
section {
  padding: 100px 0;
}
.section-title {
  font-size: 2.5rem;
  font-weight: 800;
}
.section-subtitle {
  color: var(--cl-text-secondary);
  font-size: 1.1rem;
  margin-top: 12px;
}

/* ── Workflow ─────────────────────────────────────────────────────── */
.workflow-viz {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  margin-top: 60px;
}
.wf-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.wf-icon {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(30, 41, 59, 0.8);
  border: 2px solid var(--cl-border);
  display: flex;
  align-items: center;
  justify-content: center;
}
.wf-label {
  font-weight: 600;
  font-size: 1rem;
}
.wf-sublabel {
  color: var(--cl-text-muted);
  font-size: 0.8rem;
}
.wf-connector {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.wf-line {
  width: 2px;
  height: 100%;
  background: linear-gradient(to bottom, #06b6d4, #8b5cf6);
}

/* ── Strategy Cards ───────────────────────────────────────────────── */
.wf-strategies {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  justify-content: center;
}
.strategy-card {
  width: 200px;
  padding: 24px 16px;
  text-align: center;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid var(--cl-border);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}
.strategy-card:hover,
.strategy-card.active {
  border-color: rgba(6, 182, 212, 0.5);
  transform: translateY(-4px);
  box-shadow: var(--cl-glow-cyan);
}
.strategy-size {
  font-family: var(--cl-font-mono);
  font-size: 0.75rem;
  color: var(--cl-text-muted);
  margin-bottom: 12px;
}
.strategy-name {
  font-weight: 700;
  margin-top: 8px;
}
.strategy-desc {
  font-size: 0.8rem;
  color: var(--cl-text-secondary);
  margin-top: 4px;
}

/* ── Feature Cards ────────────────────────────────────────────────── */
.feature-card {
  height: 100%;
  transition: all 0.3s ease;
}
.feature-card h3 {
  font-size: 1.1rem;
  font-weight: 700;
}
.text-secondary {
  color: var(--cl-text-secondary) !important;
}

/* ── Code Block ───────────────────────────────────────────────────── */
.code-block {
  background: #0d1117;
  border: 1px solid var(--cl-border);
  border-radius: 12px;
  overflow: hidden;
}
.code-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.5);
  border-bottom: 1px solid var(--cl-border);
}
.code-dot {
  width: 10px; height: 10px; border-radius: 50%;
}
.code-dot.red { background: #ff5f56; }
.code-dot.yellow { background: #ffbd2e; }
.code-dot.green { background: #27c93f; }
.code-lang {
  margin-left: auto;
  font-size: 0.75rem;
  color: var(--cl-text-muted);
}
.code-block pre {
  padding: 20px;
  font-family: var(--cl-font-mono);
  font-size: 0.85rem;
  line-height: 1.6;
  color: #e6edf3;
  overflow-x: auto;
}
.code-kw { color: #ff7b72; }
.code-str { color: #a5d6ff; }
.code-comment { color: #8b949e; }

/* ── Integration Steps ────────────────────────────────────────────── */
.int-step {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  padding: 16px 0;
}
.int-num {
  width: 32px; height: 32px; min-width: 32px;
  border-radius: 50%;
  background: var(--cl-gradient-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85rem;
}

/* ── CTA ──────────────────────────────────────────────────────────── */
.cta-section {
  background: radial-gradient(ellipse at center, rgba(6, 182, 212, 0.08), transparent 70%);
}

/* ── Footer ───────────────────────────────────────────────────────── */
.landing-footer {
  padding: 60px 0 30px;
  border-top: 1px solid var(--cl-border);
}
.footer-brand {
  display: flex;
  align-items: center;
}
.footer-links {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.footer-links a,
.footer-links span {
  color: var(--cl-text-secondary);
  text-decoration: none;
  font-size: 0.9rem;
}
.footer-links a:hover {
  color: #06b6d4;
}
</style>
