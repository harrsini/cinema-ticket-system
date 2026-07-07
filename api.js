import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

/**
 * Send a message to the CineBot backend.
 * @param {string} message
 * @returns {Promise<object>} result from cinema_tool
 */
export async function sendMessage(message) {
  const { data } = await client.post('/chat', { message })
  return data
}
