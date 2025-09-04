# Relvy Take-Home Assignment: Log Analysis Application

Build a simple log analysis app where users can upload a JSON log file and prompt them with incident-related issues (e.g., "cart service is crashing, check logs"). Ideally a set of logs should be filtered out based on the json keys available and the user prompt (e.g. get all logs for cart service). The filtered set of logs should then be analyzed via LLM for any relevance to the incident.

## Requirements
- **Frontend:** React app with file upload and prompt input
- **Backend:** API server that (We use python, feel free to use whatever you are comfortable in):
  1. Parses uploaded JSON logs (format provided below)
  2. Filters a set of logs based on user prompt
  3. Analyzes filtered logs using LLM for relevance and selects a set of logs to be highlighted
- Display LLM usage cost at the end of each analysis

## Sample Log Format
```json
{"clusterUid":"111de5db-ce60-429a-9b8b-d7e9652ef3c2","containerId":"969088119e70a0ccaee0ce92951f3cc715455c3cd9709383df0be592876de9cf","containerName":"frauddetectionservice","log":"2025-09-02 23:12:41 - frauddetectionservice - Consumed record with orderId: 53267606-8852-11f0-9338-5e423e9fa0b8","namespace":"oteldemo","podName":"oteldemo-frauddetectionservice-7c68f5d95-lnndh","stream":"stdout","timestamp":"1756854761248507718"}
```

## Technical Details
- Time limit: Don't spend more than 2-3 hours. We are looking for a basic app as a starting point of our discussion.
- Focus on core functionality over polish
- Track and display LLM API costs

## Deliverables
- GitHub repo OR zip file with frontend and backend code (dont include your LLM key)
- Clear setup and run instructions
- Brief documentation of filtering and LLM analysis approach

Feel free to use any AI tools of your choice. Again do not spend more than 2-3 hours. This will be our starting point for our follow up discussion where we will discuss the challenges of implementing such a solution for enterprise use case.