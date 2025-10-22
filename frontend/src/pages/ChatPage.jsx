import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useConfig } from '../context/ConfigContext'
import { 
  Send, 
  Settings, 
  Database, 
  Sparkles, 
  Copy, 
  Play,
  Clock,
  BarChart3,
  MessageSquare,
  Loader2
} from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import toast from 'react-hot-toast'
import apiService from '../services/api'

const ChatPage = () => {
  const navigate = useNavigate()
  const { config } = useConfig()
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (!config.isConfigured) {
      navigate('/config')
    }
  }, [config.isConfigured, navigate])

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await apiService.executeQuery(config.schema, userMessage.content)
      
      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: userMessage.content,
        sql: response.sql,
        results: response.results,
        rowCount: response.row_count,
        executionTime: response.execution_time_ms,
        explanation: response.explanation,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])
      toast.success(`Query executed successfully! ${response.row_count} rows returned`)
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: userMessage.content,
        error: error.response?.data?.detail || error.message,
        timestamp: new Date()
      }
      
      setMessages(prev => [...prev, errorMessage])
      toast.error('Query failed. Please check your input and try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard!')
  }

  const formatExecutionTime = (timeMs) => {
    if (timeMs < 1000) {
      return `${Math.round(timeMs)}ms`
    } else {
      return `${(timeMs / 1000).toFixed(2)}s`
    }
  }

  const exampleQueries = [
    "Show total revenue for each market in 2024",
    "What are the top 5 products by sales volume?",
    "Compare revenue between different regions",
    "Find markets with revenue above average"
  ]

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="glass-effect border-b border-white/20 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Sparkles className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">NL2SQL Chat</h1>
            <p className="text-sm text-gray-600">Ask questions about your data in natural language</p>
          </div>
        </div>
        
        <button
          onClick={() => navigate('/config')}
          className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <Settings className="h-4 w-4" />
          <span>Configure</span>
        </button>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="p-4 bg-primary-100 rounded-2xl inline-block mb-4">
              <MessageSquare className="h-12 w-12 text-primary-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Start Your Conversation</h2>
            <p className="text-gray-600 mb-8 max-w-md mx-auto">
              Ask questions about your data in natural language. I'll convert them to SQL and show you the results.
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
              {exampleQueries.map((query, index) => (
                <button
                  key={index}
                  onClick={() => setInputValue(query)}
                  className="p-4 text-left bg-white rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-md transition-all"
                >
                  <div className="flex items-start space-x-3">
                    <Database className="h-5 w-5 text-primary-600 mt-0.5" />
                    <span className="text-sm text-gray-700">{query}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className="animate-slide-up">
              {message.type === 'user' && (
                <div className="flex justify-end">
                  <div className="max-w-3xl bg-primary-600 text-white rounded-2xl rounded-br-md px-6 py-4">
                    <p className="text-sm font-medium">{message.content}</p>
                    <p className="text-xs text-primary-200 mt-2">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              )}

              {message.type === 'assistant' && (
                <div className="flex justify-start">
                  <div className="max-w-5xl w-full">
                    <div className="glass-effect rounded-2xl rounded-bl-md p-6 shadow-elegant">
                      {/* Query Header */}
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-2">
                          <Sparkles className="h-5 w-5 text-primary-600" />
                          <span className="font-medium text-gray-900">Query Result</span>
                        </div>
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          <div className="flex items-center space-x-1">
                            <Clock className="h-4 w-4" />
                            <span>{formatExecutionTime(message.executionTime)}</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <BarChart3 className="h-4 w-4" />
                            <span>{message.rowCount} rows</span>
                          </div>
                        </div>
                      </div>

                      {/* Generated SQL */}
                      <div className="mb-6">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-gray-900">Generated SQL</h4>
                          <button
                            onClick={() => copyToClipboard(message.sql)}
                            className="flex items-center space-x-1 text-sm text-gray-500 hover:text-gray-700"
                          >
                            <Copy className="h-4 w-4" />
                            <span>Copy</span>
                          </button>
                        </div>
                        <div className="rounded-lg overflow-hidden">
                          <SyntaxHighlighter
                            language="sql"
                            style={oneDark}
                            customStyle={{
                              margin: 0,
                              fontSize: '14px',
                              lineHeight: '1.5'
                            }}
                          >
                            {message.sql}
                          </SyntaxHighlighter>
                        </div>
                        {message.explanation && (
                          <p className="text-sm text-gray-600 mt-2 italic">
                            {message.explanation}
                          </p>
                        )}
                      </div>

                      {/* Results Table */}
                      {message.results && message.results.length > 0 && (
                        <div>
                          <h4 className="font-medium text-gray-900 mb-3">Results</h4>
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-gray-200">
                                  {Object.keys(message.results[0]).map((column) => (
                                    <th key={column} className="text-left py-2 px-3 font-medium text-gray-700">
                                      {column}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {message.results.slice(0, 10).map((row, index) => (
                                  <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                                    {Object.values(row).map((value, cellIndex) => (
                                      <td key={cellIndex} className="py-2 px-3 text-gray-900">
                                        {value === null ? (
                                          <span className="text-gray-400 italic">null</span>
                                        ) : typeof value === 'number' ? (
                                          value.toLocaleString()
                                        ) : (
                                          String(value)
                                        )}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          {message.results.length > 10 && (
                            <p className="text-sm text-gray-500 mt-2">
                              Showing first 10 of {message.rowCount} rows
                            </p>
                          )}
                        </div>
                      )}

                      <p className="text-xs text-gray-500 mt-4">
                        {message.timestamp.toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {message.type === 'error' && (
                <div className="flex justify-start">
                  <div className="max-w-3xl bg-red-50 border border-red-200 rounded-2xl rounded-bl-md px-6 py-4">
                    <div className="flex items-start space-x-3">
                      <div className="p-1 bg-red-100 rounded-full">
                        <Database className="h-4 w-4 text-red-600" />
                      </div>
                      <div>
                        <p className="font-medium text-red-900 mb-1">Query Failed</p>
                        <p className="text-sm text-red-700">{message.error}</p>
                        <p className="text-xs text-red-500 mt-2">
                          {message.timestamp.toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="flex justify-start animate-slide-up">
            <div className="glass-effect rounded-2xl rounded-bl-md px-6 py-4">
              <div className="flex items-center space-x-3">
                <Loader2 className="h-5 w-5 text-primary-600 animate-spin" />
                <span className="text-gray-600">Processing your query<span className="loading-dots"></span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="glass-effect border-t border-white/20 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end space-x-4">
            <div className="flex-1">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question about your data... (e.g., 'Show total revenue by market')"
                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                rows={2}
                disabled={isLoading}
              />
            </div>
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="p-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}

export default ChatPage
