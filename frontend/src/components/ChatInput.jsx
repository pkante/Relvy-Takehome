import React, { useState } from 'react'
import { Send } from 'lucide-react'

const ChatInput = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSendMessage(message.trim())
      setMessage('')
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="chat-input-form">
      <input
        type="text"
        className="input"
        placeholder="Ask about your logs (e.g., 'cart service is crashing, check logs')"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyPress={handleKeyPress}
        disabled={disabled}
      />
      <button
        type="submit"
        className="btn btn-primary"
        disabled={!message.trim() || disabled}
      >
        <Send size={20} />
        Send
      </button>
    </form>
  )
}

export default ChatInput
