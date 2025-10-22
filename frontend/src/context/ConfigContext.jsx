import React, { createContext, useContext, useState, useEffect } from 'react'

const ConfigContext = createContext()

export const useConfig = () => {
  const context = useContext(ConfigContext)
  if (!context) {
    throw new Error('useConfig must be used within a ConfigProvider')
  }
  return context
}

export const ConfigProvider = ({ children }) => {
  const [config, setConfig] = useState(() => {
    // Load from localStorage or use defaults
    const saved = localStorage.getItem('nl2sql-config')
    if (saved) {
      return JSON.parse(saved)
    }
    
    return {
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
- sale_date (date)`,
      isConfigured: false
    }
  })

  const updateConfig = (newConfig) => {
    const updatedConfig = { ...config, ...newConfig }
    setConfig(updatedConfig)
    localStorage.setItem('nl2sql-config', JSON.stringify(updatedConfig))
  }

  const resetConfig = () => {
    localStorage.removeItem('nl2sql-config')
    setConfig({
      databaseUrl: 'postgresql://neondb_owner:npg_KIa8Uz2BsdAF@ep-fragrant-silence-a4ljv5qz-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require',
      schema: '',
      isConfigured: false
    })
  }

  return (
    <ConfigContext.Provider value={{ config, updateConfig, resetConfig }}>
      {children}
    </ConfigContext.Provider>
  )
}
