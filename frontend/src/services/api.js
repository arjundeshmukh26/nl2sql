import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const apiService = {
  // Health check
  async checkHealth() {
    const response = await api.get('/health')
    return response.data
  },

  // Generate SQL only
  async generateSQL(schema, query) {
    const response = await api.post('/generate-sql', {
      schema_text: schema,
      query: query
    })
    return response.data
  },

  // Generate and execute SQL
  async executeQuery(schema, query) {
    const response = await api.post('/query', {
      schema_text: schema,
      query: query
    })
    return response.data
  },

  // Validate schema
  async validateSchema(schema) {
    const response = await api.post('/validate-schema', {
      schema_text: schema,
      description: 'User provided schema'
    })
    return response.data
  },

  // Test SQL execution
  async testSQL(sql) {
    const response = await api.post('/test-sql', {
      sql: sql
    })
    return response.data
  }
}

export default apiService
