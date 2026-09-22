const BASE_URL = '/api'

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`)
  if (!response.ok) {
    const body = await response.text()
    throw new Error(`GET ${path} failed (${response.status}): ${body}`)
  }
  return response.json() as Promise<T>
}
