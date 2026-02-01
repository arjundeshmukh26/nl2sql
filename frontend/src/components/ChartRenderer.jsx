import React from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js'
import { Line, Bar, Pie, Scatter } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
)

const ChartRenderer = ({ toolName, data, title, xLabel, yLabel }) => {
  // Debug logging
  console.log('ChartRenderer received:', { toolName, data, title, xLabel, yLabel });
  
  // Handle different data formats
  const processChartData = () => {
    if (!data || !Array.isArray(data)) {
      console.log('Data is not an array:', data);
      return null
    }
    
    console.log('Processing chart data for:', toolName, 'with', data.length, 'items');

    // Generate colors for charts
    const generateColors = (count) => {
      const colors = [
        'rgba(59, 130, 246, 0.8)',   // Blue
        'rgba(16, 185, 129, 0.8)',   // Green  
        'rgba(245, 101, 101, 0.8)',  // Red
        'rgba(251, 191, 36, 0.8)',   // Yellow
        'rgba(139, 92, 246, 0.8)',   // Purple
        'rgba(236, 72, 153, 0.8)',   // Pink
        'rgba(34, 197, 94, 0.8)',    // Emerald
        'rgba(249, 115, 22, 0.8)',   // Orange
        'rgba(168, 85, 247, 0.8)',   // Violet
        'rgba(14, 165, 233, 0.8)',   // Sky
      ]
      return Array.from({ length: count }, (_, i) => colors[i % colors.length])
    }

    const borderColors = generateColors(data.length).map(color => color.replace('0.8', '1'))
    const backgroundColors = generateColors(data.length)

    switch (toolName) {
      case 'generate_line_chart':
        // Time series data
        return {
          labels: data.map(item => {
            if (item.month) {
              return new Date(item.month).toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'short' 
              })
            }
            return Object.keys(item)[0]
          }),
          datasets: [{
            label: yLabel || 'Value',
            data: data.map(item => {
              const values = Object.values(item)
              return values[values.length - 1] // Get the numeric value
            }),
            borderColor: 'rgba(59, 130, 246, 1)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.4,
            fill: true
          }]
        }

      case 'generate_bar_chart':
        // Bar chart data
        return {
          labels: data.map(item => {
            const keys = Object.keys(item)
            return item[keys[0]] // First field is usually the label
          }),
          datasets: [{
            label: yLabel || 'Value',
            data: data.map(item => {
              const values = Object.values(item)
              return values[values.length - 1] // Last field is usually the value
            }),
            backgroundColor: backgroundColors,
            borderColor: borderColors,
            borderWidth: 1
          }]
        }

      case 'generate_pie_chart':
        // Pie chart data
        return {
          labels: data.map(item => {
            const keys = Object.keys(item)
            return item[keys[0]] // First field is the label
          }),
          datasets: [{
            data: data.map(item => {
              const values = Object.values(item)
              return values[values.length - 1] // Last field is the value
            }),
            backgroundColor: backgroundColors,
            borderColor: borderColors,
            borderWidth: 2
          }]
        }

      case 'generate_scatter_plot':
        // Scatter plot data
        return {
          datasets: [{
            label: `${xLabel || 'X'} vs ${yLabel || 'Y'}`,
            data: data.map(item => ({
              x: Object.values(item)[0],
              y: Object.values(item)[1]
            })),
            backgroundColor: 'rgba(59, 130, 246, 0.6)',
            borderColor: 'rgba(59, 130, 246, 1)',
            pointRadius: 5,
            pointHoverRadius: 7
          }]
        }

      default:
        return null
    }
  }

  const chartData = processChartData()
  
  if (!chartData) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-4">
        <p className="text-red-600 text-sm">Unable to render chart - invalid data format</p>
      </div>
    )
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: title || 'Chart',
        font: {
          size: 16,
          weight: 'bold'
        }
      },
    },
    scales: toolName !== 'generate_pie_chart' ? {
      x: {
        title: {
          display: true,
          text: xLabel || 'X Axis'
        }
      },
      y: {
        title: {
          display: true,
          text: yLabel || 'Y Axis'
        }
      }
    } : {}
  }

  const renderChart = () => {
    switch (toolName) {
      case 'generate_line_chart':
        return <Line data={chartData} options={chartOptions} />
      case 'generate_bar_chart':
        return <Bar data={chartData} options={chartOptions} />
      case 'generate_pie_chart':
        return <Pie data={chartData} options={chartOptions} />
      case 'generate_scatter_plot':
        return <Scatter data={chartData} options={chartOptions} />
      default:
        return <div className="text-gray-500">Unsupported chart type</div>
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
      <div className="h-80 w-full">
        {renderChart()}
      </div>
      <div className="mt-3 text-xs text-gray-500 text-center">
        📊 {data.length} data points • Generated by {toolName}
      </div>
    </div>
  )
}

export default ChartRenderer
