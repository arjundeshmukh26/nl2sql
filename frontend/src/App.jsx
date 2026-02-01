import React, { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ConfigPage from './pages/ConfigPage'
import ChatPage from './pages/ChatPage'
import AgenticChatPage from './pages/AgenticChatPage'
import { ConfigProvider } from './context/ConfigContext'

function App() {
  return (
    <ConfigProvider>
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        <Routes>
          <Route path="/" element={<Navigate to="/config" replace />} />
          <Route path="/config" element={<ConfigPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/agentic" element={<AgenticChatPage />} />
        </Routes>
      </div>
    </ConfigProvider>
  )
}

export default App