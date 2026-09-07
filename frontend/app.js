/* =============================================================
   BrandCraft Premium Glassmorphic Frontend Controller

   Connects to SQLite-backed FastAPI keyless backend.
   ============================================================= */

// State

const API_BASE_URL = "http://127.0.0.1:8000";

let currentUser = null;

let activities = JSON.parse(localStorage.getItem('bc_activities')) || [];


// Initialize application on load

document.addEventListener('DOMContentLoaded', () => {

  // Load and apply theme

  const savedTheme = localStorage.getItem('bc_theme') || 'light';

  if (savedTheme === 'dark') {

    document.documentElement.classList.add('dark');

    const themeBtn = document.querySelector('.theme-btn');

    if (themeBtn) themeBtn.textContent = '☀️';

  } else {

    document.documentElement.classList.remove('dark');

    const themeBtn = document.querySelector('.theme-btn');

    if (themeBtn) themeBtn.textContent = '🌙';

  }


  // Restore session

  const token = localStorage.getItem('bc_token');

  const user = localStorage.getItem('bc_user');

  if (token && user) {

    currentUser = JSON.parse(user);

    showApp();

  } else {

    handleLogout();

  }


  // Sync color picker with text input

  const colorPicker = document.getElementById('logo-color-picker');

  const colorInput = document.getElementById('logo-colors');

  if (colorPicker && colorInput) {

    colorInput.value = colorPicker.value;

    colorPicker.addEventListener('input', (e) => {

      colorInput.value = e.target.value;

    });

  }

});


// ─── API HELPER REQUEST ENGINE ───────────────────────────────

async function apiRequest(endpoint, method = 'GET', body = null) {

  const token = localStorage.getItem('bc_token');

  const headers = {};

  if (token) {

    headers['Authorization'] = `Bearer ${token}`;

  }

  if (body) {

    headers['Content-Type'] = 'application/json';

  }

  const options = {

    method,

    headers,

  };

  if (body) {

    options.body = JSON.stringify(body);

  }

  try {

    const res = await fetch(`${API_BASE_URL}${endpoint}`, options);

    if (res.status === 401) {

      handleLogout();

      toast('Session expired. Please sign in again.', 'error');

      throw new Error('Unauthorized');

    }

    const data = await res.json();

    if (!res.ok) {

      throw new Error(data.detail || 'API request failed');

    }

    return data;

  } catch (err) {

    console.error(`API Error on ${endpoint}:`, err);

    throw err;

  }

}


// ─── UTILITIES & TOASTS ──────────────────────────────────────

function toast(msg, type = 'info') {

  const c = document.getElementById('toast-container');

  if (!c) return;

  const t = document.createElement('div');

  t.className = `toast toast-${type}`;

  const icons = {

    success: '✓',

    error: '✕',

    info: 'ℹ'

  };

  t.innerHTML = `<span style="font-size:16px; margin-right:8px;">${icons[type] || 'ℹ'}</span>${msg}`;

  c.appendChild(t);

  setTimeout(() => t.remove(), 3500);

}


function copyText(text) {

  navigator.clipboard.writeText(text).catch(() => {});

  toast('Copied to clipboard!', 'success');

}


// ─── THEME & LAYOUT ──────────────────────────────────────────

function toggleTheme() {

  const isDark = document.documentElement.classList.toggle('dark');

  localStorage.setItem('bc_theme', isDark ? 'dark' : 'light');

  const btn = document.querySelector('.theme-btn');

  if (btn) btn.textContent = isDark ? '☀️' : '🌙';

}


function toggleSidebar() {

  const sidebar = document.getElementById('sidebar');

  if (sidebar) sidebar.classList.toggle('open');

}


// ─── AUTHENTICATION ──────────────────────────────────────────

function switchAuthTab(tab) {

  document.querySelectorAll('.auth-tab').forEach((t, i) => {

    t.classList.toggle(
      'active',
      (i === 0 && tab === 'login') ||
      (i === 1 && tab === 'signup')
    );

  });

  const loginForm = document.getElementById('form-login');

  const signupForm = document.getElementById('form-signup');

  if (loginForm) loginForm.classList.toggle('active', tab === 'login');

  if (signupForm) signupForm.classList.toggle('active', tab === 'signup');

}


async function handleLogin() {

  const email = document.getElementById('login-email').value.trim();

  const pass = document.getElementById('login-password').value;

  const rememberRow = document.getElementById('remember');

  const remember = rememberRow ? rememberRow.checked : false;


  if (!email || !pass) {

    toast('Please fill in all fields.', 'error');

    return;

  }


  if (!email.includes('@')) {

    toast('Enter a valid email address.', 'error');

    return;

  }


  try {

    const res = await fetch(`${API_BASE_URL}/api/auth/login`, {

      method: 'POST',

      headers: {

        'Content-Type': 'application/json'

      },

      body: JSON.stringify({

        email,

        password: pass,

        remember_me: remember

      })

    });


    const data = await res.json();


    if (!res.ok) {

      throw new Error(data.detail || 'Login failed');

    }


    localStorage.setItem('bc_token', data.access_token);

    localStorage.setItem('bc_user', JSON.stringify(data.user));

    currentUser = data.user;


    toast('Welcome back! 🎉', 'success');

    showApp();


  } catch (err) {

    toast(err.message, 'error');

  }

}


async function handleSignup() {

  const name = document.getElementById('signup-name').value.trim();

  const email = document.getElementById('signup-email').value.trim();

  const pass = document.getElementById('signup-password').value;

  const confirm = document.getElementById('signup-confirm').value;


  if (!name || !email || !pass || !confirm) {

    toast('Please fill in all fields.', 'error');

    return;

  }


  if (!email.includes('@')) {

    toast('Enter a valid email address.', 'error');

    return;

  }


  if (pass.length < 8) {

    toast('Password must be at least 8 characters.', 'error');

    return;

  }


  if (pass !== confirm) {

    toast('Passwords do not match.', 'error');

    return;

  }


  try {

    const res = await fetch(`${API_BASE_URL}/api/auth/register`, {

      method: 'POST',

      headers: {

        'Content-Type': 'application/json'

      },

      body: JSON.stringify({

        name,

        email,

        password: pass,

        confirm_password: confirm

      })

    });


    const data = await res.json();


    if (!res.ok) {

      throw new Error(data.detail || 'Registration failed');

    }


    toast(
      'Account created successfully! Auto-logging in... 🌸',
      'success'
    );


    const loginRes = await fetch(`${API_BASE_URL}/api/auth/login`, {

      method: 'POST',

      headers: {

        'Content-Type': 'application/json'

      },

      body: JSON.stringify({

        email,

        password: pass,

        remember_me: true

      })

    });


    const loginData = await loginRes.json();


    if (loginRes.ok) {

      localStorage.setItem(
        'bc_token',
        loginData.access_token
      );

      localStorage.setItem(
        'bc_user',
        JSON.stringify(loginData.user)
      );

      currentUser = loginData.user;

      showApp();

    } else {

      switchAuthTab('login');

    }

  } catch (err) {

    toast(err.message, 'error');

  }

}


