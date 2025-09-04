#!/usr/bin/env python3
"""
Enhanced Intelligent Log Filtering System
Implements advanced filtering strategies for maximum accuracy with minimal API costs
"""

import json
import re
import hashlib
import logging
from typing import List, Dict, Any, Tuple, Optional, Union
from datetime import datetime, timezone
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from pathlib import Path
import uuid

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class LogEntry:
    """Normalized log entry with defensive field extraction"""
    raw: Dict[str, Any]
    timestamp: Optional[datetime] = None
    timestamp_raw: Optional[str] = None
    severity_text: Optional[str] = None
    severity_number: Optional[int] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    status: Optional[int] = None
    route: Optional[str] = None
    method: Optional[str] = None
    body: str = ""
    service_name: str = "unknown"
    is_hot: bool = False
    template_hash: Optional[str] = None

@dataclass
class LogWindow:
    """A window of related logs (trace-based or time-based)"""
    logs: List[LogEntry] = field(default_factory=list)
    trace_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    importance_score: float = 0.0
    prompt_match_score: float = 0.0
    template_counts: Dict[str, int] = field(default_factory=dict)
    summary: str = ""

class EnhancedLogFilter:
    def __init__(self):
        # Severity mappings with numeric values
        self.severity_mappings = {
            'FATAL': (100, 'FATAL'), 'EMERGENCY': (100, 'FATAL'), 'PANIC': (100, 'FATAL'),
            'ERROR': (90, 'ERROR'), 'ERR': (90, 'ERROR'), 'CRITICAL': (85, 'ERROR'),
            'WARN': (70, 'WARN'), 'WARNING': (70, 'WARN'), 'ALERT': (75, 'WARN'),
            'INFO': (30, 'INFO'), 'INFORMATION': (30, 'INFO'), 'NOTICE': (35, 'INFO'),
            'DEBUG': (10, 'DEBUG'), 'TRACE': (5, 'DEBUG'), 'VERBOSE': (8, 'DEBUG')
        }
        
        # Hot event patterns (high precision indicators)
        self.error_patterns = re.compile(r'\b(error|exception|failed?|failure|crash|timeout|refused|denied|unavailable|unreachable|panic|fatal|critical|alert|emergency|abort|kill|interrupt)\b', re.IGNORECASE)
        
        # HTTP status patterns
        self.status_pattern = re.compile(r'\b(status[:\s]*([45]\d{2})|HTTP[/\s]*([45]\d{2})|\b([45]\d{2})\b)', re.IGNORECASE)
        
        # Route patterns
        self.route_pattern = re.compile(r'(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+([/\w\-\.:]+)|(?:route|path|endpoint)[:\s]*([/\w\-\.:]+)', re.IGNORECASE)
        
        # Method patterns
        self.method_pattern = re.compile(r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', re.IGNORECASE)
        
        # Template patterns for deduplication
        self.template_patterns = [
            (re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE), 'UUID'),
            (re.compile(r'\b\d+\b'), 'NUM'),
            (re.compile(r'"[^"]*"'), 'STR'),
            (re.compile(r"'[^']*'"), 'STR'),
            (re.compile(r'\b[0-9a-f]{16,64}\b', re.IGNORECASE), 'HASH'),
            (re.compile(r'\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}'), 'TIMESTAMP')
        ]

    def normalize_log_entry(self, raw_log: Dict[str, Any]) -> LogEntry:
        """Defensive field extraction with multiple fallback paths"""
        entry = LogEntry(raw=raw_log)
        
        entry.timestamp_raw, entry.timestamp = self._extract_timestamp(raw_log)
        entry.severity_text, entry.severity_number = self._extract_severity(raw_log)
        
        # trace id
        entry.trace_id = self._extract_trace_id(raw_log)
        entry.span_id = self._extract_span_id(raw_log)
        
        entry.status = self._extract_status(raw_log)
        
        entry.route = self._extract_route(raw_log)
        entry.method = self._extract_method(raw_log)
        entry.body = self._extract_body(raw_log)
    
        entry.service_name = self._extract_service_name(raw_log)
        
        entry.is_hot = self._is_hot_event(entry)
       
        entry.template_hash = self._generate_template_hash(entry.body)
        
        return entry

    def _extract_timestamp(self, log: Dict[str, Any]) -> Tuple[Optional[str], Optional[datetime]]:
        """Extract timestamp with multiple fallback paths"""
        timestamp_fields = [
            'timestamp', '@timestamp', 'time', 'ts', 'datetime',
            'fields.timestamp', 'attributes.timestamp'
        ]
        
        for field_path in timestamp_fields:
            value = self._safe_get_nested(log, field_path)
            if value is not None:
                dt = self._parse_timestamp(value)
                if dt:
                    return str(value), dt
        
        return None, None

    def _parse_timestamp(self, value: Union[str, int, float]) -> Optional[datetime]:
        """Parse timestamp from various formats"""
        if isinstance(value, (int, float)):
            try:
                # Handle nanosecond, microsecond, millisecond, and second timestamps
                if value > 1e15:  # Nanoseconds
                    return datetime.fromtimestamp(value / 1e9, tz=timezone.utc)
                elif value > 1e12:  # Microseconds
                    return datetime.fromtimestamp(value / 1e6, tz=timezone.utc)
                elif value > 1e10:  # Milliseconds
                    return datetime.fromtimestamp(value / 1e3, tz=timezone.utc)
                else:  # Seconds
                    return datetime.fromtimestamp(value, tz=timezone.utc)
            except (ValueError, OSError):
                pass
        
        if isinstance(value, str):
            # Try ISO8601 formats
            iso_formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S',
            ]
            
            for fmt in iso_formats:
                try:
                    return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        
        return None

    def _extract_severity(self, log: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
        """Extract severity with normalization"""
        severity_fields = [
            'fields.severity_text', 'severity_text', 'severity', 'level',
            'fields.severity_number', 'severity_number', 'levelname'
        ]
        
        for field_path in severity_fields:
            value = self._safe_get_nested(log, field_path)
            if value is not None:
                if isinstance(value, str):
                    normalized = value.upper().strip()
                    if normalized in self.severity_mappings:
                        num, text = self.severity_mappings[normalized]
                        return text, num
                elif isinstance(value, int):
                    # Map numeric levels to text
                    if value >= 90:
                        return 'ERROR', value
                    elif value >= 70:
                        return 'WARN', value
                    elif value >= 30:
                        return 'INFO', value
                    else:
                        return 'DEBUG', value
        
        return None, None

    def _extract_trace_id(self, log: Dict[str, Any]) -> Optional[str]:
        """Extract trace ID from various locations"""
        trace_fields = [
            'fields.trace_id', 'trace_id', 'traceId', 'traceid',
            'attributes.trace_id', 'spans.trace_id', 'context.trace_id'
        ]
        
        for field_path in trace_fields:
            value = self._safe_get_nested(log, field_path)
            if value and isinstance(value, str) and len(value) > 8:
                return value
        
        # Try to extract from body
        body = self._extract_body(log)
        trace_match = re.search(r'trace[_-]?id[:\s=]*([a-f0-9]{16,64})', body, re.IGNORECASE)
        if trace_match:
            return trace_match.group(1)
        
        return None

    def _extract_span_id(self, log: Dict[str, Any]) -> Optional[str]:
        """Extract span ID"""
        span_fields = [
            'fields.span_id', 'span_id', 'spanId', 'spanid',
            'attributes.span_id'
        ]
        
        for field_path in span_fields:
            value = self._safe_get_nested(log, field_path)
            if value and isinstance(value, str):
                return value
        
        return None

    def _extract_status(self, log: Dict[str, Any]) -> Optional[int]:
        """Extract HTTP status code"""
        status_fields = [
            'status', 'status_code', 'http.status_code', 'response.status',
            'attributes.http.status_code', 'fields.status'
        ]
        
        for field_path in status_fields:
            value = self._safe_get_nested(log, field_path)
            if isinstance(value, int) and 100 <= value <= 599:
                return value
            elif isinstance(value, str) and value.isdigit():
                status = int(value)
                if 100 <= status <= 599:
                    return status
        
        body = self._extract_body(log)
        status_match = self.status_pattern.search(body)
        if status_match:
            for group in status_match.groups():
                if group and group.isdigit():
                    status = int(group)
                    if 100 <= status <= 599:
                        return status
        
        return None

    def _extract_route(self, log: Dict[str, Any]) -> Optional[str]:
        """Extract route/endpoint"""
        route_fields = [
            'route', 'path', 'endpoint', 'url', 'uri',
            'http.route', 'http.target', 'attributes.http.route'
        ]
        
        for field_path in route_fields:
            value = self._safe_get_nested(log, field_path)
            if value and isinstance(value, str) and value.startswith('/'):
                return value
        
        body = self._extract_body(log)
        route_match = self.route_pattern.search(body)
        if route_match:
            for group in route_match.groups():
                if group and group.startswith('/'):
                    return group
        
        return None

    def _extract_method(self, log: Dict[str, Any]) -> Optional[str]:
        """Extract HTTP method"""
        method_fields = [
            'method', 'http.method', 'request.method',
            'attributes.http.method'
        ]
        
        for field_path in method_fields:
            value = self._safe_get_nested(log, field_path)
            if value and isinstance(value, str):
                method = value.upper()
                if method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                    return method
    
        body = self._extract_body(log)
        method_match = self.method_pattern.search(body)
        if method_match:
            return method_match.group(1).upper()
        
        return None

    def _extract_body(self, log: Dict[str, Any]) -> str:
        """Extract log message/body with fallbacks"""
        body_fields = [
            'body', 'message', 'msg', 'text', 'log',
            'attributes.message', 'fields.message'
        ]
        
        for field_path in body_fields:
            value = self._safe_get_nested(log, field_path)
            if value:
                return str(value)
        
        # If no body field found, return string representation of entire log
        return str(log)

    def _extract_service_name(self, log: Dict[str, Any]) -> str:
        """Extract service name with fallbacks"""
        service_fields = [
            'resource_attributes.service.name',
            'service.name', 'service_name', 'serviceName',
            'resource_attributes.k8s.deployment.name',
            'resource_attributes.k8s.container.name',
            'k8s.deployment.name', 'k8s.container.name',
            'container_name', 'app', 'component'
        ]
        
        for field_path in service_fields:
            value = self._safe_get_nested(log, field_path)
            if value and isinstance(value, str):
                return value.lower()
        
        return 'unknown'

    def _safe_get_nested(self, obj: Dict[str, Any], path: str) -> Any:
        """Safely get nested dictionary value"""
        keys = path.split('.')
        current = obj
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current

    def _is_hot_event(self, entry: LogEntry) -> bool:
        """Determine if this is a hot event (high importance)"""
        # Severity >= WARN
        if entry.severity_number and entry.severity_number >= 70:
            return True
        
        # Status >= 500
        if entry.status and entry.status >= 500:
            return True
        
        # Error keywords in body
        if self.error_patterns.search(entry.body):
            return True
        
        return False

    def _generate_template_hash(self, body: str) -> str:
        """Generate template hash for deduplication"""
        template = body
        for pattern, replacement in self.template_patterns:
            template = pattern.sub(replacement, template)
        
        return hashlib.md5(template.encode()).hexdigest()[:8]

    def load_logs(self, file_path: str) -> List[LogEntry]:
        """Load logs from NDJSON or JSON array"""
        logs = []
        
        with open(file_path, 'r') as f:
            content = f.read().strip()
            
            # Try to parse as JSON array first
            try:
                if content.startswith('['):
                    json_logs = json.loads(content)
                    for log_data in json_logs:
                        logs.append(self.normalize_log_entry(log_data))
                    return logs
            except json.JSONDecodeError:
                pass
            
            # Parse as NDJSON
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                try:
                    log_data = json.loads(line)
                    logs.append(self.normalize_log_entry(log_data))
                except json.JSONDecodeError:
                    continue
        
        return logs

    def hot_event_prefilter(self, logs: List[LogEntry]) -> List[LogEntry]:
        """Quick prefilter to keep only interesting logs"""
        hot_logs = [log for log in logs if log.is_hot]
        logger.info(f"Hot event prefilter: {len(logs)} → {len(hot_logs)} logs")
        return hot_logs

    def create_trace_windows(self, logs: List[LogEntry], window_seconds: int = 30, max_window_size: int = 40) -> List[LogWindow]:
        """Create trace-based or time-based windows"""
        windows = []
        processed_logs = set()
        
        # Group by trace_id first
        trace_groups = defaultdict(list)
        no_trace_logs = []
        
        for log in logs:
            if log.trace_id:
                trace_groups[log.trace_id].append(log)
            else:
                no_trace_logs.append(log)
        
        # Create trace-based windows
        for trace_id, trace_logs in trace_groups.items():
            if len(trace_logs) <= max_window_size:
                window = LogWindow(
                    logs=trace_logs,
                    trace_id=trace_id,
                    start_time=min((log.timestamp for log in trace_logs if log.timestamp), default=None),
                    end_time=max((log.timestamp for log in trace_logs if log.timestamp), default=None)
                )
                windows.append(window)
                processed_logs.update(id(log) for log in trace_logs)
        
        # Create time-based windows for logs without trace_id
        remaining_logs = [log for log in no_trace_logs if id(log) not in processed_logs]
        remaining_logs.sort(key=lambda x: x.timestamp or datetime.min.replace(tzinfo=timezone.utc))
        
        i = 0
        while i < len(remaining_logs):
            window_logs = [remaining_logs[i]]
            base_time = remaining_logs[i].timestamp
            
            j = i + 1
            while j < len(remaining_logs) and len(window_logs) < max_window_size:
                current_time = remaining_logs[j].timestamp
                if base_time and current_time and (current_time - base_time).total_seconds() <= window_seconds:
                    window_logs.append(remaining_logs[j])
                    j += 1
                else:
                    break
            
            window = LogWindow(
                logs=window_logs,
                start_time=min((log.timestamp for log in window_logs if log.timestamp), default=None),
                end_time=max((log.timestamp for log in window_logs if log.timestamp), default=None)
            )
            windows.append(window)
            i = j if j > i + 1 else i + 1
        
        return windows

    def deduplicate_templates(self, window: LogWindow) -> LogWindow:
        """Apply template deduplication within window"""
        template_counts = Counter()
        unique_logs = []
        seen_templates = set()
        
        for log in window.logs:
            if log.template_hash not in seen_templates:
                unique_logs.append(log)
                seen_templates.add(log.template_hash)
            template_counts[log.template_hash] += 1
        
        window.logs = unique_logs
        window.template_counts = dict(template_counts)
        return window

    def calculate_importance_score(self, window: LogWindow) -> float:
        """Calculate importance score for window"""
        score = 0.0
        
        for log in window.logs:
            if log.severity_number:
                score += log.severity_number * 0.5
            
            if log.status and log.status >= 500:
                score += 30

            if self.error_patterns.search(log.body):
                score += 20

            template_count = window.template_counts.get(log.template_hash, 1)
            score += max(10 - template_count, 1)
        
        if window.end_time:
            hours_ago = (datetime.now(timezone.utc) - window.end_time).total_seconds() / 3600
            if hours_ago < 24:
                score += max(10 - hours_ago, 0)
        
        return score

    def parse_query_advanced(self, query: str) -> Dict[str, Any]:
        """Enhanced query parsing for routes, methods, IDs"""
        query_lower = query.lower()
        
        criteria = {
            'services': [],
            'routes': [],
            'methods': [],
            'user_ids': [],
            'error_indicators': False,
            'keywords': [],
            'time_recent': False,
            'status_codes': []
        }

        route_matches = re.findall(r'(/[\w\-\./]+)', query)
        criteria['routes'].extend(route_matches)

        method_matches = re.findall(r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', query.upper())
        criteria['methods'].extend(method_matches)

        user_id_matches = re.findall(r'user[:\s]+(\w+)', query_lower)
        criteria['user_ids'].extend(user_id_matches)
        
        status_matches = re.findall(r'\b([45]\d{2})\b', query)
        criteria['status_codes'].extend([int(s) for s in status_matches])

        service_patterns = {
            'cart': ['cart', 'shopping', 'basket', 'checkout'],
            'payment': ['payment', 'billing', 'transaction', 'charge'],
            'auth': ['auth', 'login', 'token', 'session', 'permission'],
            'database': ['db', 'database', 'sql', 'connection', 'query'],
            'api': ['api', 'endpoint', 'request', 'response', 'http']
        }
        
        for service, patterns in service_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                criteria['services'].append(service)

        error_keywords = ['error', 'exception', 'failed', 'failure', 'crash', 'timeout', 'refused']
        if any(keyword in query_lower for keyword in error_keywords):
            criteria['error_indicators'] = True
        
        # Time indicators
        time_keywords = ['recent', 'latest', 'current', 'now', 'today']
        if any(keyword in query_lower for keyword in time_keywords):
            criteria['time_recent'] = True
        
        # Extract other keywords
        stop_words = {'the', 'is', 'are', 'was', 'were', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = re.findall(r'\b\w+\b', query_lower)
        criteria['keywords'] = [word for word in words if word not in stop_words and len(word) > 2]
        
        return criteria

    def calculate_prompt_match_score(self, window: LogWindow, criteria: Dict[str, Any]) -> float:
        """Calculate how well window matches the query"""
        score = 0.0
        
        for log in window.logs:
            # Service matching
            if criteria['services']:
                for service in criteria['services']:
                    if service in log.service_name:
                        score += 30.0
                        break
            
            # Route matching
            if criteria['routes'] and log.route:
                for route in criteria['routes']:
                    if route in log.route:
                        score += 25.0
                        break
            
            # Method matching
            if criteria['methods'] and log.method:
                if log.method in criteria['methods']:
                    score += 20.0
            
            # Status code matching
            if criteria['status_codes'] and log.status:
                if log.status in criteria['status_codes']:
                    score += 25.0
            
            # Keyword matching in body
            for keyword in criteria['keywords']:
                if keyword in log.body.lower():
                    score += 5.0
        
        return score

    def generate_window_summary(self, window: LogWindow) -> str:
        """Generate human-readable summary for window"""
        if not window.logs:
            return "Empty window"

        services = Counter(log.service_name for log in window.logs)
        severities = Counter(log.severity_text for log in window.logs if log.severity_text)
        status_codes = Counter(log.status for log in window.logs if log.status)
        routes = Counter(log.route for log in window.logs if log.route)
        methods = Counter(log.method for log in window.logs if log.method)

        summary_parts = []
        
        top_service = services.most_common(1)[0] if services else ('unknown', 0)
        if top_service[1] > 1:
            summary_parts.append(f"{top_service[0]} service")

        error_count = sum(1 for log in window.logs if self.error_patterns.search(log.body))
        if error_count > 0:
            summary_parts.append(f"{error_count} errors")

        if status_codes:
            status_summary = []
            for status, count in status_codes.most_common(3):
                if status >= 400:
                    status_summary.append(f"{status} ({count}x)")
            if status_summary:
                summary_parts.append(f"status: {', '.join(status_summary)}")

        if routes:
            top_route = routes.most_common(1)[0]
            if top_route[1] > 1:
                summary_parts.append(f"route: {top_route[0]} ({top_route[1]}x)")

        unique_templates = len(window.template_counts)
        total_logs = len(window.logs)
        if unique_templates < total_logs:
            repeated = total_logs - unique_templates
            summary_parts.append(f"{repeated} repeated patterns")
        
        return "; ".join(summary_parts) if summary_parts else f"{len(window.logs)} log entries"

    def filter_logs_enhanced(self, logs: List[LogEntry], query: str, max_windows: int = 20) -> List[LogWindow]:
        """Main enhanced filtering function"""
        logger.info(f"Starting enhanced filtering with {len(logs)} logs")
        
        # Hot event prefilter
        hot_logs = self.hot_event_prefilter(logs)
        if not hot_logs:
            logger.info("No hot events found, keeping top severity logs")
            # Fallback: keep logs with some severity
            hot_logs = [log for log in logs if log.severity_number and log.severity_number >= 30][:200]
        
        # Create trace/time windows
        windows = self.create_trace_windows(hot_logs)
        logger.info(f"Created {len(windows)} windows")
        
        # Template deduplication
        for window in windows:
            self.deduplicate_templates(window)
        
        # Calculate scores
        query_criteria = self.parse_query_advanced(query)
        logger.debug(f"Query criteria: {query_criteria}")
        
        for window in windows:
            window.importance_score = self.calculate_importance_score(window)
            window.prompt_match_score = self.calculate_prompt_match_score(window, query_criteria)
            window.summary = self.generate_window_summary(window)
        
        # Sort and limit
        windows.sort(key=lambda w: w.importance_score + w.prompt_match_score, reverse=True)
        final_windows = windows[:max_windows]
        
        logger.info(f"Returning {len(final_windows)} top-scored windows")
        return final_windows


def main():
    """Test the enhanced filtering system"""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    filter_system = EnhancedLogFilter()
    
    logs = filter_system.load_logs('../../sample_logs.ndjson')
    logger.info(f"Loaded {len(logs)} logs from sample_logs.ndjson")
    
    test_queries = [
        "cart service is crashing with 500 errors",
        "GET /checkout timeouts",
        "payment service user 12345 errors",
        "recent kafka failures",
        "database connection issues"
    ]
    
    for query in test_queries:
        logger.info(f"Query: '{query}'")
        
        windows = filter_system.filter_logs_enhanced(logs, query, max_windows=5)
        
        for i, window in enumerate(windows):
            logger.info(f"Window {i+1}: {len(window.logs)} logs, Score: {window.importance_score + window.prompt_match_score:.1f}")
            logger.debug(f"  Summary: {window.summary}")
            logger.debug(f"  Template Counts: {window.template_counts}")
            
            if window.logs:
                log = window.logs[0]
                logger.debug(f"  Sample: [{log.service_name}] [{log.severity_text}] {log.body[:100]}...")


if __name__ == "__main__":
    main()
