#!/usr/bin/env python3
"""
Focused test of enhanced log filtering with concise output for LLM processing
"""

import logging
import json
from enhanced_log_filter import EnhancedLogFilter

# Configure logging for developer info
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Test with single query and only print LLM output"""
    filter_system = EnhancedLogFilter()
    
    # Load logs
    logs = filter_system.load_logs('../../sample_logs.ndjson')
    logger.info(f"Loaded {len(logs)} logs from sample_logs.ndjson")
    
    # Single focused query
    query = "cart service errors and timeouts"
    logger.info(f"Processing query: '{query}'")
    
    # Get filtered windows (this will have internal logging)
    windows = filter_system.filter_logs_enhanced(logs, query, max_windows=5)
    
    logger.info(f"Generated {len(windows)} windows for LLM processing")
    
    # Prepare concise data for LLM
    llm_data = []
    total_logs = 0
    
    for window in windows:
        window_data = {
            'summary': window.summary,
            'logs': []
        }
        
        # Only include the most important logs from each window
        important_logs = sorted(window.logs, key=lambda x: (x.severity_number or 0), reverse=True)[:3]
        total_logs += len(important_logs)
        
        for log in important_logs:
            window_data['logs'].append({
                'service': log.service_name,
                'severity': log.severity_text or 'UNKNOWN',
                'message': log.body[:150] + ('...' if len(log.body) > 150 else ''),
                'status': log.status,
                'route': log.route,
                'timestamp': log.timestamp_raw
            })
        
        llm_data.append(window_data)
    
    logger.info(f"Prepared {len(llm_data)} windows with {total_logs} logs for LLM")
    logger.info(f"Cost reduction: {(1 - total_logs/len(logs))*100:.1f}%")
    
    # ONLY PRINT WHAT LLM WILL RECEIVE
    print(json.dumps(llm_data, indent=2))

if __name__ == "__main__":
    main()
