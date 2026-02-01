import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useConfig } from '../context/ConfigContext'
import { Database, Settings, ArrowRight, Check, AlertCircle, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'
import apiService from '../services/api'

const ConfigPage = () => {
  const navigate = useNavigate()
  const { config, updateConfig } = useConfig()
  const [formData, setFormData] = useState({
    databaseUrl: config.databaseUrl,
    schema: config.schema
  })
  const [isValidating, setIsValidating] = useState(false)
  const [validationStatus, setValidationStatus] = useState(null)

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    setValidationStatus(null)
  }

  const validateConfiguration = async () => {
    if (!formData.databaseUrl.trim() || !formData.schema.trim()) {
      toast.error('Please fill in both database URL and schema')
      return false
    }

    setIsValidating(true)
    try {
      // Test API connection
      await apiService.checkHealth()
      
      // Validate schema format
      const schemaValidation = await apiService.validateSchema(formData.schema)
      
      if (schemaValidation.valid) {
        setValidationStatus('success')
        toast.success('Configuration validated successfully!')
        return true
      } else {
        setValidationStatus('error')
        toast.error(`Schema validation failed: ${schemaValidation.message}`)
        return false
      }
    } catch (error) {
      setValidationStatus('error')
      toast.error(`Validation failed: ${error.response?.data?.detail || error.message}`)
      return false
    } finally {
      setIsValidating(false)
    }
  }

  const handleSaveAndContinue = async () => {
    const isValid = await validateConfiguration()
    if (isValid) {
      updateConfig({
        ...formData,
        isConfigured: true
      })
      toast.success('Configuration saved! Redirecting to chat...')
      setTimeout(() => navigate('/chat'), 1000)
    }
  }

  const resetToDefaults = () => {
    setFormData({
      databaseUrl: 'postgresql://neondb_owner:npg_KIa8Uz2BsdAF@ep-fragrant-silence-a4ljv5qz-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require',
      schema: `Table: markets
- id (integer, primary key)
- market_name (varchar)
- region (varchar)

Table: products
- id (integer, primary key)
- product_name (varchar)
- category (varchar)
- price (decimal)

Table: sales
- id (integer, primary key)
- market_id (integer, foreign key to markets.id)
- product_id (integer, foreign key to products.id)
- quantity (integer)
- revenue (decimal)
- sale_date (date)`
    })
    setValidationStatus(null)
    toast.success('Reset to default configuration')
  }

  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        {/* Header */}
        <div className="text-center mb-8 animate-fade-in">
          <div className="flex items-center justify-center mb-4">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-iris-100 to-coral-100">
              <Settings className="h-8 w-8 text-iris-600" />
            </div>
          </div>
          <h1 className="text-4xl font-bold text-slate-900 mb-2">
            Configure Your <span className="text-gradient">NL2SQL</span> System
          </h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Set up your database connection and schema to start converting natural language to SQL queries
          </p>
        </div>

        {/* Configuration Form */}
        <div className="card rounded-3xl p-8 shadow-elegant-lg animate-slide-up">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            {/* Database Configuration */}
            <div className="space-y-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-br from-iris-100 to-iris-200">
                  <Database className="h-5 w-5 text-iris-600" />
                </div>
                <h2 className="text-xl font-semibold text-slate-900">Database Connection</h2>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  PostgreSQL Connection String
                </label>
                <textarea
                  value={formData.databaseUrl}
                  onChange={(e) => handleInputChange('databaseUrl', e.target.value)}
                  className="w-full h-24 px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none font-mono text-sm"
                  placeholder="postgresql://username:password@host:port/database"
                />
                <p className="text-xs text-gray-500 mt-2">
                  Your Neon PostgreSQL connection string (default provided)
                </p>
              </div>

              <button
                onClick={resetToDefaults}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                Reset to defaults
              </button>
            </div>

            {/* Schema Configuration */}
            <div className="space-y-6">
              <div className="flex items-center space-x-3 mb-6">
                <div className="p-2 bg-primary-100 rounded-lg">
                  <Settings className="h-5 w-5 text-primary-600" />
                </div>
                <h2 className="text-xl font-semibold text-gray-900">Database Schema</h2>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Schema Definition (Data Model Format)
                </label>
                <textarea
                  value={formData.schema}
                  onChange={(e) => handleInputChange('schema', e.target.value)}
                  className="w-full h-80 px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none font-mono text-sm"
                  placeholder="Table: table_name&#10;- column_name (data_type, constraints)&#10;- foreign_key (integer, foreign key to other_table.id)"
                />
                <p className="text-xs text-gray-500 mt-2">
                  Define your database schema in the data model format shown above
                </p>
              </div>
            </div>
          </div>

          {/* Validation Status */}
          {validationStatus && (
            <div className={`mt-6 p-4 rounded-xl flex items-center space-x-3 ${
              validationStatus === 'success' 
                ? 'bg-green-50 text-green-800 border border-green-200' 
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}>
              {validationStatus === 'success' ? (
                <Check className="h-5 w-5 text-green-600" />
              ) : (
                <AlertCircle className="h-5 w-5 text-red-600" />
              )}
              <span className="font-medium">
                {validationStatus === 'success' 
                  ? 'Configuration is valid and ready to use!' 
                  : 'Please check your configuration and try again.'
                }
              </span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-200">
            <div className="text-sm text-gray-500">
              Configuration will be saved locally in your browser
            </div>
            
            <div className="flex space-x-4">
              <button
                onClick={validateConfiguration}
                disabled={isValidating}
                className="px-6 py-3 border border-primary-200 text-primary-700 rounded-xl hover:bg-primary-50 transition-colors font-medium disabled:opacity-50"
              >
                {isValidating ? (
                  <span className="loading-dots">Validating</span>
                ) : (
                  'Validate'
                )}
              </button>
              
              <button
                onClick={handleSaveAndContinue}
                disabled={isValidating}
                className="px-8 py-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors font-medium flex items-center space-x-2 disabled:opacity-50"
              >
                <span>Simple Chat</span>
                <ArrowRight className="h-4 w-4" />
              </button>
              
              <button
                onClick={() => {
                  updateConfig({ isConfigured: true })
                  navigate('/agentic')
                }}
                disabled={isValidating}
                className="px-8 py-3 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-colors font-medium flex items-center space-x-2 disabled:opacity-50"
              >
                <span>Agentic Investigation</span>
                <Sparkles className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Help Text */}
        <div className="text-center mt-8 text-sm text-gray-500">
          <p>
            Need help? The default configuration connects to your Neon database with sample schema.
            <br />
            You can modify these settings anytime from the chat interface.
          </p>
        </div>
      </div>
    </div>
  )
}

export default ConfigPage
