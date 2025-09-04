import React from 'react'

const ChatMessage = ({ message }) => {
  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const formatContent = (content) => {
    // Basic markdown-like formatting for better readability
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // **bold**
      .replace(/`(.*?)`/g, '<code>$1</code>') // `code`
      .replace(/### (.*?)(\n|$)/g, '<h3>$1</h3>$2') // ### headers
      .replace(/## (.*?)(\n|$)/g, '<h2>$1</h2>$2') // ## headers
      .replace(/# (.*?)(\n|$)/g, '<h1>$1</h1>$2') // # headers
      .replace(/\n\n/g, '</p><p>') // paragraphs
      .replace(/\n- (.*?)(\n|$)/g, '<li>$1</li>') // bullet points
      .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>') // wrap lists
      .replace(/^\s*/, '<p>') // start paragraph
      .replace(/\s*$/, '</p>') // end paragraph
  }

  return (
    <div className={`message ${message.type}`}>
      <div 
        className="message-content"
        dangerouslySetInnerHTML={{ 
          __html: formatContent(message.content) 
        }}
      />
      <div className="message-time">
        {formatTime(message.timestamp)}
      </div>
    </div>
  )
}

export default ChatMessage
