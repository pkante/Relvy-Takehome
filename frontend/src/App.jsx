import React, { useState, useRef } from 'react'
import { Upload, Send, FileText } from 'lucide-react'
import FileUpload from './components/FileUpload'
import ChatMessage from './components/ChatMessage'
import ChatInput from './components/ChatInput'

function App() {
  const [messages, setMessages] = useState([])
  const [uploadedFile, setUploadedFile] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const fileInputRef = useRef(null)

  const handleFileUpload = (file) => {
    setUploadedFile(file)
    // Clear any existing messages and conversation when a new file is uploaded
    setMessages([])
    setConversationId(null)
  }

  const handleSendMessage = async (messageText) => {
    if (!uploadedFile) {
      setMessages(prev => [...prev, {
        id: Date.now(),
        type: 'assistant',
        content: 'Please upload a log file first before asking questions.',
        timestamp: new Date()
      }])
      return
    }

    // Add user message
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: messageText,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMessage])

    // Add loading message
    const loadingMessage = {
      id: Date.now() + 1,
      type: 'assistant',
      content: 'Analyzing your logs...',
      timestamp: new Date(),
      isLoading: true
    }
    setMessages(prev => [...prev, loadingMessage])

    setIsAnalyzing(true)

    try {
      // Create FormData for file upload
      const formData = new FormData()
      formData.append('query', messageText)
      formData.append('file', uploadedFile)
      
      // Add conversation ID if we have one
      if (conversationId) {
        formData.append('conversation_id', conversationId)
      }

      // Call backend API
      const response = await fetch('http://localhost:8000/analyze-logs', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      // Store conversation ID for future messages
      if (data.conversation_id && !conversationId) {
        setConversationId(data.conversation_id)
      }
      
      // Remove loading message
      setMessages(prev => prev.filter(msg => !msg.isLoading))
      
      // Create response message with LLM analysis and cost info
      const responseMessage = {
        id: Date.now() + 2,
        type: 'assistant',
        content: `${data.response}

---
*Analysis: ${data.processing_summary} | Cost reduction: ${data.cost_reduction_percentage}% | LLM tokens: ${data.llm_tokens_used} | Cost: $${data.llm_cost}*`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, responseMessage])
    } catch (error) {
      // Remove loading message and add error
      setMessages(prev => prev.filter(msg => !msg.isLoading))
      
      const errorMessage = {
        id: Date.now() + 2,
        type: 'assistant',
        content: `Sorry, there was an error analyzing your logs: ${error.message}. Please try again.`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleFileDrop = (e) => {
    e.preventDefault()
    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFileUpload(files[0])
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
  }

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>Log Analysis Assistant</h1>
        {!uploadedFile ? (
          <p>Upload your logs and ask questions about incidents</p>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <p>📁 {uploadedFile.name} ({(uploadedFile.size / 1024 / 1024).toFixed(2)} MB)</p>
            <button
              onClick={() => {
                setUploadedFile(null)
                setMessages([])
                setConversationId(null)
                if (fileInputRef.current) {
                  fileInputRef.current.value = ''
                }
              }}
              style={{
                background: 'rgba(255,255,255,0.2)',
                border: '1px solid rgba(255,255,255,0.3)',
                color: 'white',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                cursor: 'pointer'
              }}
            >
              Upload New File
            </button>
          </div>
        )}
      </div>

      <div className="chat-messages">
        {!uploadedFile && (
          <div className="card">
            <FileUpload
              onFileUpload={handleFileUpload}
              onFileDrop={handleFileDrop}
              onDragOver={handleDragOver}
              fileInputRef={fileInputRef}
            />
          </div>
        )}

        {uploadedFile && messages.length === 0 && (
          <div className="message assistant">
            <div className="message-content">
              File "{uploadedFile.name}" uploaded successfully! You can now ask questions about your logs.
              <br />
              <small style={{ opacity: 0.8, marginTop: '8px', display: 'block' }}>
                Try asking: "Show me errors from the cart service" or "What caused the recent crashes?"
              </small>
            </div>
            <div className="message-time">
              {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {isAnalyzing && (
          <div className="message assistant">
            <div className="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
      </div>

      <div className="chat-input">
        <ChatInput onSendMessage={handleSendMessage} disabled={isAnalyzing} />
      </div>
    </div>
  )
}

export default App