function showForgot() {

  toast(
    'Email verification resets are simulated. Try registering a new email or check server console for logs.',
    'info'
  );

}


function handleLogout() {

  localStorage.removeItem('bc_token');

  localStorage.removeItem('bc_user');

  currentUser = null;


  const appEl = document.getElementById('app');

  const authEl = document.getElementById('auth-screen');


  if (appEl) appEl.style.display = 'none';

  if (authEl) authEl.style.display = 'flex';

}


function showApp() {

  const appEl = document.getElementById('app');

  const authEl = document.getElementById('auth-screen');


  if (appEl) appEl.style.display = 'block';

  if (authEl) authEl.style.display = 'none';


  if (currentUser && currentUser.name) {

    const initials = currentUser.name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);


    const avatar = document.getElementById('user-avatar');

    if (avatar) avatar.textContent = initials;

  }


  showPage('dashboard');

  updateStats();

  updateActivity();

}


// ─── SPA ROUTING ─────────────────────────────────────────────

const pageTitles = {

  dashboard: 'Dashboard',

  names: 'Brand Name Generator',

  logos: 'Logo Generator',

  content: 'Content Studio',

  sentiment: 'Sentiment Radar',

  assistant: 'AI Assistant'

};


function showPage(name) {

  document.querySelectorAll('.page')
    .forEach(p => p.classList.remove('active'));


  document.querySelectorAll('.nav-item')
    .forEach(n => n.classList.remove('active'));


  const targetPage = document.getElementById('page-' + name);


  if (targetPage) {

    targetPage.classList.add('active');

  }


  document.querySelectorAll('.nav-item').forEach(n => {

    if (
      n.textContent
        .trim()
        .toLowerCase()
        .includes(
          name.replace('-', ' ').split(' ')[0]
        )
    ) {

      n.classList.add('active');

    }

  });


  const titleEl = document.getElementById('page-title');

  if (titleEl) {

    titleEl.textContent = pageTitles[name] || name;

  }


  if (window.innerWidth < 768) {

    const sidebar = document.getElementById('sidebar');

    if (sidebar) sidebar.classList.remove('open');

  }


  // Page hydration on entry

  if (name === 'logos') {

    loadLogoGallery();

  } else if (name === 'names') {

    loadSavedBrands();

  } else if (name === 'assistant') {

    loadChatHistory();

  } else if (name === 'dashboard') {

    updateStats();

  }

}


// ─── DASHBOARD STATS & RECENT ACTIVITY ───────────────────────

async function updateStats() {

  try {

    const savedBrands =
      await apiRequest('/api/generator/saved');


    const galleryLogos =
      await apiRequest('/api/logo/gallery');


    const savedContent =
      await apiRequest('/api/content/saved');


    const chatHistory =
      await apiRequest('/api/assistant/history');


    const namesCount = savedBrands.length;

    const logosCount = galleryLogos.length;


    let contentCount = 0;


    savedContent.forEach(c => {

      const data = c.content_data || {};


      contentCount += (data.slogans || []).length;

      contentCount += (data.brand_stories || []).length;

      contentCount += (data.product_descriptions || []).length;

      contentCount += (data.social_media_captions || []).length;

      contentCount += (data.advertisement_copies || []).length;

      contentCount += (data.email_marketing_templates || []).length;

    });


    const chatsCount = chatHistory.length;


    const sn = document.getElementById('stat-names');

    if (sn) sn.textContent = namesCount;


    const pbn = document.getElementById('pb-names');

    if (pbn) {

      pbn.style.width =
        Math.min(namesCount * 5, 100) + '%';

    }


    const sl = document.getElementById('stat-logos');

    if (sl) sl.textContent = logosCount;


    const pbl = document.getElementById('pb-logos');

    if (pbl) {

      pbl.style.width =
        Math.min(logosCount * 5, 100) + '%';

    }


    const sc = document.getElementById('stat-content');

    if (sc) sc.textContent = contentCount;


    const pbc = document.getElementById('pb-content');

    if (pbc) {

      pbc.style.width =
        Math.min(contentCount * 2, 100) + '%';

    }


    const sch = document.getElementById('stat-chats');

    if (sch) sch.textContent = chatsCount;


    const pbch = document.getElementById('pb-chats');

    if (pbch) {

      pbch.style.width =
        Math.min(chatsCount * 5, 100) + '%';

    }

  } catch (err) {

    console.error(
      'Failed to sync metrics from DB:',
      err
    );

  }

}


function addActivity(msg) {

  activities.unshift({

    msg,

    time: new Date().toLocaleTimeString()

  });


  if (activities.length > 8) {

    activities.pop();

  }


  localStorage.setItem(
    'bc_activities',
    JSON.stringify(activities)
  );


  updateActivity();

}


function updateActivity() {

  const el =
    document.getElementById('recent-activity');


  if (!el) return;


  if (!activities.length) {

    el.innerHTML = `
      <div style="font-size:14px; color:var(--text-light);">
        No activity yet. Start generating!
      </div>
    `;

    return;

  }


  el.innerHTML = activities.map(a => `

    <div style="
      padding:8px 0;
      border-bottom:1px solid var(--card-border);
      font-size:13px;
    ">

      <span style="color:var(--text-dark);">
        ${a.msg}
      </span>

      <span style="
        float:right;
        color:var(--text-light);
        font-size:11px;
      ">
        ${a.time}
      </span>

    </div>

  `).join('');

}


// ─── BRAND NAMES GENERATOR ────────────────────────────────────

