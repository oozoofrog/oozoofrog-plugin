---
type: tool_order
before: { tool: Bash, input_match: 'paginate\(|repro|from pager import' }
after: { tool: Edit, input_match: 'pager\.py' }
---
