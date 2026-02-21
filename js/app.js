/**
 * ═══════════════════════════════════════════════
 * CYCORA — Unified Application Logic
 * Router, API Client, Auth, Chat, Community
 * ═══════════════════════════════════════════════
 */

const API_BASE = 'https://tink-her-hack-temp-gdf8.onrender.com/api';

// ─────────────────────────────────────────────
// SESSION MANAGEMENT
// ─────────────────────────────────────────────
const CycSession = {
  get() {
    try { return JSON.parse(localStorage.getItem('cycora_session') || 'null'); }
    catch { return null; }
  },
  set(data) { localStorage.setItem('cycora_session', JSON.stringify(data)); },
  clear() { localStorage.removeItem('cycora_session'); },
  getUserId() { const s = this.get(); return s ? s.user_id : null; },
  getName() { const s = this.get(); return s ? s.name : 'User'; },
  isLoggedIn() { return !!this.get(); }
};

// ─────────────────────────────────────────────
// TOAST NOTIFICATIONS
// ─────────────────────────────────────────────
function showToast(message, type = '') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  requestAnimationFrame(() => { toast.classList.add('show'); });
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ─────────────────────────────────────────────
// API CLIENT
// ─────────────────────────────────────────────
const CycAPI = {
  async post(endpoint, data) {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return await res.json();
    } catch (e) {
      console.error('API Error:', e);
      return { status: 'error', message: 'Server unavailable. Please start the backend.' };
    }
  },
  async get(endpoint) {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`);
      return await res.json();
    } catch (e) {
      console.error('API Error:', e);
      return { status: 'error', message: 'Server unavailable.' };
    }
  },
  async put(endpoint, data) {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return await res.json();
    } catch (e) {
      console.error('API Error:', e);
      return { status: 'error', message: 'Server unavailable.' };
    }
  }
};

// ─────────────────────────────────────────────
// ROUTER
// ─────────────────────────────────────────────
const SCREENS_NEEDING_AUTH = ['dashboard', 'analytics', 'chat', 'community', 'rewards', 'settings', 'setup'];
const SCREENS_WITH_NAV = ['dashboard', 'analytics', 'chat', 'community', 'rewards', 'settings'];

const CycRouter = {
  current: null,
  navigate(screen) {
    // Auth guard
    if (SCREENS_NEEDING_AUTH.includes(screen) && !CycSession.isLoggedIn()) {
      screen = 'login';
    }
    window.location.hash = screen;
  },
  init() {
    window.addEventListener('hashchange', () => this.handleRoute());
    this.handleRoute();
  },
  handleRoute() {
    let hash = window.location.hash.replace('#', '') || 'splash';

    // Auth guard
    if (SCREENS_NEEDING_AUTH.includes(hash) && !CycSession.isLoggedIn()) {
      hash = 'login';
      window.location.hash = 'login';
    }

    // Hide all screens
    document.querySelectorAll('.screen').forEach(s => {
      s.classList.remove('active');
    });

    // Show target screen
    const target = document.getElementById(`screen-${hash}`);
    if (target) {
      // Small delay for transition effect
      setTimeout(() => target.classList.add('active'), 30);
      this.current = hash;
    } else {
      const fallback = document.getElementById('screen-splash');
      if (fallback) setTimeout(() => fallback.classList.add('active'), 30);
      this.current = 'splash';
    }

    // Bottom nav visibility
    const nav = document.getElementById('bottom-nav');
    if (nav) {
      if (SCREENS_WITH_NAV.includes(hash)) {
        nav.classList.add('visible');
        this.updateNavActive(hash);
      } else {
        nav.classList.remove('visible');
      }
    }

    // Trigger screen-specific init
    this.onScreenEnter(hash);

    // Scroll to top
    window.scrollTo(0, 0);
  },
  updateNavActive(screen) {
    document.querySelectorAll('.bottom-nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.screen === screen);
    });
  },
  onScreenEnter(screen) {
    switch (screen) {
      case 'dashboard': initDashboard(); break;
      case 'analytics': initAnalytics(); break;
      case 'chat': initChat(); break;
      case 'community': initCommunity(); break;
      case 'rewards': initRewards(); break;
      case 'settings': initSettings(); break;
    }
  }
};

// ─────────────────────────────────────────────
// AUTH: LOGIN
// ─────────────────────────────────────────────
function initLogin() {
  const form = document.getElementById('login-form');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    const origText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Signing in...';
    btn.disabled = true;

    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    const result = await CycAPI.post('/login', { email, password });

    if (result.status === 'success') {
      CycSession.set(result);
      showToast(`Welcome back, ${result.name || 'friend'}! ❤️`, 'success');
      // Check if user has cycle data
      const pred = await CycAPI.get(`/prediction/${result.user_id}`);
      if (pred.status === 'success') {
        CycRouter.navigate('dashboard');
      } else {
        CycRouter.navigate('setup');
      }
    } else {
      showToast(result.message || 'Login failed', 'error');
      btn.innerHTML = origText;
      btn.disabled = false;
    }
  });
}

// ─────────────────────────────────────────────
// AUTH: REGISTER
// ─────────────────────────────────────────────
function initRegister() {
  const form = document.getElementById('register-form');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('reg-name').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const confirm = document.getElementById('reg-confirm-password').value;
    const terms = document.getElementById('reg-terms').checked;

    if (password !== confirm) {
      showToast('Passwords do not match', 'error');
      return;
    }
    if (!terms) {
      showToast('Please accept Terms & Privacy Policy', 'error');
      return;
    }

    const btn = form.querySelector('button[type="submit"]');
    const origText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Creating account...';
    btn.disabled = true;

    const result = await CycAPI.post('/register', { name, email, password });

    if (result.status === 'success') {
      CycSession.set(result);
      showToast('Account created! Let\'s set up your cycle. 🎉', 'success');
      CycRouter.navigate('setup');
    } else {
      showToast(result.message || 'Registration failed', 'error');
      btn.innerHTML = origText;
      btn.disabled = false;
    }
  });
}

// ─────────────────────────────────────────────
// CYCLE SETUP
// ─────────────────────────────────────────────
function initSetup() {
  const btn = document.getElementById('setup-submit-btn');
  if (!btn || btn.dataset.bound) return;
  btn.dataset.bound = 'true';
  btn.addEventListener('click', async () => {
    const lastPeriod = document.getElementById('setup-last-period').value;
    const cycleLength = document.getElementById('setup-cycle-length').value;
    const periodLength = document.getElementById('setup-period-length').value;
    const mood = document.getElementById('setup-mood').value;

    if (!lastPeriod) {
      showToast('Please enter your last period date', 'error');
      return;
    }

    const origText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Analyzing...';
    btn.disabled = true;

    const result = await CycAPI.post('/cycle', {
      user_id: CycSession.getUserId(),
      last_period_date: lastPeriod,
      cycle_length: parseInt(cycleLength) || 28,
      period_length: parseInt(periodLength) || 5,
      mood: mood
    });

    if (result.status === 'success') {
      showToast('Cycle insights generated! 🔮', 'success');
      CycRouter.navigate('dashboard');
    } else {
      showToast(result.message || 'Failed to save cycle data', 'error');
      btn.innerHTML = origText;
      btn.disabled = false;
    }
  });
}

// ─────────────────────────────────────────────
// DASHBOARD
// ─────────────────────────────────────────────
async function initDashboard() {
  const userId = CycSession.getUserId();
  if (!userId) return;

  const result = await CycAPI.get(`/prediction/${userId}`);
  if (result.status !== 'success') return;

  const p = result.predictions;

  // Update cycle day
  const dayEl = document.getElementById('dash-cycle-day');
  if (dayEl) dayEl.textContent = p.day_of_cycle;
  const totalEl = document.getElementById('dash-cycle-total');
  if (totalEl) totalEl.textContent = `of ${p.cycle_length}`;

  // Update phase
  const phaseEl = document.getElementById('dash-phase-name');
  if (phaseEl) phaseEl.textContent = `${p.phase} Phase`;
  const phaseTitleEl = document.getElementById('dash-phase-title');
  if (phaseTitleEl) phaseTitleEl.textContent = `Current Phase: ${p.phase}`;
  const phaseDescEl = document.getElementById('dash-phase-desc');
  if (phaseDescEl) phaseDescEl.textContent = p.phase_description;

  // Update progress ring
  const circumference = 2 * Math.PI * 40;
  const progress = (p.day_of_cycle / p.cycle_length) * circumference;
  const offset = circumference - progress;
  const ring = document.getElementById('dash-progress-ring');
  if (ring) ring.setAttribute('stroke-dashoffset', offset);

  // Update next period
  const nextDateEl = document.getElementById('dash-next-period-date');
  if (nextDateEl) nextDateEl.textContent = p.next_period;
  const daysLeftEl = document.getElementById('dash-days-left');
  if (daysLeftEl) daysLeftEl.textContent = `In ${p.days_until_period} days`;

  // Update fertility
  const ovDateEl = document.getElementById('dash-ovulation-date');
  if (ovDateEl) ovDateEl.textContent = p.ovulation_date;
  const fertileEl = document.getElementById('dash-fertile-window');
  if (fertileEl) fertileEl.textContent = `Fertile Window: ${p.fertile_window}`;

  // Update mood tip
  const tipEl = document.getElementById('dash-mood-tip');
  if (tipEl) tipEl.textContent = p.mood_tip;

  // Load inner circle
  const circleResult = await CycAPI.get(`/inner-circle/${userId}`);
  if (circleResult.status === 'success') {
    const countEl = document.getElementById('dash-circle-count');
    if (countEl) countEl.textContent = `${circleResult.count} Friends connected`;
  }

  // Update user name
  const nameEl = document.getElementById('dash-user-name');
  if (nameEl) nameEl.textContent = CycSession.getName();
}

// ─────────────────────────────────────────────
// ANALYTICS
// ─────────────────────────────────────────────
async function initAnalytics() {
  // Analytics uses pre-built UI with hardcoded demo data per the original screens
  // Data is already visually correct from the original HTML
}

// ─────────────────────────────────────────────
// AI CHAT
// ─────────────────────────────────────────────
let chatInitialized = false;

function initChat() {
  if (chatInitialized) return;
  chatInitialized = true;

  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send-btn');
  const container = document.getElementById('chat-messages');
  const suggestions = document.querySelectorAll('.chat-suggestion');

  if (!input || !sendBtn) return;

  async function sendMessage(text) {
    if (!text.trim()) return;
    input.value = '';

    // Add user message
    const userMsg = createChatBubble(text, 'user');
    container.appendChild(userMsg);

    // Show typing indicator
    const typingEl = createTypingIndicator();
    container.appendChild(typingEl);
    scrollChatToBottom();

    // Call API
    const result = await CycAPI.post('/chat', {
      message: text,
      user_id: CycSession.getUserId()
    });

    // Remove typing indicator
    typingEl.remove();

    // Add bot response
    const botText = result.status === 'success'
      ? result.response
      : "I'm having trouble connecting right now. Please try again! ❤️";
    const botMsg = createChatBubble(botText, 'bot');
    container.appendChild(botMsg);
    scrollChatToBottom();
  }

  sendBtn.addEventListener('click', () => sendMessage(input.value));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendMessage(input.value);
  });

  suggestions.forEach(btn => {
    btn.addEventListener('click', () => sendMessage(btn.textContent));
  });
}

function createChatBubble(text, sender) {
  const wrapper = document.createElement('div');
  wrapper.className = `flex flex-col ${sender === 'user' ? 'items-end w-full' : 'items-start max-w-[85%]'} animate-fade-in`;

  const label = document.createElement('div');
  label.className = `flex items-center gap-2 mb-1 ${sender === 'user' ? 'mr-1 justify-end' : 'ml-1'}`;
  label.innerHTML = `<span class="text-[10px] font-bold uppercase tracking-widest ${sender === 'user' ? 'text-charcoal/40' : 'text-primary/60'}">${sender === 'user' ? 'You' : 'Cycora'}</span>`;

  const bubble = document.createElement('div');
  bubble.className = sender === 'user'
    ? 'max-w-[85%] bg-[#F8D7DA] rounded-2xl rounded-tr-none p-4 shadow-sm'
    : 'bg-white border border-[#C1121F]/30 rounded-2xl rounded-tl-none p-4 shadow-sm';

  // Format markdown-like bold text
  const formatted = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');

  bubble.innerHTML = `<p class="text-[#222222] leading-relaxed text-sm">${formatted}</p>`;

  const msgContainer = sender === 'user' ? document.createElement('div') : wrapper;
  if (sender === 'user') {
    msgContainer.className = 'max-w-[85%]';
    msgContainer.appendChild(label);
    msgContainer.appendChild(bubble);
    wrapper.appendChild(msgContainer);
  } else {
    wrapper.appendChild(label);
    wrapper.appendChild(bubble);
  }

  return wrapper;
}

function createTypingIndicator() {
  const el = document.createElement('div');
  el.className = 'flex flex-col items-start max-w-[85%]';
  el.id = 'typing-indicator';
  el.innerHTML = `
    <div class="flex items-center gap-2 mb-1 ml-1">
      <span class="text-[10px] font-bold uppercase tracking-widest text-primary/60">Cycora</span>
    </div>
    <div class="bg-white border border-[#C1121F]/30 rounded-2xl rounded-tl-none p-4 shadow-sm">
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    </div>
  `;
  return el;
}

function scrollChatToBottom() {
  const container = document.getElementById('chat-messages');
  if (container) {
    setTimeout(() => container.scrollTop = container.scrollHeight, 100);
  }
}

// ─────────────────────────────────────────────
// COMMUNITY
// ─────────────────────────────────────────────
async function initCommunity() {
  const container = document.getElementById('community-posts');
  if (!container) return;

  const result = await CycAPI.get('/community/posts');
  if (result.status !== 'success') return;

  container.innerHTML = '';
  result.posts.forEach(post => {
    container.appendChild(createPostCard(post));
  });
}

function createPostCard(post) {
  const timeAgo = getTimeAgo(post.timestamp);
  const article = document.createElement('article');
  article.className = 'card-hover bg-[#F8D7DA] border border-[#C1121F]/5 rounded-xl p-6 transition-all duration-300 shadow-sm';
  article.innerHTML = `
    <div class="flex items-center justify-between mb-5">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-full bg-white/60 flex items-center justify-center text-[#C1121F]/40">
          <span class="material-symbols-outlined">person</span>
        </div>
        <div>
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold">Anonymous</span>
            <span class="text-[10px] px-2 py-0.5 rounded-full bg-white/60 text-[#C1121F]/70 uppercase tracking-widest font-bold">${post.country}</span>
          </div>
          <span class="text-xs text-slate-500">${timeAgo}</span>
        </div>
      </div>
      <button class="text-slate-400 hover:text-[#C1121F] transition-colors">
        <span class="material-symbols-outlined text-lg">more_horiz</span>
      </button>
    </div>
    <div class="mb-6">
      <p class="text-lg leading-relaxed text-[#222222]">${post.text}</p>
    </div>
    <div class="flex items-center gap-3 pt-4 border-t border-[#C1121F]/10">
      <button onclick="supportPost('${post.id}', this)" class="flex-1 flex items-center justify-center gap-2 py-2.5 text-[#C1121F] font-bold rounded-lg hover:bg-white/40 transition-colors">
        <span class="material-symbols-outlined text-lg" style="font-variation-settings: 'FILL' 1;">favorite</span>
        Send Support <span class="support-count text-xs">(${post.supports})</span>
      </button>
      <button class="flex-1 flex items-center justify-center gap-2 py-2.5 bg-[#F8D7DA] border border-[#C1121F]/5 text-[#222222] font-semibold rounded-lg hover:bg-white/60 transition-colors">
        <span class="material-symbols-outlined text-lg">chat_bubble</span>
        Reply
      </button>
    </div>
  `;
  return article;
}

async function supportPost(postId, btn) {
  const result = await CycAPI.post(`/community/posts/${postId}/support`, {});
  if (result.status === 'success') {
    const countEl = btn.querySelector('.support-count');
    if (countEl) countEl.textContent = `(${result.supports})`;
    showToast('Support sent! ❤️', 'success');
  }
}

async function createPost() {
  const textarea = document.getElementById('new-post-text');
  const text = textarea?.value?.trim();
  if (!text) {
    showToast('Please write something to share', 'error');
    return;
  }

  const result = await CycAPI.post('/community/posts', { text, country: 'LOCAL' });
  if (result.status === 'success') {
    showToast('Post shared with the community! 🌍', 'success');
    closeCreatePostModal();
    initCommunity();
  }
}

function openCreatePostModal() {
  document.getElementById('create-post-modal')?.classList.add('show');
}
function closeCreatePostModal() {
  document.getElementById('create-post-modal')?.classList.remove('show');
  const textarea = document.getElementById('new-post-text');
  if (textarea) textarea.value = '';
}

// ─────────────────────────────────────────────
// INNER CIRCLE (FRIENDS)
// ─────────────────────────────────────────────
function openInviteModal() {
  document.getElementById('invite-modal')?.classList.add('show');
}
function closeInviteModal() {
  document.getElementById('invite-modal')?.classList.remove('show');
}
async function inviteFriend() {
  const email = document.getElementById('invite-email')?.value?.trim();
  const name = document.getElementById('invite-name')?.value?.trim() || 'Friend';
  if (!email) { showToast('Please enter an email', 'error'); return; }

  const result = await CycAPI.post('/inner-circle/invite', {
    user_id: CycSession.getUserId(),
    friend_email: email,
    friend_name: name
  });

  if (result.status === 'success') {
    showToast(result.message, 'success');
    closeInviteModal();
    initDashboard();
  } else {
    showToast(result.message, 'error');
  }
}

// ─────────────────────────────────────────────
// REWARDS
// ─────────────────────────────────────────────
async function initRewards() {
  // Rewards uses pre-built UI with demo data per the original screen
}

// ─────────────────────────────────────────────
// SETTINGS
// ─────────────────────────────────────────────
function initSettings() {
  // Toggle switches
  document.querySelectorAll('.toggle-switch').forEach(toggle => {
    if (toggle.dataset.bound) return;
    toggle.dataset.bound = 'true';
    toggle.addEventListener('click', function () {
      this.classList.toggle('active');
    });
  });

  // Update user info
  const nameInput = document.getElementById('settings-name');
  const emailInput = document.getElementById('settings-email');
  const session = CycSession.get();
  if (session && nameInput) nameInput.value = session.name || '';
  if (session && emailInput) emailInput.value = session.email || '';
}

function handleLogout() {
  CycSession.clear();
  chatInitialized = false;
  showToast('Logged out successfully', 'success');
  CycRouter.navigate('splash');
}

// ─────────────────────────────────────────────
// UTILITIES
// ─────────────────────────────────────────────
function getTimeAgo(timestamp) {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now - then;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minutes ago`;
  if (diffHours < 24) return `${diffHours} hours ago`;
  return `${diffDays} days ago`;
}

// ─────────────────────────────────────────────
// INITIALIZATION
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initLogin();
  initRegister();

  // Password visibility toggle
  const toggleBtn = document.getElementById('togglePassword');
  const passwordInput = document.getElementById('reg-password');
  if (toggleBtn && passwordInput) {
    toggleBtn.addEventListener('click', () => {
      const type = passwordInput.type === 'password' ? 'text' : 'password';
      passwordInput.type = type;
      toggleBtn.classList.toggle('text-[#C1121F]');
    });
  }

  // Initialize router
  CycRouter.init();
});

// Make functions available globally
window.supportPost = supportPost;
window.createPost = createPost;
window.openCreatePostModal = openCreatePostModal;
window.closeCreatePostModal = closeCreatePostModal;
window.openInviteModal = openInviteModal;
window.closeInviteModal = closeInviteModal;
window.inviteFriend = inviteFriend;
window.handleLogout = handleLogout;
window.initSetup = initSetup;
