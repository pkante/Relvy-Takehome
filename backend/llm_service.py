#!/usr/bin/env python3
"""
LLM Service for log analysis
Handles OpenAI API calls with conversation context
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-4o-mini"
        
        # System prompt
        self.system_prompt = """You are an expert log analysis assistant. You help developers understand and debug issues in their application logs.

FORMATTING REQUIREMENTS:
- Use clear markdown formatting with headers, bullet points, and code blocks
- Keep responses well-structured and scannable
- Use emojis sparingly for visual hierarchy (🚨 for critical, ⚠️ for warnings, 💡 for suggestions)
- Break up long paragraphs into shorter, digestible sections
- Use **bold** for important terms and `code formatting` for technical details

ANALYSIS APPROACH:
- Start with a brief summary of the most critical issues
- Organize findings by severity (Critical → Warnings → Info)
- Provide specific, actionable recommendations
- Include relevant trace IDs and technical details when helpful
- End with clear next steps

TONE:
- Professional but approachable
- Focus on actionable insights over lengthy explanations
- Prioritize what developers need to know to fix issues quickly"""

    def analyze_logs(self, 
                    filtered_windows: List[Dict[str, Any]], 
                    user_query: str, 
                    conversation_history: List[Dict[str, str]] = None,
                    processing_summary: str = "") -> Dict[str, Any]:
        """
        Analyze filtered logs using AI
        
        Args:
            filtered_windows: The filtered log windows from our enhanced filter
            user_query: The user's current query
            conversation_history: Previous messages in this conversation
            processing_summary: Summary of the filtering process
            
        Returns:
            Dict with LLM response and metadata
        """
        try:
            log_context = self._prepare_log_context(filtered_windows, processing_summary)

            #cache to store messages
            messages = [{"role": "system", "content": self.system_prompt}]

            if conversation_history:
                messages.extend(conversation_history)

            user_message = f"""**User Query:** {user_query}

**Filtered Log Data:**
{log_context}

Please analyze these logs and help me understand what's happening with my system."""

            messages.append({"role": "user", "content": user_message})
            
            logger.info(f"Sending request to OpenAI with {len(messages)} messages")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1500,
                temperature=0.1  
            )
            
            llm_response = response.choices[0].message.content
            
            # Calculate cost (approximate)
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            
            input_cost = (input_tokens / 1000000) * 0.15  # $0.15 per 1M input tokens
            output_cost = (output_tokens / 1000000) * 0.60  # $0.60 per 1M output tokens
            total_cost = input_cost + output_cost
            
            logger.info(f"OpenAI response received. Tokens: {total_tokens}, Cost: ${total_cost:.4f}")
            
            return {
                "response": llm_response,
                "tokens_used": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost": total_cost,
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise Exception(f"LLM analysis failed: {str(e)}")

    def chat_about_logs(self, 
                       user_query: str, 
                       conversation_history: List[Dict[str, str]] = None,
                       initial_analysis: str = "",
                       log_summary: str = "") -> Dict[str, Any]:
        """
        Chat about previously analyzed logs without re-analyzing
        Uses cached analysis to save costs
        """
        try:
            # Build conversation messages with cached context
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add the initial analysis as context
            context_message = f"""**Previous Log Analysis:**
{initial_analysis}

**Log Summary:** {log_summary}

You have already analyzed the user's logs. Use this previous analysis to answer follow-up questions. Do not re-analyze the logs - just reference your previous findings and provide helpful insights based on the user's new question."""

            messages.append({"role": "assistant", "content": context_message})
            
            # Add conversation history if available
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add the current query
            messages.append({"role": "user", "content": user_query})
            
            logger.info(f"Sending follow-up chat request to OpenAI with {len(messages)} messages")
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=800,  # Smaller for follow-up questions
                temperature=0.1
            )
            
            # Extract response
            llm_response = response.choices[0].message.content
            
            # Calculate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            
            # GPT-4o mini pricing
            input_cost = (input_tokens / 1000000) * 0.15
            output_cost = (output_tokens / 1000000) * 0.60
            total_cost = input_cost + output_cost
            
            logger.info(f"Follow-up response received. Tokens: {total_tokens}, Cost: ${total_cost:.4f}")
            
            return {
                "response": llm_response,
                "tokens_used": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost": total_cost,
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Error in follow-up chat: {str(e)}")
            raise Exception(f"Follow-up chat failed: {str(e)}")

    def _prepare_log_context(self, filtered_windows: List[Dict[str, Any]], processing_summary: str) -> str:
        """Prepare log data in a format optimized for LLM analysis"""
        
        context_parts = [f"**Processing Summary:** {processing_summary}", ""]
        
        for i, window in enumerate(filtered_windows, 1):
            context_parts.append(f"**Window {i}: {window['summary']}**")
            
            for j, log in enumerate(window['logs'], 1):
                log_info = []
                
                if log.get('service') and log['service'] != 'unknown':
                    log_info.append(f"Service: {log['service']}")

                if log.get('severity'):
                    log_info.append(f"Severity: {log['severity']}")
                
                if log.get('method') and log.get('route'):
                    log_info.append(f"HTTP: {log['method']} {log['route']}")
                elif log.get('route'):
                    log_info.append(f"Route: {log['route']}")
                
                # status code
                if log.get('status'):
                    log_info.append(f"Status: {log['status']}")
                
                # trace ID
                if log.get('trace_id'):
                    log_info.append(f"Trace: {log['trace_id'][:16]}...")
                
                # format log entry
                log_header = f"  Log {j}: {' | '.join(log_info)}" if log_info else f"  Log {j}:"
                context_parts.append(log_header)
                context_parts.append(f"    Message: {log['message']}")
                context_parts.append("")
        
        return "\n".join(context_parts)

    def health_check(self) -> bool:
        """Check if OpenAI API is accessible"""
        try:
            # simple test
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                temperature=0.1
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {str(e)}")
            return False
