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
  Loader2,
  Lightbulb,
  TrendingUp,
  Eye,
  EyeOff
} from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import toast from 'react-hot-toast'
import apiService from '../services/api'
import { formatInsights, formatTableValue } from '../utils/formatters'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  RadialLinearScale,
} from 'chart.js'
import { Bar, Line, Pie, Scatter, Doughnut, PolarArea, Radar } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  RadialLinearScale
)

const ChatPage = () => {
  const navigate = useNavigate()
  const { config } = useConfig()
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [loadingInsights, setLoadingInsights] = useState({})
  const [loadingViz, setLoadingViz] = useState({})
  const [showFullResults, setShowFullResults] = useState({})
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

  const generateInsights = async (messageId, userQuery, results, sql) => {
    setLoadingInsights(prev => ({ ...prev, [messageId]: true }))
    
    try {
      const response = await apiService.generateInsights(userQuery, results, sql)
      
      setMessages(prev => prev.map(msg => 
        msg.id === messageId 
          ? { ...msg, insights: response.insights, dataSummary: response.data_summary }
          : msg
      ))
      
      toast.success('Insights generated successfully!')
    } catch (error) {
      toast.error('Failed to generate insights: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoadingInsights(prev => ({ ...prev, [messageId]: false }))
    }
  }

  const generateVisualization = async (messageId, userQuery, results, sql) => {
    setLoadingViz(prev => ({ ...prev, [messageId]: true }))
    
    try {
      console.log('🔄 Frontend: Requesting visualization for:', {
        messageId,
        query: userQuery,
        sql: sql,
        resultsLength: results?.length,
        sampleResults: results?.slice(0, 2)
      })
      
      const response = await apiService.generateVisualization(userQuery, results, sql)
      
      console.log('📊 Frontend: Received visualization response:', response)
      console.log('📊 Frontend: Chart type:', response.chart_type)
      console.log('📊 Frontend: Data type:', typeof response.data)
      console.log('📊 Frontend: Data length:', response.data?.length)
      console.log('📊 Frontend: Sample data:', response.data?.slice(0, 2))
      console.log('📊 Frontend: Aggregated data:', response.aggregated_data)
      
      setMessages(prev => prev.map(msg => 
        msg.id === messageId 
          ? { 
              ...msg, 
              visualization: {
                chartType: response.chart_type,
                data: response.data || response.aggregated_data, // Try both fields
                sql: response.sql,
                explanation: response.explanation
              }
            }
          : msg
      ))
      
      toast.success('Visualization generated successfully!')
    } catch (error) {
      toast.error('Failed to generate visualization: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoadingViz(prev => ({ ...prev, [messageId]: false }))
    }
  }

  const toggleFullResults = (messageId) => {
    setShowFullResults(prev => ({ ...prev, [messageId]: !prev[messageId] }))
  }

  const formatExecutionTime = (timeMs) => {
    if (timeMs < 1000) {
      return `${Math.round(timeMs)}ms`
    } else {
      return `${(timeMs / 1000).toFixed(2)}s`
    }
  }

  const renderChart = (visualization) => {
    console.log('🎨 Frontend: renderChart called with:', visualization)
    console.log('🎨 Frontend: visualization.data:', visualization?.data)
    console.log('🎨 Frontend: data type:', typeof visualization?.data)
    console.log('🎨 Frontend: data length:', visualization?.data?.length)
    
    if (!visualization || !visualization.data || visualization.data.length === 0) {
      return (
        <div className="flex items-center justify-center h-64 text-gray-500">
          <div className="text-center">
            <BarChart3 className="h-12 w-12 mx-auto mb-2 text-gray-400" />
            <p className="font-medium">No Data Available</p>
            <p className="text-sm">The query returned no results to visualize</p>
          </div>
        </div>
      )
    }

    const data = visualization.data
    const chartType = (visualization.chartType || 'bar').toLowerCase()
    
      // Prepare chart data - handle multi-column data intelligently
      const columns = Object.keys(data[0])
      console.log('🎨 Available columns:', columns)
      
      // For this specific data structure, create meaningful labels and values
      let labels, values
      
      if (columns.includes('region') && columns.includes('category') && columns.includes('total_revenue')) {
        // Create combined labels: "Region - Category"
        labels = data.map(row => `${row.region} - ${row.category}`)
        // Use total_revenue as the primary value (convert string to number)
        values = data.map(row => parseFloat(row.total_revenue) || 0)
        console.log('🎨 Using region-category labels with total_revenue values')
      } else {
        // Fallback: use first column as labels, second as values
        labels = data.map(row => Object.values(row)[0])
        values = data.map(row => {
          const val = Object.values(row)[1]
          return typeof val === 'string' ? parseFloat(val) || 0 : val
        })
        console.log('🎨 Using fallback: first column as labels, second as values')
      }
      
      console.log('🎨 Final labels:', labels)
      console.log('🎨 Final values:', values)
    
    const colors = [
      'rgba(59, 130, 246, 0.8)',   // Blue
      'rgba(16, 185, 129, 0.8)',   // Green
      'rgba(245, 158, 11, 0.8)',   // Amber
      'rgba(239, 68, 68, 0.8)',    // Red
      'rgba(139, 92, 246, 0.8)',   // Purple
      'rgba(236, 72, 153, 0.8)',   // Pink
      'rgba(34, 197, 94, 0.8)',    // Emerald
      'rgba(251, 146, 60, 0.8)',   // Orange
      'rgba(20, 184, 166, 0.8)',   // Teal
      'rgba(168, 85, 247, 0.8)',   // Violet
    ]

    const borderColors = colors.map(color => color.replace('0.8', '1'))
    
      const chartData = {
        labels,
        datasets: [
          {
            label: 'Total Revenue',
          data: values,
          backgroundColor: chartType === 'line' ? 'rgba(59, 130, 246, 0.1)' : colors,
          borderColor: chartType === 'line' ? 'rgba(59, 130, 246, 1)' : borderColors,
          borderWidth: 2,
          fill: chartType === 'area',
          tension: chartType === 'line' ? 0.4 : 0,
          pointBackgroundColor: chartType === 'line' ? 'rgba(59, 130, 246, 1)' : undefined,
          pointBorderColor: chartType === 'line' ? '#fff' : undefined,
          pointBorderWidth: chartType === 'line' ? 2 : undefined,
        },
      ],
    }

    // Special handling for scatter plots
    if (chartType === 'scatter' && data.length > 0) {
      const keys = Object.keys(data[0])
      if (keys.length >= 2) {
        chartData.datasets[0].data = data.map(row => ({
          x: row[keys[0]],
          y: row[keys[1]]
        }))
      }
    }

    const baseOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: {
            usePointStyle: true,
            padding: 20,
          }
        },
          title: {
            display: true,
            text: 'Total Revenue by Region and Category',
          font: {
            size: 16,
            weight: 'bold'
          },
          padding: 20,
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: '#fff',
          bodyColor: '#fff',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
        }
      },
    }

    // Chart-specific options
    let options = { ...baseOptions }
    
    if (!['pie', 'doughnut', 'polararea', 'radar'].includes(chartType)) {
      options.scales = {
        y: {
          beginAtZero: true,
          grid: {
            color: 'rgba(0, 0, 0, 0.1)',
          },
          ticks: {
            callback: function(value) {
              return typeof value === 'number' ? value.toLocaleString() : value
            }
          }
        },
        x: {
          grid: {
            color: 'rgba(0, 0, 0, 0.1)',
          }
        }
      }
    }

    // Radar chart specific options
    if (chartType === 'radar') {
      options.scales = {
        r: {
          beginAtZero: true,
          grid: {
            color: 'rgba(0, 0, 0, 0.1)',
          }
        }
      }
    }

    const chartProps = {
      data: chartData,
      options: options,
      height: 300
    }

    switch (chartType) {
      case 'line':
        return <Line {...chartProps} />
      case 'pie':
        return <Pie {...chartProps} />
      case 'doughnut':
        return <Doughnut {...chartProps} />
      case 'scatter':
        return <Scatter {...chartProps} />
      case 'polararea':
        return <PolarArea {...chartProps} />
      case 'radar':
        return <Radar {...chartProps} />
      case 'area':
        return <Line {...chartProps} />
      default:
        return <Bar {...chartProps} />
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
      <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-6xl mx-auto w-full">
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
                <div className="flex justify-center">
                  <div className="max-w-4xl w-full flex justify-end">
                    <div className="max-w-3xl bg-primary-600 text-white rounded-2xl rounded-br-md px-6 py-4">
                      <p className="text-sm font-medium">{message.content}</p>
                      <p className="text-xs text-primary-200 mt-2">
                        {message.timestamp.toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {message.type === 'assistant' && (
                <div className="flex justify-center">
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
                      <div className="mb-8">
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

                      {/* Action Buttons */}
                      <div className="flex items-center space-x-3 mb-8">
                        <button
                          onClick={() => generateInsights(message.id, message.content, message.results, message.sql)}
                          disabled={loadingInsights[message.id]}
                          className="flex items-center space-x-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50"
                        >
                          {loadingInsights[message.id] ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Lightbulb className="h-4 w-4" />
                          )}
                          <span>Generate Insights</span>
                        </button>
                        
                        <button
                          onClick={() => generateVisualization(message.id, message.content, message.results, message.sql)}
                          disabled={loadingViz[message.id]}
                          className="flex items-center space-x-2 px-4 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors disabled:opacity-50"
                        >
                          {loadingViz[message.id] ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <TrendingUp className="h-4 w-4" />
                          )}
                          <span>Generate Visualization</span>
                        </button>
                      </div>

                      {/* Insights Section */}
                      {message.insights && (
                        <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                          <div className="flex items-center space-x-2 mb-3">
                            <Lightbulb className="h-5 w-5 text-blue-600" />
                            <h4 className="font-medium text-blue-900">AI Insights</h4>
                          </div>
                          <div className="text-sm text-blue-800 whitespace-pre-line leading-relaxed">
                            {formatInsights(message.insights)}
                          </div>
                        </div>
                      )}

                      {/* Visualization Section */}
                      {message.visualization && (
                        <div className="mb-6 p-4 bg-green-50 rounded-lg border border-green-200">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center space-x-2">
                              <TrendingUp className="h-5 w-5 text-green-600" />
                              <h4 className="font-medium text-green-900">Visualization</h4>
                              <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full font-medium">
                                {(message.visualization.chartType || 'bar').toUpperCase()}
                              </span>
                            </div>
                            {message.visualization.explanation && (
                              <p className="text-xs text-green-700 italic max-w-md">
                                {message.visualization.explanation}
                              </p>
                            )}
                          </div>
                          <div className="bg-white rounded-lg p-4">
                            {renderChart(message.visualization)}
                          </div>
                          {message.visualization.sql !== message.sql && (
                            <div className="mt-3">
                              <p className="text-xs text-green-700 mb-2">Aggregation Query:</p>
                              <div className="bg-gray-900 rounded text-xs p-2 font-mono text-gray-100">
                                {message.visualization.sql}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Results Table */}
                      {message.results && message.results.length > 0 && (
                        <div>
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="font-medium text-gray-900">Results</h4>
                            <button
                              onClick={() => toggleFullResults(message.id)}
                              className="flex items-center space-x-1 text-sm text-gray-500 hover:text-gray-700"
                            >
                              {showFullResults[message.id] ? (
                                <>
                                  <EyeOff className="h-4 w-4" />
                                  <span>Show Less</span>
                                </>
                              ) : (
                                <>
                                  <Eye className="h-4 w-4" />
                                  <span>Show All ({message.rowCount} rows)</span>
                                </>
                              )}
                            </button>
                          </div>
                          <div className="overflow-x-auto bg-white rounded-lg border border-gray-200">
                            <table className="w-full text-sm">
                              <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
                                <tr className="border-b border-gray-200">
                                  {Object.keys(message.results[0]).map((column) => (
                                    <th key={column} className="text-left py-4 px-6 font-semibold text-gray-800 uppercase text-xs tracking-wider">
                                      {column.replace(/_/g, ' ')}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {(showFullResults[message.id] ? message.results : message.results.slice(0, 10)).map((row, index) => (
                                  <tr key={index} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                                    {Object.values(row).map((value, cellIndex) => {
                                      const formatted = formatTableValue(value)
                                      return (
                                        <td 
                                          key={cellIndex} 
                                          className={`py-4 px-6 ${formatted.className}`}
                                          title={formatted.title}
                                        >
                                          {formatted.value}
                                        </td>
                                      )
                                    })}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          {!showFullResults[message.id] && message.results.length > 10 && (
                            <p className="text-sm text-gray-500 mt-2">
                              Showing first 10 of {message.rowCount} rows. Click "Show All" to see complete results.
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
        <div className="max-w-5xl mx-auto">
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
