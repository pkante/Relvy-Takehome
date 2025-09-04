#!/usr/bin/env python3
"""
Intelligent Log Filtering System
Filters logs based on user queries without using AI to minimize API costs
"""

import json
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict, Counter

class LogFilter:
    def __init__(self):
        # Define severity priority (higher = more important)
        self.severity_priority = {
            'FATAL': 100, 'ERROR': 90, 'WARN': 70, 'WARNING': 70,
            'INFO': 30, 'DEBUG': 10, 'TRACE': 5
        }
        
        # Common error/issue keywords
        self.error_keywords = [
            'error', 'exception', 'failed', 'failure', 'crash', 'crashed',
            'timeout', 'refused', 'denied', 'unavailable', 'unreachable',
            'panic', 'fatal', 'critical', 'alert', 'emergency'
        ]
        
        # Service-related keywords for common issues
        self.service_patterns = {
            'cart': ['cart', 'shopping', 'basket', 'checkout'],
            'payment': ['payment', 'billing', 'transaction', 'charge'],
            'auth': ['auth', 'login', 'token', 'session', 'permission'],
            'database': ['db', 'database', 'sql', 'connection', 'query'],
            'api': ['api', 'endpoint', 'request', 'response', 'http']
        }

    def load_logs(self, file_path: str) -> List[Dict[str, Any]]:
        """Load NDJSON log file"""
        logs = []
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    log = json.loads(line.strip())
                    logs.append(log)
                except json.JSONDecodeError:
                    continue
        return logs

    def extract_service_name(self, log: Dict[str, Any]) -> str:
        """Extract service name from log entry"""
        resource_attrs = log.get('resource_attributes', {})
        
        # Try different service name fields
        service_name = (
            resource_attrs.get('service.name') or
            resource_attrs.get('k8s.deployment.name') or
            resource_attrs.get('k8s.container.name') or
            'unknown'
        )
        return service_name.lower()

    def get_severity_score(self, log: Dict[str, Any]) -> int:
        """Get severity score for prioritization"""
        fields = log.get('fields', {})
        severity_text = fields.get('severity_text', '').upper()
        return self.severity_priority.get(severity_text, 0)

    def extract_keywords_from_query(self, query: str) -> Dict[str, Any]:
        """Extract filtering criteria from user query"""
        query_lower = query.lower()
        
        criteria = {
            'services': [],
            'error_indicators': False,
            'keywords': [],
            'time_recent': False
        }
        
        # Check for service mentions
        for service, patterns in self.service_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                criteria['services'].append(service)
        
        # Check for error indicators
        if any(keyword in query_lower for keyword in self.error_keywords):
            criteria['error_indicators'] = True
        
        # Check for time-related terms
        time_keywords = ['recent', 'latest', 'current', 'now', 'today']
        if any(keyword in query_lower for keyword in time_keywords):
            criteria['time_recent'] = True
        
        # Extract other keywords (remove common words)
        stop_words = {'the', 'is', 'are', 'was', 'were', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = re.findall(r'\b\w+\b', query_lower)
        criteria['keywords'] = [word for word in words if word not in stop_words and len(word) > 2]
        
        return criteria

    def calculate_relevance_score(self, log: Dict[str, Any], criteria: Dict[str, Any]) -> float:
        """Calculate relevance score for a log entry"""
        score = 0.0
        
        # Service matching (high weight)
        service_name = self.extract_service_name(log)
        if criteria['services']:
            for service in criteria['services']:
                if service in service_name:
                    score += 50.0
                    break
        
        # Severity score (medium weight)
        severity_score = self.get_severity_score(log)
        score += severity_score * 0.5
        
        # Error indicators (high weight if query mentions errors)
        if criteria['error_indicators']:
            log_body = str(log.get('body', '')).lower()
            if any(keyword in log_body for keyword in self.error_keywords):
                score += 40.0
        
        # Keyword matching in log body (medium weight)
        log_body = str(log.get('body', '')).lower()
        for keyword in criteria['keywords']:
            if keyword in log_body:
                score += 10.0
        
        # Time recency (if requested)
        if criteria['time_recent']:
            # For now, assume more recent logs have higher timestamps
            timestamp = log.get('timestamp', 0)
            if isinstance(timestamp, str):
                timestamp = int(timestamp) if timestamp.isdigit() else 0
            # Normalize timestamp score (simple heuristic)
            score += min(timestamp / 1e15, 20.0)
        
        return score

    def filter_logs(self, logs: List[Dict[str, Any]], query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Main filtering function
        Returns filtered logs sorted by relevance
        """
        print(f"Starting with {len(logs)} logs")
        
        # Extract query criteria
        criteria = self.extract_keywords_from_query(query)
        print(f"Query criteria: {criteria}")
        
        # Stage 1: Basic filtering
        filtered_logs = []
        
        for log in logs:
            # Skip logs with no body content
            if not log.get('body'):
                continue
                
            # Calculate relevance score
            score = self.calculate_relevance_score(log, criteria)
            
            # Only keep logs with some relevance
            if score > 0:
                log['_relevance_score'] = score
                filtered_logs.append(log)
        
        print(f"After relevance filtering: {len(filtered_logs)} logs")
        
        # Stage 2: Sort by relevance and take top results
        filtered_logs.sort(key=lambda x: x['_relevance_score'], reverse=True)
        final_logs = filtered_logs[:max_results]
        
        print(f"Final filtered logs: {len(final_logs)} logs")
        
        return final_logs

    def analyze_filtered_logs(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze filtered logs to provide summary statistics"""
        if not logs:
            return {}
        
        services = Counter()
        severities = Counter()
        total_score = 0
        
        for log in logs:
            services[self.extract_service_name(log)] += 1
            severity = log.get('fields', {}).get('severity_text', 'UNKNOWN')
            severities[severity] += 1
            total_score += log.get('_relevance_score', 0)
        
        return {
            'total_logs': len(logs),
            'avg_relevance_score': total_score / len(logs),
            'top_services': dict(services.most_common(5)),
            'severity_distribution': dict(severities),
        }


def main():
    """Test the filtering system"""
    filter_system = LogFilter()
    
    # Load logs
    logs = filter_system.load_logs('../../sample_logs.ndjson')
    print(f"Loaded {len(logs)} logs from sample_logs.ndjson")
    
    # Test different queries
    test_queries = [
        "cart service is crashing, check logs",
        "payment errors in the system",
        "recent database connection issues",
        "kafka service failures",
        "recommendation service problems"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: '{query}'")
        print(f"{'='*60}")
        
        filtered_logs = filter_system.filter_logs(logs, query, max_results=50)
        analysis = filter_system.analyze_filtered_logs(filtered_logs)
        
        print(f"Analysis: {json.dumps(analysis, indent=2)}")
        
        # Show top 3 most relevant logs
        print("\nTop 3 most relevant logs:")
        for i, log in enumerate(filtered_logs[:3]):
            service = filter_system.extract_service_name(log)
            severity = log.get('fields', {}).get('severity_text', 'UNKNOWN')
            score = log.get('_relevance_score', 0)
            body = str(log.get('body', ''))[:100] + '...' if len(str(log.get('body', ''))) > 100 else str(log.get('body', ''))
            
            print(f"{i+1}. [Score: {score:.1f}] [{service}] [{severity}] {body}")


if __name__ == "__main__":
    main()
