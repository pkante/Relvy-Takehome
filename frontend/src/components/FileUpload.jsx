import React, { useState } from 'react'
import { Upload, FileText, X } from 'lucide-react'

const FileUpload = ({ onFileUpload, onFileDrop, onDragOver, fileInputRef }) => {
  const [dragActive, setDragActive] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      if (file.name.endsWith('.ndjson') || file.name.endsWith('.json')) {
        setSelectedFile(file)
        onFileUpload(file)
      } else {
        alert('Please upload a .ndjson or .json file')
      }
    }
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      if (file.name.endsWith('.ndjson') || file.name.endsWith('.json')) {
        setSelectedFile(file)
        onFileUpload(file)
      } else {
        alert('Please upload a .ndjson or .json file')
      }
    }
  }

  const handleRemoveFile = () => {
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const openFileDialog = () => {
    fileInputRef.current?.click()
  }

  if (selectedFile) {
    return (
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <FileText size={24} color="var(--forest-green)" />
          <div style={{ flex: 1 }}>
            <p style={{ fontWeight: '500', marginBottom: '4px' }}>{selectedFile.name}</p>
            <p style={{ fontSize: '14px', color: 'var(--dark-gray)' }}>
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          <button
            onClick={handleRemoveFile}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '4px',
              color: 'var(--dark-gray)'
            }}
          >
            <X size={20} />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`upload-area ${dragActive ? 'dragover' : ''}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={openFileDialog}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".ndjson,.json"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />
      
      <Upload className="file-upload-icon" />
      <div className="upload-text">Upload your log file</div>
      <div className="upload-hint">
        Drag and drop a .ndjson or .json file here, or click to browse
      </div>
      <div className="upload-hint" style={{ marginTop: '8px' }}>
        Supported formats: NDJSON, JSON
      </div>
    </div>
  )
}

export default FileUpload
