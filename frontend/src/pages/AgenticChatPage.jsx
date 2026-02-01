import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useConfig } from '../context/ConfigContext'
import { 
  Send, 
  Settings, 
  Database, 
  Sparkles, 
  Copy,
  Clock,
  BarChart3,
  MessageSquare,
  Loader2,
  Lightbulb,
  TrendingUp,
  Eye,
  EyeOff,
  Cog,
  CheckCircle,
  CheckCircle2,
  AlertCircle,
  Play,
  Pause,
  Activity,
  Zap,
  Search,
  ChevronRight
} from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import toast from 'react-hot-toast'
import apiService from '../services/api'
import ChartRenderer from '../components/ChartRenderer'

const AgenticChatPage = () => {
  const navigate = useNavigate()
  const { config } = useConfig()
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isInvestigating, setIsInvestigating] = useState(false)
  const [currentInvestigation, setCurrentInvestigation] = useState(null)
  const [investigationSteps, setInvestigationSteps] = useState([])
  const [showStepDetails, setShowStepDetails] = useState({})
  const [currentStep, setCurrentStep] = useState(null)
  const [progress, setProgress] = useState({ current: 0, total: 8, status: 'idle' })
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, investigationSteps])

  useEffect(() => {
    if (!config.isConfigured) {
      navigate('/config')
    }
  }, [config.isConfigured, navigate])

  const handleStartInvestigation = async () => {
    if (!inputValue.trim() || isInvestigating) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsInvestigating(true)
    setInvestigationSteps([])
    setCurrentStep('Starting investigation...')
    setProgress({ current: 0, total: 8, status: 'investigating' })
    setCurrentInvestigation({
      query: userMessage.content,
      startTime: new Date(),
      status: 'investigating'
    })

    try {
      // Simulate step-by-step progress
      const steps = [
        'Connecting to database...',
        'Analyzing database schema...',
        'Executing initial queries...',
        'Analyzing data patterns...',
        'Detecting anomalies...',
        'Performing correlation analysis...',
        'Generating insights...',
        'Finalizing recommendations...'
      ]
      
      // Show progress simulation
      for (let i = 0; i < steps.length; i++) {
        setCurrentStep(steps[i])
        setProgress({ current: i + 1, total: steps.length, status: 'investigating' })
        await new Promise(resolve => setTimeout(resolve, 800)) // Simulate work
      }
      
      // Call the agentic investigation endpoint
      const response = await apiService.startAgenticInvestigation(userMessage.content)
      
      const investigationMessage = {
        id: Date.now() + 1,
        type: 'agentic_investigation',
        content: userMessage.content,
        investigation: response,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, investigationMessage])
      setInvestigationSteps(response.investigation_steps || [])
      setCurrentInvestigation(prev => ({
        ...prev,
        status: 'completed',
        endTime: new Date(),
        summary: response.summary
      }))
      
      setCurrentStep('Investigation completed!')
      setProgress({ current: steps.length, total: steps.length, status: 'completed' })
      
      toast.success(`Investigation completed! ${response.total_steps} steps executed`)
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'error',
        content: userMessage.content,
        error: error.response?.data?.detail || error.message,
        timestamp: new Date()
      }
      
      setMessages(prev => [...prev, errorMessage])
      setCurrentStep('Investigation failed')
      setProgress({ current: 0, total: 8, status: 'error' })
      setCurrentInvestigation(prev => ({
        ...prev,
        status: 'failed',
        endTime: new Date(),
        error: error.message
      }))
      
      if (error.response?.status === 429) {
        toast.error('⏱️ API quota exceeded. Please wait before making more requests.', {
          duration: 5000
        })
      } else {
        toast.error('Investigation failed. Please check your input and try again.')
      }
    } finally {
      setIsInvestigating(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleStartInvestigation()
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard!')
  }

  const toggleStepDetails = (stepIndex) => {
    setShowStepDetails(prev => ({
      ...prev,
      [stepIndex]: !prev[stepIndex]
    }))
  }

  const formatExecutionTime = (timeMs) => {
    if (timeMs < 1000) {
      return `${Math.round(timeMs)}ms`
    } else {
      return `${(timeMs / 1000).toFixed(2)}s`
    }
  }

  const formatMarkdownText = (text) => {
    if (!text) return ''
    
    return text
      // Convert **bold** to <strong>
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Convert *italic* to <em>
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // Convert numbered lists
      .replace(/^\d+\.\s+(.*)$/gm, '<div class="ml-4 mb-1">$1</div>')
      // Convert bullet points
      .replace(/^\*\s+(.*)$/gm, '<div class="ml-4 mb-1">• $1</div>')
      // Convert line breaks
      .replace(/\n\n/g, '<br><br>')
      .replace(/\n/g, '<br>')
  }



  const getStepIcon = (stepType, toolName) => {
    // Special icons for visualization tools
    if (toolName === 'generate_chart' || toolName === 'suggest_visualization') {
      return <BarChart3 className="h-4 w-4 text-purple-600" />
    }
    
    // Special icons for specific graph tools
    if (toolName && toolName.includes('chart') || toolName && toolName.includes('plot')) {
      return <TrendingUp className="h-4 w-4 text-green-600" />
    }
    
    switch (stepType) {
      case 'tool_call':
        return <Cog className="h-4 w-4 text-blue-600" />
      case 'analysis':
        return <Activity className="h-4 w-4 text-orange-600" />
      case 'conclusion':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-600" />
      case 'retry':
        return <Clock className="h-4 w-4 text-yellow-600" />
      default:
        return <Activity className="h-4 w-4 text-gray-600" />
    }
  }

  const getStepColor = (stepType) => {
    switch (stepType) {
      case 'tool_call':
        return 'border-slate-200 bg-white'
      case 'analysis':
        return 'border-amber-200 bg-amber-50/50'
      case 'conclusion':
        return 'border-emerald-200 bg-emerald-50/50'
      case 'error':
        return 'border-red-200 bg-red-50/50'
      case 'retry':
        return 'border-amber-200 bg-amber-50/50'
      default:
        return 'border-slate-200 bg-slate-50/50'
    }
  }

  const renderInvestigationStep = (step, index) => {
    const isExpanded = showStepDetails[index]
    const hasError = step.result?.error || step.result?.data?.error
    
    return (
      <div key={index} className={`rounded-xl border transition-all duration-200 ${
        isExpanded ? 'shadow-md' : 'shadow-sm hover:shadow-md'
      } ${getStepColor(step.step_type)}`}>
        <div 
          className="flex items-center justify-between cursor-pointer p-4"
          onClick={() => toggleStepDetails(index)}
        >
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              step.step_type === 'tool_call' ? 'bg-blue-100' :
              step.step_type === 'conclusion' ? 'bg-green-100' :
              step.step_type === 'error' ? 'bg-red-100' :
              'bg-slate-100'
            }`}>
              {getStepIcon(step.step_type, step.tool_name)}
            </div>
            <div>
              <h4 className="font-medium text-slate-900 text-sm">{step.description}</h4>
              {step.tool_name && (
                <p className="text-xs text-slate-500 mt-0.5 font-mono">{step.tool_name}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {hasError && (
              <span className="text-xs text-red-600 bg-red-100 px-2 py-0.5 rounded-full">Error</span>
            )}
            {step.result?.success && !hasError && (
              <span className="text-xs text-green-600 bg-green-100 px-2 py-0.5 rounded-full">Success</span>
            )}
            {step.result?.execution_time_ms && (
              <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                {formatExecutionTime(step.result.execution_time_ms)}
              </span>
            )}
            <div className={`p-1 rounded transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
              <ChevronRight className={`h-4 w-4 text-slate-400 transform ${isExpanded ? 'rotate-90' : ''}`} />
            </div>
          </div>
        </div>

        {isExpanded && (
          <div className="px-4 pb-4 pt-0 space-y-4 border-t border-slate-200/50">
            {step.reasoning && (
              <div className="pt-3">
                <h5 className="font-medium text-slate-600 mb-1 text-xs uppercase tracking-wide">Reasoning</h5>
                <p className="text-sm text-slate-700 bg-slate-50 rounded-lg p-3">{step.reasoning}</p>
              </div>
            )}

            {step.parameters && Object.keys(step.parameters).length > 0 && (
              <div>
                <h5 className="font-medium text-slate-600 mb-1 text-xs uppercase tracking-wide">Parameters</h5>
                <div className="bg-slate-800 rounded-lg p-3 text-xs font-mono text-slate-200 overflow-x-auto">
                  <pre className="whitespace-pre-wrap">{JSON.stringify(step.parameters, null, 2)}</pre>
                </div>
              </div>
            )}

            {/* Results Section */}
            {step.result && (
              <div>
                <h5 className="font-medium text-slate-700 mb-2 text-sm">Result:</h5>
                
                {step.step_type === 'tool_call' && (
                  <div className="bg-white/50 rounded-lg border border-slate-200 p-4">
                    {/* Render Charts - Check for chart tools */}
                    {(step.tool_name === 'generate_bar_chart' || 
                      step.tool_name === 'generate_line_chart' || 
                      step.tool_name === 'generate_pie_chart' || 
                      step.tool_name === 'generate_scatter_plot') && (
                      <div>
                        {/* Get chart data - handle wrapped structure: step.result.data.data */}
                        {(() => {
                          const chartData = step.result?.data?.data || step.result?.data || [];
                          const chartTitle = step.result?.data?.title || step.parameters?.title || 'Chart';
                          const chartConfig = step.result?.data?.config || {};
                          
                          if (Array.isArray(chartData) && chartData.length > 0) {
                            return (
                              <div className="space-y-3">
                                <div className="flex items-center gap-2">
                                  <BarChart3 className="h-5 w-5 text-iris-600" />
                                  <h6 className="font-semibold text-slate-800">{chartTitle}</h6>
                                  <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                                    {chartData.length} data points
                                  </span>
                                </div>
                                <ChartRenderer 
                                  toolName={step.tool_name}
                                  data={chartData}
                                  title={chartTitle}
                                  xLabel={chartConfig.x_label || step.parameters?.x_label}
                                  yLabel={chartConfig.y_label || step.parameters?.y_label}
                                />
                              </div>
                            );
                          } else if (step.result?.error || step.result?.data?.error) {
                            return (
                              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                <p className="text-red-700 text-sm font-medium">Chart generation failed</p>
                                <p className="text-red-600 text-xs mt-1">{step.result?.error || step.result?.data?.error}</p>
                              </div>
                            );
                          } else {
                            return (
                              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                                <p className="text-amber-700 text-sm">No chart data available</p>
                              </div>
                            );
                          }
                        })()}
                      </div>
                    )}
                    
                    {/* Visualization suggestions */}
                    {step.tool_name === 'suggest_visualization' && step.result?.data?.visualization_suggestions && (
                      <div>
                        <div className="flex items-center gap-2 mb-3">
                          <Lightbulb className="h-5 w-5 text-amber-500" />
                          <h6 className="font-semibold text-slate-800">Visualization Suggestions</h6>
                        </div>
                        <div className="grid gap-2">
                          {step.result.data.visualization_suggestions.map((suggestion, idx) => (
                            <div key={idx} className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-lg p-3">
                              <p className="font-medium text-amber-800">{suggestion.chart_type.toUpperCase()}: {suggestion.title}</p>
                              <p className="text-slate-600 text-sm mt-1">{suggestion.use_case}</p>
                              <p className="text-xs text-slate-500 mt-1">
                                X: {suggestion.x_field} • Y: {suggestion.y_field}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Other tool results */}
                    {!['generate_bar_chart', 'generate_line_chart', 'generate_pie_chart', 'generate_scatter_plot', 'suggest_visualization'].includes(step.tool_name) && (
                      <div>
                        {/* Show error if present */}
                        {(step.result?.error || step.result?.data?.error) && (
                          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
                            <p className="text-red-700 text-sm font-medium">Error</p>
                            <p className="text-red-600 text-xs mt-1">{step.result?.error || step.result?.data?.error}</p>
                          </div>
                        )}
                        {/* Show data */}
                        {!step.result?.error && (
                          <div className="max-h-64 overflow-y-auto rounded-lg">
                            <SyntaxHighlighter
                              language="json"
                              style={oneDark}
                              className="text-xs"
                              customStyle={{
                                margin: 0,
                                borderRadius: '0.5rem',
                                fontSize: '0.7rem',
                                padding: '0.75rem'
                              }}
                            >
                              {JSON.stringify(step.result?.data || step.result, null, 2)}
                            </SyntaxHighlighter>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Additional result types */}
            {step.result && step.step_type === 'analysis' && step.result.analysis && (
              <div className="bg-white/80 rounded-lg border border-slate-200 p-4">
                <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                  {step.result.analysis}
                </p>
              </div>
            )}
            
            {step.result && step.step_type === 'conclusion' && step.result.analysis && (
              <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl border border-emerald-200 p-5">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-emerald-100 rounded-lg">
                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                  </div>
                  <div>
                    <h5 className="font-semibold text-emerald-900">Complete Analysis & Recommendations</h5>
                    <p className="text-xs text-emerald-600">Comprehensive results with metrics included</p>
                  </div>
                </div>
                
                {/* Investigation Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                  <div className="bg-white/80 rounded-lg p-3 text-center border border-emerald-100">
                    <div className="text-2xl font-bold text-blue-600">{investigationSteps.filter(s => s.step_type === 'tool_call').length}</div>
                    <div className="text-xs text-slate-500 mt-1">Tools Used</div>
                  </div>
                  <div className="bg-white/80 rounded-lg p-3 text-center border border-emerald-100">
                    <div className="text-2xl font-bold text-emerald-600">{investigationSteps.filter(s => s.tool_name && s.tool_name.includes('execute_sql_query')).length}</div>
                    <div className="text-xs text-slate-500 mt-1">SQL Queries</div>
                  </div>
                  <div className="bg-white/80 rounded-lg p-3 text-center border border-emerald-100">
                    <div className="text-2xl font-bold text-purple-600">{investigationSteps.filter(s => s.tool_name && (s.tool_name.includes('chart') || s.tool_name.includes('plot'))).length}</div>
                    <div className="text-xs text-slate-500 mt-1">Visualizations</div>
                  </div>
                  <div className="bg-white/80 rounded-lg p-3 text-center border border-emerald-100">
                    <div className="text-2xl font-bold text-amber-600">{investigationSteps.filter(s => s.tool_name && s.tool_name.includes('business')).length}</div>
                    <div className="text-xs text-slate-500 mt-1">Business Metrics</div>
                  </div>
                </div>

                {/* Main Analysis Content */}
                <div className="bg-white/80 rounded-lg p-4 border border-emerald-100">
                  <div 
                    className="text-sm text-slate-700 leading-relaxed prose prose-sm max-w-none prose-headings:text-slate-900 prose-strong:text-slate-900"
                    dangerouslySetInnerHTML={{
                      __html: formatMarkdownText(step.result.analysis)
                    }}
                  />
                </div>
              </div>
            )}
            
            {step.result && !['tool_call', 'analysis', 'conclusion'].includes(step.step_type) && (
              <div className="bg-gray-100 rounded p-2 text-xs font-mono max-h-32 overflow-y-auto">
                {JSON.stringify(step.result, null, 2)}
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  const exampleQueries = [
    "Analyze our sales performance and identify improvement opportunities",
    "What trends do you see in our customer behavior?",
    "Find anomalies and unusual patterns in our data",
    "Compare performance across different regions and time periods"
  ]

  return (
    <div className="h-screen flex flex-col bg-stone-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-coral-400 to-coral-500 text-white">
            <Zap className="h-4 w-4" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-900">Agentic Investigation</h1>
            <p className="text-xs text-slate-500">Multi-step autonomous analysis</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {currentInvestigation && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-stone-100 rounded-lg border border-slate-200">
              {isInvestigating ? (
                <>
                  <div className="w-2 h-2 rounded-full bg-coral-500 animate-pulse"></div>
                  <span className="text-xs text-slate-600 font-medium">
                    {currentStep}
                  </span>
                  <div className="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-iris-500 to-coral-500 transition-all duration-300"
                      style={{ width: `${(progress.current / progress.total) * 100}%` }}
                    />
                  </div>
                </>
              ) : currentInvestigation.status === 'completed' ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  <span className="text-xs text-green-700 font-medium">Complete</span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-4 w-4 text-red-500" />
                  <span className="text-xs text-red-700 font-medium">Failed</span>
                </>
              )}
            </div>
          )}
          
          <button
            onClick={() => navigate('/chat')}
            className="btn btn-ghost px-3 py-2 text-sm gap-2"
          >
            <Database className="h-4 w-4" />
            <span className="hidden sm:inline">Basic Mode</span>
          </button>
          <button onClick={() => navigate('/config')} className="btn btn-ghost px-3 py-2 text-sm gap-2">
            <Settings className="h-4 w-4" />
            <span className="hidden sm:inline">Settings</span>
          </button>
        </div>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-7xl mx-auto w-full">
        {messages.length === 0 ? (
          <div className="pt-12 pb-8 animate-fade-in">
            <div className="text-center mb-10">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-coral-100 to-iris-100 mb-5">
                <Search className="h-8 w-8 text-coral-600" />
              </div>
            <h2 className="text-2xl font-semibold text-slate-900 mb-2">Ask a bigger question</h2>
            <p className="text-slate-500 max-w-lg mx-auto">
              Go beyond simple queries. Ask complex questions and I'll investigate your data from multiple angles to find meaningful answers.
            </p>
            
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-3xl mx-auto">
                {exampleQueries.map((query, index) => (
                  <button
                    key={index}
                    onClick={() => setInputValue(query)}
                    className="card card-interactive p-4 text-left group"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">🔍</span>
                      <span className="text-sm text-slate-700 group-hover:text-slate-900">{query}</span>
                      <ChevronRight className="h-4 w-4 text-slate-300 ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className="animate-slide-up">
              {message.type === 'user' && (
                <div className="flex justify-center">
                  <div className="max-w-4xl w-full flex justify-end">
                    <div className="max-w-3xl bg-purple-600 text-white rounded-2xl rounded-br-md px-6 py-4">
                      <p className="text-sm font-medium">{message.content}</p>
                      <p className="text-xs text-purple-200 mt-2">
                        {message.timestamp.toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {message.type === 'agentic_investigation' && (
                <div className="flex justify-center">
                  <div className="max-w-6xl w-full">
                    <div className="glass-effect rounded-2xl rounded-bl-md p-6 shadow-elegant">
                      {/* Investigation Header */}
                      <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center space-x-2">
                          <Sparkles className="h-5 w-5 text-purple-600" />
                          <span className="font-medium text-gray-900">Autonomous Investigation Results</span>
                        </div>
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          <div className="flex items-center space-x-1">
                            <Clock className="h-4 w-4" />
                            <span>{formatExecutionTime(message.investigation.execution_time_ms)}</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Activity className="h-4 w-4" />
                            <span>{message.investigation.total_steps} steps</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Cog className="h-4 w-4" />
                            <span>{message.investigation.tools_used?.length || 0} tools</span>
                          </div>
                        </div>
                      </div>

                      {/* Investigation Steps */}
                      <div className="mb-6">
                        <h4 className="font-medium text-gray-900 mb-4">Investigation Process</h4>
                        <div className="space-y-3">
                          {message.investigation.investigation_steps?.map((step, index) => 
                            renderInvestigationStep(step, index)
                          )}
                        </div>
                      </div>

                      {/* Summary */}
                      {message.investigation.summary && (
                        <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                          <h4 className="font-medium text-purple-900 mb-2">Investigation Summary</h4>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                              <span className="text-purple-700 font-medium">Total Steps:</span>
                              <span className="ml-2 text-purple-900">{message.investigation.summary.total_steps}</span>
                            </div>
                            <div>
                              <span className="text-purple-700 font-medium">Tool Calls:</span>
                              <span className="ml-2 text-purple-900">{message.investigation.summary.tool_calls}</span>
                            </div>
                            <div>
                              <span className="text-purple-700 font-medium">Analyses:</span>
                              <span className="ml-2 text-purple-900">{message.investigation.summary.analyses}</span>
                            </div>
                            <div>
                              <span className="text-purple-700 font-medium">Conclusions:</span>
                              <span className="ml-2 text-purple-900">{message.investigation.summary.conclusions}</span>
                            </div>
                          </div>
                          
                          {message.investigation.tools_used && message.investigation.tools_used.length > 0 && (
                            <div className="mt-3">
                              <span className="text-purple-700 font-medium">Tools Used:</span>
                              <div className="flex flex-wrap gap-2 mt-1">
                                {message.investigation.tools_used.map((tool, index) => (
                                  <span key={index} className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">
                                    {tool}
                                  </span>
                                ))}
                              </div>
                            </div>
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
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      </div>
                      <div>
                        <p className="font-medium text-red-900 mb-1">Investigation Failed</p>
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
        
        {isInvestigating && (
          <div className="flex justify-start animate-slide-up">
            <div className="glass-effect rounded-2xl rounded-bl-md px-6 py-4">
              <div className="flex items-center space-x-3">
                <Loader2 className="h-5 w-5 text-purple-600 animate-spin" />
                <span className="text-gray-600">
                  Conducting autonomous investigation<span className="loading-dots"></span>
                </span>
              </div>
              {investigationSteps.length > 0 && (
                <div className="mt-3 text-sm text-gray-500">
                  Completed {investigationSteps.length} investigation steps...
                </div>
              )}
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="bg-white/80 backdrop-blur-sm border-t border-slate-200 p-4">
        <div className="max-w-5xl mx-auto">
          <div className="flex gap-3">
            <div className="flex-1">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a complex question like 'What factors are driving our best-performing products?'"
                className="input pr-4 py-3.5 text-[15px] min-h-[52px] max-h-32 resize-none"
                rows={1}
                disabled={isInvestigating}
              />
            </div>
            <button
              onClick={handleStartInvestigation}
              disabled={!inputValue.trim() || isInvestigating}
              className="btn bg-gradient-to-r from-iris-600 to-coral-500 text-white hover:from-iris-700 hover:to-coral-600 px-4 py-3 shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isInvestigating ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-2 text-center">
            Press Enter to start · Shift + Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}

export default AgenticChatPage
