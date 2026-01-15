const $ = (id) => document.getElementById(id)

function getKey() {
  return localStorage.getItem('panel_api_key') || ''
}

function setKey(v) {
  localStorage.setItem('panel_api_key', v)
}

async function apiFetch(path, opts = {}) {
  const headers = Object.assign({}, opts.headers || {})
  const key = getKey()
  if (key) headers['X-API-Key'] = key

  const res = await fetch(path, {
    ...opts,
    headers,
  })

  const text = await res.text()
  let json
  try { json = JSON.parse(text) } catch { json = { raw: text } }

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${JSON.stringify(json)}`)
  }
  return json
}

function renderUsers(items) {
  const root = $('users')
  root.innerHTML = ''

  for (const u of items) {
    const el = document.createElement('div')
    el.className = 'user'
    el.innerHTML = `
      <div class="id">${u.discord_user_id}</div>
      <div class="meta">Баланс: ${u.balance}</div>
      <div class="meta">Remanga: ${u.remanga_profile_url || '—'}</div>
    `
    root.appendChild(el)
  }
}

window.addEventListener('DOMContentLoaded', () => {
  $('apiKey').value = getKey()

  $('saveKey').addEventListener('click', () => {
    setKey($('apiKey').value.trim())
  })

  $('healthBtn').addEventListener('click', async () => {
    $('healthOut').textContent = '...'
    try {
      const data = await apiFetch('/api/health')
      $('healthOut').textContent = JSON.stringify(data, null, 2)
    } catch (e) {
      $('healthOut').textContent = String(e)
    }
  })

  $('loadUsers').addEventListener('click', async () => {
    $('users').textContent = '...'
    try {
      const data = await apiFetch('/api/users?limit=100')
      renderUsers(data.items || [])
    } catch (e) {
      $('users').textContent = String(e)
    }
  })

  $('banBtn').addEventListener('click', async () => {
    $('banOut').textContent = '...'
    try {
      const userId = $('banUserId').value.trim()
      const days = Number($('banDays').value || 7)
      const reason = $('banReason').value.trim()
      const data = await apiFetch(`/api/user/${userId}/ban`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days, reason }),
      })
      $('banOut').textContent = JSON.stringify(data, null, 2)
    } catch (e) {
      $('banOut').textContent = String(e)
    }
  })

  $('unbanBtn').addEventListener('click', async () => {
    $('banOut').textContent = '...'
    try {
      const userId = $('banUserId').value.trim()
      const data = await apiFetch(`/api/user/${userId}/unban`, { method: 'POST' })
      $('banOut').textContent = JSON.stringify(data, null, 2)
    } catch (e) {
      $('banOut').textContent = String(e)
    }
  })
})
