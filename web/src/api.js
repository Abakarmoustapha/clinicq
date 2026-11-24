function getCookie(name) {
  const parts = document.cookie ? document.cookie.split('; ') : []
  for (const part of parts) {
    const index = part.indexOf('=')
    if (part.slice(0, index) === name) {
      return decodeURIComponent(part.slice(index + 1))
    }
  }
  return null
}

async function readBody(response) {
  try {
    return await response.json()
  } catch {
    return null
  }
}

// Asks the server to set the CSRF cookie, once, before the first change.
let csrfRequest = null
export function ensureCsrf() {
  if (getCookie('csrftoken')) return Promise.resolve()
  if (!csrfRequest) {
    csrfRequest = fetch('/api/auth/csrf/')
      .then(() => undefined)
      .finally(() => {
        csrfRequest = null
      })
  }
  return csrfRequest
}

export async function getJson(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error('The server answered ' + response.status)
  }
  return response.json()
}

export async function getResult(url) {
  const response = await fetch(url)
  return { ok: response.ok, status: response.status, body: await readBody(response) }
}

export async function postJson(url, data) {
  await ensureCsrf()
  const headers = { 'Content-Type': 'application/json' }
  const token = getCookie('csrftoken')
  if (token) headers['X-CSRFToken'] = token
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(data ?? {}),
  })
  return { ok: response.ok, status: response.status, body: await readBody(response) }
}