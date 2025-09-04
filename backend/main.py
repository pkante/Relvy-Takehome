#!/usr/bin/env python3
"""
FastAPI backend for log analysis MVP
Accepts file + query and returns filtered data for LLM processing
"""

import logging
import json
import tempfile
import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from enhanced_log_filter import EnhancedLogFilter
from llm_service import LLMService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Log Analysis API",
    description="MVP for analyzing log files with intelligent filtering",
    version="1.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
filter_system = EnhancedLogFilter()
llm_service = LLMService()

# In-memory conversation storage (resets on server restart)
conversations: Dict[str, List[Dict[str, str]]] = {}
# Track which conversations have analyzed logs already
analyzed_conversations: Dict[str, Dict[str, Any]] = {}

class AnalysisResponse(BaseModel):
    """Response model for log analysis"""
    query: str
    response: str
    total_logs_processed: int
    cost_reduction_percentage: float
    processing_summary: str
    llm_tokens_used: int
    llm_cost: float
    conversation_id: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Log Analysis API is running", "version": "1.0.0"}

@app.post("/analyze-logs", response_model=AnalysisResponse)
async def analyze_logs(
    query: str = Form(..., description="User query about the logs"),
    file: UploadFile = File(..., description="Log file (.json or .ndjson)"),
    conversation_id: Optional[str] = Form(None, description="Conversation ID for context")
):
    """
    Analyze logs based on user query using LLM
    Returns LLM analysis with conversation context
    """
    logger.info(f"Received analysis request for query: '{query}'")
    logger.info(f"File: {file.filename} ({file.content_type})")
    logger.info(f"Conversation ID: {conversation_id}")
    
    # Validate file type
    if not (file.filename.endswith('.json') or file.filename.endswith('.ndjson')):
        raise HTTPException(
            status_code=400,
            detail="Only .json and .ndjson files are supported"
        )
    
    try:
        # Generate conversation ID if not provided (new conversation)
        is_new_conversation = not conversation_id
        if not conversation_id:
            import uuid
            conversation_id = str(uuid.uuid4())[:8]
            logger.info(f"Generated new conversation ID: {conversation_id}")
        
        # Check if this conversation has already analyzed logs
        is_first_analysis = conversation_id not in analyzed_conversations
        
        # Only process logs if this is the first analysis for this conversation
        if is_first_analysis:
            logger.info("First analysis for this conversation - processing logs")
            
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            logger.info(f"Saved uploaded file to {temp_file_path}")
            
            # Load and process logs
            logs = filter_system.load_logs(temp_file_path)
            logger.info(f"Loaded {len(logs)} logs from uploaded file")
            
            # Apply enhanced filtering
            windows = filter_system.filter_logs_enhanced(logs, query, max_windows=10)
            
            # Prepare LLM-ready data
            llm_data = []
            total_logs = 0
            
            for window in windows:
                window_data = {
                    'summary': window.summary,
                    'logs': []
                }
                
                # Include the most important logs from each window (max 3 per window)
                important_logs = sorted(window.logs, key=lambda x: (x.severity_number or 0), reverse=True)[:3]
                total_logs += len(important_logs)
                
                for log in important_logs:
                    window_data['logs'].append({
                        'service': log.service_name,
                        'severity': log.severity_text or 'UNKNOWN',
                        'message': log.body[:200] + ('...' if len(log.body) > 200 else ''),
                        'status': log.status,
                        'route': log.route,
                        'method': log.method,
                        'timestamp': log.timestamp_raw,
                        'trace_id': log.trace_id
                    })
                
                llm_data.append(window_data)
            
            # Calculate metrics
            cost_reduction = (1 - total_logs / len(logs)) * 100 if logs else 0
            processing_summary = f"Filtered {len(logs)} logs down to {total_logs} most relevant logs across {len(llm_data)} windows"
            
            logger.info(f"Filtering complete: {cost_reduction:.1f}% cost reduction")
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
        else:
            logger.info("Follow-up question - using cached log analysis, skipping file processing")
            # Use cached data
            llm_data = analyzed_conversations[conversation_id]['filtered_windows']
            processing_summary = analyzed_conversations[conversation_id]['log_summary']
            # Set dummy metrics for follow-up questions
            cost_reduction = 99.9
            total_logs = len([log for window in llm_data for log in window['logs']])
        
        # Get conversation history
        conversation_history = conversations.get(conversation_id, [])
        
        if is_first_analysis:
            # First time - analyze logs with full context
            logger.info("First analysis for this conversation - including log data")
            llm_result = llm_service.analyze_logs(
                filtered_windows=llm_data,
                user_query=query,
                conversation_history=conversation_history,
                processing_summary=processing_summary
            )
            
            # Store the analyzed log data for future reference
            analyzed_conversations[conversation_id] = {
                'log_summary': processing_summary,
                'filtered_windows': llm_data,
                'initial_analysis': llm_result["response"],
                'total_logs_processed': len(logs)
            }
        else:
            # Subsequent queries - just chat without re-analyzing logs
            logger.info("Follow-up question - using cached log analysis")
            llm_result = llm_service.chat_about_logs(
                user_query=query,
                conversation_history=conversation_history,
                initial_analysis=analyzed_conversations[conversation_id]['initial_analysis'],
                log_summary=analyzed_conversations[conversation_id]['log_summary']
            )
        
        # Update conversation history
        if conversation_id not in conversations:
            conversations[conversation_id] = []
        
        conversations[conversation_id].extend([
            {"role": "user", "content": query},
            {"role": "assistant", "content": llm_result["response"]}
        ])
        
        # Keep conversation history reasonable (last 10 exchanges)
        if len(conversations[conversation_id]) > 20:
            conversations[conversation_id] = conversations[conversation_id][-20:]
        
        logger.info(f"LLM analysis complete: {llm_result['tokens_used']} tokens, ${llm_result['estimated_cost']:.4f}")
        
        # Calculate total logs processed (different for first vs follow-up)
        if is_first_analysis:
            total_logs_processed = len(logs)
        else:
            # For follow-up questions, use cached data
            total_logs_processed = analyzed_conversations[conversation_id].get('total_logs_processed', 10000)
        
        return AnalysisResponse(
            query=query,
            response=llm_result["response"],
            total_logs_processed=total_logs_processed,
            cost_reduction_percentage=round(cost_reduction, 1),
            processing_summary=processing_summary,
            llm_tokens_used=llm_result["tokens_used"],
            llm_cost=round(llm_result["estimated_cost"], 4),
            conversation_id=conversation_id
        )
        
    except Exception as e:
        logger.error(f"Error processing logs: {str(e)}")
        # Clean up temp file if it exists
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing logs: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "filter_system": "initialized",
        "endpoints": ["/", "/analyze-logs", "/health"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
