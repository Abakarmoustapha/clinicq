export async function getJson(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error('The server answered ' + response.status)
  }
  return response.json()
}

export async function postJson(url, data) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  let body = null
  try {
    body = await response.json()
  } catch {
    body = null
  }
  return { ok: response.ok, status: response.status, body }
}