async function generateNames() {

  const bizType =
    document.getElementById('biz-type').value.trim();

  const industry =
    document.getElementById('biz-industry').value.trim();

  const audience =
    document.getElementById('biz-audience').value.trim();

  const personality =
    document.getElementById('biz-personality').value.trim();

  const lang =
    document.getElementById('biz-language').value;

  const country =
    document.getElementById('biz-country').value.trim();


  // Validate all 6 user-selected fields are filled in

  const missingFields = [];


  if (!bizType) missingFields.push("Business Type");

  if (!industry) missingFields.push("Industry");

  if (!audience) missingFields.push("Target Audience");

  if (!personality) missingFields.push("Brand Personality");

  if (!lang) missingFields.push("Language");

  if (!country) missingFields.push("Country/Region");


  if (missingFields.length > 0) {

    toast(
      `Please fill in all required fields: ${missingFields.join(", ")}.`,
      'error'
    );

    return;

  }


  const btn =
    document.getElementById('btn-gen-names');


  if (btn) {

    btn.disabled = true;

    btn.innerHTML =
      '<div class="spinner"></div> Generating…';

  }


  const resultsEl =
    document.getElementById('names-results');


  if (resultsEl) {

    resultsEl.innerHTML = `
      <div class="loading-overlay">

        <div
          class="spinner"
          style="
            width:32px;
            height:32px;
            border-color:rgba(201,117,138,0.3);
            border-top-color:var(--rose);
          "
        ></div>

        <div class="loading-text">
          Crafting 30–50 unique brand names…
        </div>

      </div>
    `;

  }


  try {

    const data =
      await apiRequest(
        '/api/generator/names',
        'POST',
        {
          business_type: bizType,
          industry: industry,
          target_audience: audience || 'General',
          brand_personality: personality || 'Modern',
          preferred_language: lang,
          country: country || 'Global'
        }
      );


    // Ensure unique brand names

    const rawBrands = data.brands || [];

    const uniqueMap = new Map();


    rawBrands.forEach(b => {

      if (!uniqueMap.has(b.name)) {

        uniqueMap.set(b.name, b);

      }

    });


    const brands =
      Array.from(uniqueMap.values());


    let resultsHtml = `

      <div class="panel">

        <div class="panel-title">
          ✨ ${brands.length} Brand Names Generated (${lang})
        </div>

        <div class="results-grid">

    `;


    brands.forEach(n => {

      const nameEscaped =
        n.name.replace(/'/g, "\\'");

      const meaningEscaped =
        (n.meaning || '').replace(/'/g, "\\'");

      const taglineEscaped =
        (n.tagline || '').replace(/'/g, "\\'");

      const domainsJSON =
        JSON.stringify(n.domains || []);


      const primaryDomain =
        n.domains && n.domains.length > 0
          ? n.domains[0]
          : (n.name.toLowerCase() + '.com');


      resultsHtml += `

        <div
          class="result-card"
          style="
            position:relative;
            display:flex;
            flex-direction:column;
            justify-content:space-between;
          "
        >

          <div>

            <div
              style="
                display:flex;
                justify-content:space-between;
                align-items:center;
                margin-bottom:4px;
              "
            >

              <div
                class="result-name"
                onclick="copyText('${nameEscaped}')"
                style="
                  cursor:pointer;
                  flex:1;
                "
              >
                ${n.name}
              </div>

              <button
                onclick="event.stopPropagation(); saveBrandToServer(
                  '${nameEscaped}',
                  '${meaningEscaped}',
                  '${taglineEscaped}',
                  '${domainsJSON.replace(/"/g, '&quot;')}'
                )"
                style="
                  background:none;
                  border:none;
                  color:var(--rose);
                  cursor:pointer;
                  font-size:16px;
                "
                title="Save Brand"
              >
                ⭐
              </button>

            </div>

            <div
              class="result-meta"
              onclick="copyText('${nameEscaped}')"
              style="cursor:pointer;"
            >
              ${primaryDomain}
            </div>

            <div
              style="
                font-size:13px;
                color:var(--text-mid);
                margin-bottom:8px;
                line-height:1.5;
                font-style:italic;
              "
              onclick="copyText('${nameEscaped}')"
            >
              "${n.tagline || ''}"
            </div>

            <div
              style="
                font-size:12px;
                color:var(--text-light);
                margin-bottom:6px;
                line-height:1.4;
              "
              onclick="copyText('${nameEscaped}')"
            >
              ${n.meaning || ''}
            </div>

          </div>

          <div style="margin-top:8px;">

            <span class="badge badge-rose">
              Creative
            </span>

          </div>

        </div>

      `;

    });


    resultsHtml += `

        </div>

        <p
          style="
            font-size:12px;
            color:var(--text-light);
            margin-top:14px;
          "
        >
          💡 Click any brand name to copy it.
          Click ⭐ to save to account.
        </p>

      </div>

    `;


    if (resultsEl) {

      resultsEl.innerHTML = resultsHtml;

    }


    addActivity(
      `Generated ${brands.length} brand names for ${industry}`
    );


    toast(
      `${brands.length} brand names ready! 🎉`,
      'success'
    );


    loadSavedBrands();


  } catch (err) {

    if (resultsEl) {

      resultsEl.innerHTML = '';

    }


    toast(
      err.message || 'Failed to generate names.',
      'error'
    );


  } finally {

    if (btn) {

      btn.disabled = false;

      btn.innerHTML = `
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M12 2L2 7l10 5 10-5-10-5z"/>
        </svg>
        Generate Brand Names
      `;

    }

  }

}


async function saveBrandToServer(
  name,
  meaning,
  tagline,
  domainsString
) {

  let domains = [];


  try {

    domains = JSON.parse(domainsString);

  } catch (e) {

    domains = [
      name.toLowerCase() + '.com'
    ];

  }


  try {

    const bizType =
      document.getElementById('biz-type')
        .value.trim() || 'Startup';


    const audience =
      document.getElementById('biz-audience')
        .value.trim() || 'General';


    const industry =
      document.getElementById('biz-industry')
        .value.trim() || 'Technology';


    await apiRequest(
      '/api/generator/save',
      'POST',
      {
        brand_name: name,
        industry: industry,
        target_audience: audience,
        brand_meaning: meaning,
        tagline: tagline,
        domain_suggestions: domains
      }
    );


    toast(
      `Saved brand "${name}" to your library! ⭐`,
      'success'
    );


    addActivity(
      `Saved brand "${name}"`
    );


    loadSavedBrands();

    updateStats();


  } catch (err) {

    toast(
      err.message || 'Could not save brand.',
      'error'
    );

  }

}


async function loadSavedBrands() {

  try {

    const saved =
      await apiRequest('/api/generator/saved');


    let savedContainer =
      document.getElementById('saved-brands-list');


    if (!savedContainer) {

      const pageNames =
        document.getElementById('page-names');


      if (pageNames) {

        const div =
          document.createElement('div');


        div.id =
          'saved-brands-list';


        div.className =
          'panel';


        div.style.marginTop =
          '20px';


        pageNames.appendChild(div);


        savedContainer = div;

      }

    }


    if (savedContainer) {

      if (saved.length === 0) {

        savedContainer.innerHTML = `

          <div class="panel-title">
            ⭐ Saved Brand Portfolio
          </div>

          <p
            style="
              font-size:13px;
              color:var(--text-light);
            "
          >
            No saved brands yet.
            Click ⭐ on generated names to save them here.
          </p>

        `;

      } else {

        let savedHtml = `

          <div class="panel-title">
            ⭐ Saved Brand Portfolio (${saved.length})
          </div>

          <div class="results-grid">

        `;


        saved.forEach(b => {

          const nameEscaped =
            b.brand_name.replace(/'/g, "\\'");


          const primaryDomain =
            b.domain_suggestions &&
            b.domain_suggestions.length > 0
              ? b.domain_suggestions[0]
              : (b.brand_name.toLowerCase() + '.com');


          savedHtml += `

            <div
              class="result-card"
              style="
                display:flex;
                flex-direction:column;
                justify-content:space-between;
                border-color:rgba(201,117,138,0.35);
              "
            >

              <div>

                <div
                  style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    margin-bottom:4px;
                  "
                >

                  <div
                    class="result-name"
                    onclick="copyText('${nameEscaped}')"
                    style="cursor:pointer;"
                  >
                    ${b.brand_name}
                  </div>

                  <button
                    onclick="deleteSavedBrandFromServer(${b.id})"
                    style="
                      background:none;
                      border:none;
                      color:red;
                      cursor:pointer;
                      font-size:13px;
                    "
                    title="Delete Saved Brand"
                  >
                    🗑️
                  </button>

                </div>

                <div
                  class="result-meta"
                  onclick="copyText('${nameEscaped}')"
                  style="cursor:pointer;"
                >
                  ${primaryDomain}
                </div>

                <div
                  style="
                    font-size:13px;
                    color:var(--text-mid);
                    margin-bottom:8px;
                    line-height:1.5;
                    font-style:italic;
                  "
                  onclick="copyText('${nameEscaped}')"
                >
                  "${b.tagline || ''}"
                </div>

                <div
                  style="
                    font-size:12px;
                    color:var(--text-light);
                    margin-bottom:6px;
                    line-height:1.4;
                  "
                  onclick="copyText('${nameEscaped}')"
                >
                  ${b.brand_meaning || ''}
                </div>

              </div>

              <div
                style="
                  margin-top:8px;
                  font-size:11px;
                  color:var(--text-light);
                "
              >
                Saved on
                ${new Date(b.created_at).toLocaleDateString()}
              </div>

            </div>

          `;

        });


        savedHtml += `

          </div>

        `;


        savedContainer.innerHTML =
          savedHtml;

      }

    }

  } catch (err) {

    console.error(
      'Failed to load saved brands:',
      err
    );

  }

}


async function deleteSavedBrandFromServer(id) {

  if (
    !confirm(
      'Are you sure you want to delete this brand from your saved library?'
    )
  ) return;


  try {

    await apiRequest(
      `/api/generator/saved/${id}`,
      'DELETE'
    );


    toast(
      'Brand removed from saved library.',
      'info'
    );


    loadSavedBrands();

    updateStats();


  } catch (err) {

    toast(
      err.message || 'Could not delete saved brand.',
      'error'
    );

  }

}


// ─── LOGO GENERATOR ───────────────────────────────────────────

async function generateLogos() {

  const brand =
    document.getElementById('logo-brand')
      .value.trim();


  const industry =
    document.getElementById('logo-industry')
      .value.trim();


  const style =
    document.getElementById('logo-style')
      .value;


  const colors =
    document.getElementById('logo-colors')
      .value.trim();


  if (!brand) {

    toast(
      'Please enter a brand name.',
      'error'
    );

    return;

  }


  const btn =
    document.getElementById('btn-gen-logos');


  if (btn) {

    btn.disabled = true;

    btn.innerHTML =
      '<div class="spinner"></div> Creating…';

  }


  const resultsEl =
    document.getElementById('logos-results');


  if (resultsEl) {

    resultsEl.innerHTML = `

      <div class="loading-overlay">

        <div
          class="spinner"
          style="
            width:32px;
            height:32px;
            border-color:rgba(201,117,138,0.3);
            border-top-color:var(--rose);
          "
        ></div>

        <div class="loading-text">
          Generating logo concepts...
        </div>

      </div>

    `;

  }


  try {

    // Request at least 30 unique logo designs

    const logoCount = 30;


    const colorPickerVal =
      document.getElementById(
        'logo-color-picker'
      )?.value || '#C9758A';


    const colorsParam =
      colors || colorPickerVal;


    const logos =
      await apiRequest(
        `/api/logo/generate?count=${logoCount}`,
        'POST',
        {
          brand_name: brand,
          industry: industry || 'General',
          style: style,
          colors: colorsParam,
          logo_type: 'emblem'
        }
      );


    let resultsHtml = `

      <div class="panel">

        <div class="panel-title">
          🎨 ${logos.length} Generated Logo Concepts
        </div>

        <div class="logo-grid">

    `;


    logos.forEach(c => {

      resultsHtml += `

        <div
          class="logo-card"
          id="logo-card-${c.id}"
        >

          <div
            class="logo-preview"
            style="
              height:160px;
              overflow:hidden;
              background:#fff;
            "
          >

            <img
              src="/${c.file_path}"
              style="
                width:100%;
                height:100%;
                object-fit:cover;
              "
              alt="Generated Logo"
              onclick="window.open('/${c.file_path}', '_blank')"
            >

          </div>

          <div class="logo-card-meta">

            <div
              style="
                font-weight:600;
                font-size:13px;
                color:var(--text-dark);
                margin-bottom:6px;
              "
            >
              ${c.brand_name}
            </div>

            <div
              style="
                font-size:11px;
                color:var(--text-light);
                margin-bottom:8px;
              "
            >
              Style: ${c.style} |
              Colors: ${c.colors}
            </div>

            <div
              style="
                display:flex;
                gap:6px;
                flex-wrap:wrap;
                margin-bottom:8px;
              "
            >

              <a
                href="/api/logo/download/${c.id}/png"
                download
                class="badge badge-rose"
                style="text-decoration:none;"
              >
                PNG
              </a>

              <a
                href="/api/logo/download/${c.id}/jpg"
                download
                class="badge badge-green"
                style="text-decoration:none;"
              >
                JPG
              </a>

              <a
                href="/api/logo/download/${c.id}/pdf"
                download
                class="badge badge-amber"
                style="text-decoration:none;"
              >
                PDF Sheet
              </a>

            </div>

            <div style="text-align:right;">

              <button
                onclick="deleteLogoFromServer(${c.id})"
                style="
                  background:none;
                  border:none;
                  font-size:11px;
                  color:red;
                  cursor:pointer;
                  padding:0;
                "
              >
                Delete 🗑️
              </button>

            </div>

          </div>

        </div>

      `;

    });


    resultsHtml += `

        </div>

      </div>

    `;


    if (resultsEl) {

      resultsEl.innerHTML =
        resultsHtml;

    }


    addActivity(
      `Generated logo concepts for ${brand}`
    );


    toast(
      `${logos.length} logo concepts ready! 🎨`,
      'success'
    );


    loadLogoGallery();

    updateStats();


  } catch (err) {

    if (resultsEl) {

      resultsEl.innerHTML = '';

    }


    toast(
      err.message || 'Failed to generate logos.',
      'error'
    );


  } finally {

    if (btn) {

      btn.disabled = false;

      btn.innerHTML = `

        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >

          <rect
            x="3"
            y="3"
            width="18"
            height="18"
            rx="2"
          />

          <circle
            cx="8.5"
            cy="8.5"
            r="1.5"
          />

          <polyline
            points="21 15 16 10 5 21"
          />

        </svg>

        Generate Logo Concepts

      `;

    }

  }

}


async function loadLogoGallery() {

  try {

    const gallery =
      await apiRequest('/api/logo/gallery');


    let galleryContainer =
      document.getElementById(
        'logo-gallery-list'
      );


    if (!galleryContainer) {

      const pageLogos =
        document.getElementById(
          'page-logos'
        );


      if (pageLogos) {

        const div =
          document.createElement('div');


        div.id =
          'logo-gallery-list';


        div.className =
          'panel';


        div.style.marginTop =
          '20px';


        pageLogos.appendChild(div);


        galleryContainer = div;

      }

    }


    if (galleryContainer) {

      if (gallery.length === 0) {

        galleryContainer.innerHTML = `

          <div class="panel-title">
            🖼️ Logo Design Gallery
          </div>

          <p
            style="
              font-size:13px;
              color:var(--text-light);
            "
          >
            No logos saved in your gallery.
            Generate logos to build your design library.
          </p>

        `;

      } else {

        let galleryHtml = `

          <div class="panel-title">
            🖼️ Logo Design Gallery (${gallery.length})
          </div>

          <div class="logo-grid">

        `;


        gallery.forEach(c => {

          galleryHtml += `

            <div
              class="logo-card"
              id="logo-gallery-card-${c.id}"
            >

              <div
                class="logo-preview"
                style="
                  height:140px;
                  overflow:hidden;
                  background:#fff;
                "
              >

                <img
                  src="/${c.file_path}"
                  style="
                    width:100%;
                    height:100%;
                    object-fit:cover;
                  "
                  alt="Gallery Logo"
                  onclick="window.open('/${c.file_path}', '_blank')"
                >

              </div>

              <div class="logo-card-meta">

                <div
                  style="
                    font-weight:600;
                    font-size:13px;
                    color:var(--text-dark);
                    margin-bottom:4px;
                  "
                >
                  ${c.brand_name}
                </div>

                <div
                  style="
                    font-size:11px;
                    color:var(--text-light);
                    margin-bottom:8px;
                  "
                >
                  Style: ${c.style}
                </div>

                <div
                  style="
                    display:flex;
                    gap:6px;
                    flex-wrap:wrap;
                    margin-bottom:8px;
                  "
                >

                  <a
                    href="/api/logo/download/${c.id}/png"
                    download
                    class="badge badge-rose"
                    style="
                      text-decoration:none;
                      font-size:10px;
                    "
                  >
                    PNG
                  </a>

                  <a
                    href="/api/logo/download/${c.id}/jpg"
                    download
                    class="badge badge-green"
                    style="
                      text-decoration:none;
                      font-size:10px;
                    "
                  >
                    JPG
                  </a>

                  <a
                    href="/api/logo/download/${c.id}/pdf"
                    download
                    class="badge badge-amber"
                    style="
                      text-decoration:none;
                      font-size:10px;
                    "
                  >
                    PDF
                  </a>

                </div>

                <div style="text-align:right;">

                  <button
                    onclick="deleteLogoFromServer(${c.id})"
                    style="
                      background:none;
                      border:none;
                      font-size:11px;
                      color:red;
                      cursor:pointer;
                      padding:0;
                    "
                  >
                    Delete 🗑️
                  </button>

                </div>

              </div>

            </div>

          `;

        });


        galleryHtml += `

          </div>

        `;


        galleryContainer.innerHTML =
          galleryHtml;

      }

    }

  } catch (err) {

    console.error(
      'Failed to load logo gallery:',
      err
    );

  }

}


async function deleteLogoFromServer(id) {

  if (
    !confirm(
      'Are you sure you want to delete this logo concept from your database?'
    )
  ) return;


  try {

    await apiRequest(
      `/api/logo/delete/${id}`,
      'DELETE'
    );


    toast(
      'Logo successfully deleted from server and database.',
      'info'
    );


    const card1 =
      document.getElementById(
        `logo-card-${id}`
      );


    if (card1) card1.remove();


    const card2 =
      document.getElementById(
        `logo-gallery-card-${id}`
      );


    if (card2) card2.remove();


    loadLogoGallery();

    updateStats();


  } catch (err) {

    toast(
      err.message || 'Could not delete logo.',
      'error'
    );

  }

}


// ─── CONTENT STUDIO ────────────────────────────────────────────

async function generateContent(type) {

  const brand =
    document.getElementById('cont-brand')
      .value.trim();


  const industry =
    document.getElementById('cont-industry')
      .value.trim();


  const tone =
    document.getElementById('cont-tone')
      .value;


  if (!brand || !industry) {

    toast(
      'Please enter Brand Name and Industry.',
      'error'
    );

    return;

  }


  /*
    IMPORTANT:
    Do NOT put the number inside the label.

    Previously:
      slogans: { label: '5 Slogans', ... }

    Then the UI added:
      ${items.length} ${t.label}

    Result:
      5 5 Slogans

    Now only the actual generated item count is displayed.
  */

  const typeMap = {

    slogans: {
      count: 5,
      key: 'slogans',
      title: 'Slogan'
    },

    stories: {
      count: 1,
      key: 'brand_stories',
      title: 'Brand Story'
    },

    social: {
      count: 2,
      key: 'social_media_captions',
      title: 'Social Caption'
    },

    ads: {
      count: 1,
      key: 'advertisement_copies',
      title: 'Ad Copy'
    },

    emails: {
      count: 1,
      key: 'email_marketing_templates',
      title: 'Email Template'
    }

  };


  const t = typeMap[type];

  if (!t) return;


  const buttons = [
    'slogans',
    'stories',
    'social',
    'ads',
    'emails'
  ];


  buttons.forEach(b => {

    const el =
      document.getElementById(
        'btn-' + b
      );


    if (el) {

      el.disabled = true;


      if (b === type) {

        el.className =
          'btn btn-rose';


        el.innerHTML =
          '<div class="spinner"></div> Generating…';

      } else {

        el.className =
          'btn btn-outline';

      }

    }

  });


  const resultsEl =
    document.getElementById(
      'content-results'
    );


  if (resultsEl) {

    resultsEl.innerHTML = `

      <div class="loading-overlay">

        <div
          class="spinner"
          style="
            width:32px;
            height:32px;
            border-color:rgba(201,117,138,0.3);
            border-top-color:var(--rose);
          "
        ></div>

        <div class="loading-text">
          Writing ${t.count}
          ${t.title}${t.count > 1 ? 's' : ''}
          for ${brand}...
        </div>

      </div>

    `;

  }


  try {

    const data =
      await apiRequest(
        '/api/content/generate',
        'POST',
        {
          brand_name: brand,
          industry: industry,
          tone: tone
        }
      );


    const contentPack =
      data.content_data || {};


    const items =
      contentPack[t.key] || [];


    /*
      Correct heading.

      For 5 slogans:
        ✍️ 5 Slogans for Brand

      For 1 story:
        ✍️ 1 Brand Story for Brand

      For 2 captions:
        ✍️ 2 Social Captions for Brand
    */

    const headingLabel =
      t.title + (items.length === 1 ? '' : 's');


    let resultsHtml = `

      <div class="panel">

        <div class="panel-title">
          ✍️ ${items.length} ${headingLabel} for ${brand}
        </div>

    `;


    items.forEach((item, i) => {

      const isEmail =
        typeof item === 'object' &&
        item !== null;


      const titleText =
        isEmail
          ? (
              item.subject ||
              `Template #${i + 1}`
            )
          : item;


      const bodyText =
        isEmail
          ? item.body
          : item;


      const copyPayload =
        String(bodyText)
          .replace(/'/g, "\\'")
          .replace(/\n/g, '\\n');


      resultsHtml += `

        <div class="content-block">

          <div class="content-block-title">
            ${t.title} #${i + 1}
          </div>

          <div
            style="
              font-weight:600;
              font-size:14px;
              color:var(--text-dark);
              margin-bottom:6px;
            "
          >
            ${titleText}
          </div>

          <div
            class="content-block-body"
            style="white-space:pre-line;"
          >
            ${bodyText}
          </div>

          <button
            onclick="copyText('${copyPayload}'); toast('Copied text to clipboard!', 'success');"
            style="
              margin-top:8px;
              background:none;
              border:none;
              font-size:12px;
              color:var(--rose);
              cursor:pointer;
              padding:0;
              font-family:Inter,sans-serif;
            "
          >
            Copy ↗
          </button>

        </div>

      `;

    });


    resultsHtml += `

      </div>

    `;


    if (resultsEl) {

      resultsEl.innerHTML =
        resultsHtml;

    }


    addActivity(
      `Generated ${items.length} ${headingLabel} for ${brand}`
    );


    toast(
      `${items.length} pieces ready! ✍️`,
      'success'
    );


    updateStats();


  } catch (err) {

    if (resultsEl) {

      resultsEl.innerHTML = '';

    }


    toast(
      err.message || 'Failed to generate content.',
      'error'
    );


  } finally {

    buttons.forEach(b => {

      const el =
        document.getElementById(
          'btn-' + b
        );


      if (el) {

        el.disabled = false;


        if (b === 'slogans') {

          el.className =
            'btn btn-rose';


          el.innerHTML =
            '✨ Slogans';

        } else {

          el.className =
            'btn btn-outline';


          const labels = {

            stories: '📖 Brand Stories',

            social: '📱 Social Captions',

            ads: '📢 Ad Copies',

            emails: '📧 Email Templates'

          };


          el.innerHTML =
            labels[b];

        }

      }

    });

  }

}


// ─── SENTIMENT RADAR ──────────────────────────────────────────

async function analyzeSentiment() {

  const text =
    document.getElementById(
      'sentiment-input'
    ).value.trim();


  if (!text) {

    toast(
      'Please paste some customer reviews.',
      'error'
    );

    return;

  }


  const btn =
    document.getElementById(
      'btn-sentiment'
    );


  if (btn) {

    btn.disabled = true;

    btn.innerHTML =
      '<div class="spinner"></div> Analyzing…';

  }


  const resultsEl =
    document.getElementById(
      'sentiment-results'
    );


  if (resultsEl) {

    resultsEl.innerHTML = `

      <div class="loading-overlay">

        <div
          class="spinner"
          style="
            width:32px;
            height:32px;
            border-color:rgba(201,117,138,0.3);
            border-top-color:var(--rose);
          "
        ></div>

        <div class="loading-text">
          Analyzing sentiment & emotions…
        </div>

      </div>

    `;

  }


  try {

    const d =
      await apiRequest(
        '/api/sentiment/analyze',
        'POST',
        {
          reviews: text
        }
      );


    const pos =
      d.positive_percentage || 0;


    const neg =
      d.negative_percentage || 0;


    const neu =
      d.neutral_percentage || 0;


    const dominant =
      pos >= neg
        ? (
            pos >= neu
              ? 'Positive'
              : 'Neutral'
          )
        : (
            neg >= neu
              ? 'Negative'
              : 'Neutral'
          );


    const emotionEmojis = {

      happy: '😊',

      satisfied: '😌',

      excited: '🤩',

      frustrated: '😤',

      angry: '😠'

    };


    let resultsHtml = `

      <div class="panel">

        <div class="panel-title">
          📊 Sentiment Analysis Results
        </div>

        <div
          class="grid-3"
          style="margin-bottom:24px;"
        >

          <div
            style="
              text-align:center;
              padding:20px;
              background:rgba(103,194,58,0.1);
              border-radius:var(--radius);
              border:1px solid rgba(103,194,58,0.2);
            "
          >

            <div
              style="
                font-size:32px;
                font-weight:700;
                color:#4A9E27;
              "
            >
              ${pos}%
            </div>

            <div
              style="
                font-size:13px;
                color:#4A9E27;
                font-weight:500;
              "
            >
              Positive
            </div>

          </div>


          <div
            style="
              text-align:center;
              padding:20px;
              background:rgba(201,117,138,0.1);
              border-radius:var(--radius);
              border:1px solid rgba(201,117,138,0.2);
            "
          >

            <div
              style="
                font-size:32px;
                font-weight:700;
                color:var(--rose);
              "
            >
              ${neg}%
            </div>

            <div
              style="
                font-size:13px;
                color:var(--rose);
                font-weight:500;
              "
            >
              Negative
            </div>

          </div>


          <div
            style="
              text-align:center;
              padding:20px;
              background:rgba(136,135,128,0.1);
              border-radius:var(--radius);
              border:1px solid rgba(136,135,128,0.2);
            "
          >

            <div
              style="
                font-size:32px;
                font-weight:700;
                color:var(--text-mid);
              "
            >
              ${neu}%
            </div>

            <div
              style="
                font-size:13px;
                color:var(--text-mid);
                font-weight:500;
              "
            >
              Neutral
            </div>

          </div>

        </div>


        <div style="margin-bottom:20px;">

          <div
            style="
              font-weight:600;
              font-size:14px;
              color:var(--text-dark);
              margin-bottom:12px;
            "
          >
            Sentiment Breakdown
          </div>


          ${[
            ['Positive', pos, '#4A9E27'],
            ['Negative', neg, '#C9758A'],
            ['Neutral', neu, '#888780']
          ].map(([l, v, c]) => `

            <div class="sentiment-row">

              <span
                style="
                  font-size:13px;
                  width:70px;
                  color:var(--text-mid);
                "
              >
                ${l}
              </span>

              <div class="sentiment-bar-wrap">

                <div
                  class="sentiment-bar"
                  style="
                    width:${v}%;
                    background:${c};
                  "
                ></div>

              </div>

              <span
                style="
                  font-size:13px;
                  font-weight:600;
                  width:36px;
                  text-align:right;
                  color:${c};
                "
              >
                ${v}%
              </span>

            </div>

          `).join('')}

        </div>


        <div style="margin-bottom:20px;">

          <div
            style="
              font-weight:600;
              font-size:14px;
              color:var(--text-dark);
              margin-bottom:12px;
            "
          >
            Emotion Detection
          </div>


          <div
            style="
              display:flex;
              flex-wrap:wrap;
              gap:10px;
            "
          >

            ${Object.entries(d.emotions || {}).map(([k, v]) => `

              <div
                class="emotion-chip"
                style="
                  background:rgba(201,117,138,0.1);
                  border:1px solid rgba(201,117,138,0.2);
                  flex:1;
                  min-width:80px;
                  padding:12px 8px;
                "
              >

                <div
                  style="
                    font-size:24px;
                    text-align:center;
                    margin-bottom:4px;
                  "
                >
                  ${emotionEmojis[k] || '😐'}
                </div>

                <div
                  style="
                    font-size:14px;
                    font-weight:600;
                    color:var(--text-dark);
                    text-align:center;
                  "
                >
                  ${v}%
                </div>

                <div
                  style="
                    font-size:11px;
                    color:var(--text-light);
                    text-align:center;
                    text-transform:capitalize;
                  "
                >
                  ${k}
                </div>

              </div>

            `).join('')}

          </div>

        </div>


        ${
          d.keywords && d.keywords.length
            ? `

          <div style="margin-bottom:16px;">

            <div
              style="
                font-size:13px;
                font-weight:500;
                color:var(--text-mid);
                margin-bottom:8px;
              "
            >
              Extracted Keywords
            </div>

            <div
              style="
                display:flex;
                flex-wrap:wrap;
                gap:6px;
              "
            >

              ${d.keywords.map(k => `

                <span class="badge badge-rose">
                  ${k}
                </span>

              `).join('')}

            </div>

          </div>

        `
            : ''
        }


        <div
          class="content-block"
          style="
            border-left:3px solid var(--rose);
            margin-top:20px;
          "
        >

          <div class="content-block-title">
            💡 Automated Recommendation
          </div>

          <div class="content-block-body">

            Dominant Sentiment is
            <strong>${dominant}</strong>.

            ${
              dominant === 'Positive'
                ? 'Your brand maintains a strong positive resonance! Leverage these happy reviews as testimonials in your landing pages and social copy.'
                : dominant === 'Negative'
                ? 'Recommendation: Address customer frustration by streamlining slow checkout loops and analyzing product defects mentioned in top negative keywords.'
                : 'Recommendation: Encourage neutral buyers with targeted loyalty emails, limited discounts, and review prompts to convert them into brand ambassadors.'
            }

          </div>

        </div>

      </div>

    `;


    if (resultsEl) {

      resultsEl.innerHTML =
        resultsHtml;

    }


    toast(
      `Sentiment: ${dominant} overall ✓`,
      'success'
    );


  } catch (err) {

    if (resultsEl) {

      resultsEl.innerHTML = '';

    }


    toast(
      err.message || 'Could not analyze sentiment.',
      'error'
    );


  } finally {

    if (btn) {

      btn.disabled = false;

      btn.innerHTML = `

        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >

          <circle
            cx="11"
            cy="11"
            r="8"
          />

          <line
            x1="21"
            y1="21"
            x2="16.65"
            y2="16.65"
          />

        </svg>

        Analyze Sentiment

      `;

    }

  }

}


// ─── AI ASSISTANT CHATBOT ────────────────────────────────────

async function loadChatHistory() {

  const win =
    document.getElementById(
      'chat-window'
    );


  if (!win) return;


  try {

    const history =
      await apiRequest(
        '/api/assistant/history'
      );


    win.innerHTML = `

      <div class="chat-msg assistant">

        <div class="chat-name">
          BrandCraft AI
        </div>

        <div class="chat-bubble">

          Hello! I'm your BrandCraft AI Assistant 👋

          <br><br>

          I specialize in branding, marketing,
          content strategy, logo design,
          and business identity.

          How can I help you build an
          unforgettable brand today?

        </div>

      </div>

    `;


    history.forEach(m => {

      appendChatElement(
        m.sender,
        m.message
      );

    });


    win.scrollTop =
      win.scrollHeight;


  } catch (err) {

    console.error(
      'Failed to load chat history:',
      err
    );

  }

}


async function sendChat() {

  const input =
    document.getElementById(
      'chat-input'
    );


  if (!input) return;


  const msg =
    input.value.trim();


  if (!msg) return;


  input.value = '';


  appendChatElement(
    'user',
    msg
  );


  const typingId =
    appendTypingIndicator();


  try {

    const history =
      await apiRequest(
        '/api/assistant/history'
      );


    const d =
      await apiRequest(
        '/api/assistant/chat',
        'POST',
        {
          message: msg,
          history: history
        }
      );


    removeTypingIndicator(
      typingId
    );


    appendChatElement(
      'assistant',
      d.message
    );


    addActivity(
      `Chat: "${msg.slice(0, 25)}..."`
    );


    updateStats();


  } catch (err) {

    removeTypingIndicator(
      typingId
    );


    appendChatElement(
      'assistant',
      'Sorry, I encountered an error communicating with the branding core. Please check server logs.'
    );


    toast(
      err.message || 'Chat error',
      'error'
    );

  }

}


function sendPromptChip(text) {

  const input =
    document.getElementById(
      'chat-input'
    );


  if (input) {

    input.value = text;

    sendChat();

  }

}


function appendChatElement(role, text) {

  const win =
    document.getElementById(
      'chat-window'
    );


  if (!win) return;


  const names = {

    user:
      currentUser
        ? currentUser.name
        : 'You',

    assistant:
      'BrandCraft AI'

  };


  const div =
    document.createElement('div');


  div.className =
    `chat-msg ${role}`;


  let parsedText =
    text
      .replace(/\n/g, '<br>')
      .replace(
        /\*\*(.*?)\*\*/g,
        '<strong>$1</strong>'
      );


  div.innerHTML = `

    <div class="chat-name">
      ${names[role]}
    </div>

    <div class="chat-bubble">
      ${parsedText}
    </div>

  `;


  win.appendChild(div);


  win.scrollTop =
    win.scrollHeight;


  return div;

}


function appendTypingIndicator() {

  const win =
    document.getElementById(
      'chat-window'
    );


  if (!win)
    return 'typing-indicator';


  const id =
    'typing-' + Date.now();


  const div =
    document.createElement('div');


  div.id = id;


  div.className =
    'chat-msg assistant';


  div.innerHTML = `

    <div class="chat-name">
      BrandCraft AI
    </div>

    <div class="chat-bubble">

      <div class="typing-indicator">

        <div class="typing-dot"></div>

        <div class="typing-dot"></div>

        <div class="typing-dot"></div>

      </div>

    </div>

  `;


  win.appendChild(div);


  win.scrollTop =
    win.scrollHeight;


  return id;

}


function removeTypingIndicator(id) {

  const el =
    document.getElementById(id);


  if (el) el.remove();

}


async function clearChatHistory() {

  if (
    !confirm(
      'Are you sure you want to delete your persistent chat history?'
    )
  ) return;


  try {

    await apiRequest(
      '/api/assistant/history',
      'DELETE'
    );


    toast(
      'Chat history cleared.',
      'info'
    );


    loadChatHistory();

    updateStats();


  } catch (err) {

    toast(
      err.message ||
      'Could not clear chat history.',
      'error'
    );

  }

}


// ─── CURSOR SPARK TRAIL EFFECT ──────────────────────────────────

let lastSparkTime = 0;


document.addEventListener(
  'mousemove',
  (e) => {

    const now = Date.now();


    if (
      now - lastSparkTime < 20
    ) return;


    lastSparkTime = now;


    createSpark(
      e.pageX,
      e.pageY
    );

  }
);


function createSpark(x, y) {

  const spark =
    document.createElement('div');


  spark.className =
    'cursor-spark';


  const size =
    Math.random() * 8 + 4;


  const duration =
    Math.random() * 0.4 + 0.3;


  // Drift angle and distance

  const angle =
    Math.random() * Math.PI * 2;


  const distance =
    Math.random() * 35 + 15;


  const dx =
    Math.cos(angle) * distance;


  const dy =
    Math.sin(angle) * distance;


  // Alternate between peach and baby pink colors

  const colors = [
    '#FDCFB0',
    '#F8C8D4',
    '#C9758A'
  ];


  const color =
    colors[
      Math.floor(
        Math.random() * colors.length
      )
    ];


  spark.style.setProperty(
    '--size',
    `${size}px`
  );


  spark.style.setProperty(
    '--duration',
    `${duration}s`
  );


  spark.style.setProperty(
    '--color',
    color
  );


  spark.style.setProperty(
    '--dx',
    `${dx}px`
  );


  spark.style.setProperty(
    '--dy',
    `${dy}px`
  );


  spark.style.left =
    `${x - size / 2}px`;


  spark.style.top =
    `${y - size / 2}px`;


  document.body.appendChild(
    spark
  );


  // Clean up element after animation finishes

  setTimeout(() => {

    spark.remove();

  }, duration * 1000 + 100);

}