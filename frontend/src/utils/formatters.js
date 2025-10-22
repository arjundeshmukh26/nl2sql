// Utility functions for formatting text and data

export const formatInsights = (text) => {
  if (!text) return ''
  
  return text
    // Remove markdown bold formatting
    .replace(/\*\*(.*?)\*\*/g, '$1')
    // Remove markdown italic formatting
    .replace(/\*(.*?)\*/g, '$1')
    // Remove markdown headers
    .replace(/#{1,6}\s*/g, '')
    // Convert markdown bullet points to proper bullets
    .replace(/^\s*[-*+]\s+/gm, '• ')
    // Convert numbered lists
    .replace(/^\s*\d+\.\s+/gm, (match, offset, string) => {
      const lineStart = string.lastIndexOf('\n', offset) + 1
      const lineNumber = string.substring(lineStart, offset).match(/\d+/)?.[0] || '1'
      return `${lineNumber}. `
    })
    // Clean up extra whitespace
    .replace(/\n\s*\n/g, '\n')
    .trim()
}

export const formatNumber = (value) => {
  if (value === null || value === undefined) return 'N/A'
  if (typeof value === 'number') {
    if (Number.isInteger(value)) {
      return value.toLocaleString()
    } else {
      return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
    }
  }
  return String(value)
}

export const formatTableValue = (value) => {
  if (value === null || value === undefined) {
    return { value: 'null', className: 'text-gray-400 italic' }
  }
  
  if (typeof value === 'number') {
    return { 
      value: formatNumber(value), 
      className: 'text-gray-900 font-medium' 
    }
  }
  
  if (typeof value === 'boolean') {
    return { 
      value: value ? 'true' : 'false', 
      className: value ? 'text-green-600' : 'text-red-600' 
    }
  }
  
  if (typeof value === 'string' && value.length > 50) {
    return { 
      value: value.substring(0, 50) + '...', 
      className: 'text-gray-900',
      title: value 
    }
  }
  
  return { value: String(value), className: 'text-gray-900' }
}
