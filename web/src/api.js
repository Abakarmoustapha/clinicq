export async function getJson(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error('The server answered ' + response.status)
  }
  return response.json()
}