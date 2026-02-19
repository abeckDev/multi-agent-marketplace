# Running Experiment Details Page - Implementation Documentation

## Overview
This document describes the implementation of the Running Experiment Details page, which provides a live console-style view showing real-time experiment logs while an experiment is running.

## Components Implemented

### 1. TypeScript Interfaces (`src/types.ts`)
Added new interfaces for log streaming:
- `LogEntry`: Represents a single log entry with timestamp, level, message, data, and agent_id
- `LogStreamMessage`: WebSocket message format with type ('log', 'status', or 'error')

### 2. ExperimentLogStream Service (`src/services/experimentLogs.ts`)
A robust WebSocket service that:
- Connects to `/api/experiments/{name}/logs/ws` endpoint
- Handles automatic reconnection with exponential backoff
- Parses and routes log messages to appropriate handlers
- Supports graceful disconnection and cleanup
- Configurable with database connection parameters

**Key Features:**
- Maximum 5 reconnection attempts with exponential backoff (1s to 30s)
- Proper cleanup to prevent memory leaks
- Type-safe message handling
- Connection state management

### 3. LogConsole Component (`src/components/LogConsole.tsx`)
A terminal-style console component that:
- Displays logs with syntax highlighting based on log level (error, warning, info, debug)
- Auto-scrolls to bottom as new logs arrive
- Pauses auto-scroll when user manually scrolls up
- Shows timestamps with millisecond precision
- Displays agent IDs when available
- Formats and pretty-prints JSON data
- Shows log count in header

**Visual Features:**
- Dark theme (gray-900 background) for terminal feel
- Monospace font for authentic console appearance
- Color-coded log levels (red=error, yellow=warning, blue=info, green=success)
- Icon indicators for each log level
- Hover highlighting on log entries

### 4. RunningExperiment Page (`src/pages/RunningExperiment.tsx`)
Main page component that:
- Reads experiment name from URL parameter (`/dashboard/experiment/:name`)
- Establishes WebSocket connection for log streaming
- Polls experiment status every 3 seconds
- Displays live connection status indicator
- Shows experiment status (pending, running, completed, failed)
- Auto-redirects to Analyzer UI (`/?schema={name}`) when experiment completes
- Handles and displays connection errors
- Provides reconnect functionality

**State Management:**
- Stores database configuration in localStorage for persistence
- Manages WebSocket connection lifecycle
- Tracks connection state and experiment status independently

### 5. App.tsx Updates
- Added new route: `/dashboard/experiment/:name` → `RunningExperiment`
- Created `RunningExperimentWithNav` wrapper with navigation header
- Maintains consistent navigation pattern with other pages

### 6. Dashboard Updates (`src/pages/Dashboard.tsx`)
- Added "View Logs" button for pending/running experiments
- Saves database configuration to localStorage on experiment launch
- Links directly to running experiment page
- Visual indicator (Eye icon) for accessing live logs

## User Flow

1. **Launch Experiment**: User launches experiment from Dashboard
2. **Access Logs**: Click "View Logs" button on running experiment
3. **View Logs**: See live logs streaming in terminal-style console
4. **Monitor Status**: Watch real-time status updates in header
5. **Auto-Redirect**: Upon completion, automatically redirected to Analyzer UI

## Error Handling

### WebSocket Errors
- Connection failures display error banner
- Provides "Reconnect" button for manual retry
- Automatic reconnection up to 5 attempts
- Clear error messages for debugging

### Network Issues
- Graceful handling of disconnects
- Visual indicator shows connection state
- Continues polling status even if WebSocket fails

### Invalid Experiment
- Validates experiment name parameter
- Shows clear error if name is missing
- Backend validates schema name for SQL injection prevention

## Technical Details

### WebSocket Protocol
- Endpoint: `ws://localhost:8000/api/experiments/{name}/logs/ws`
- Query parameters: `since`, `host`, `port`, `database`, `user`, `password`
- Message format: JSON with `type` field ('log', 'status', 'error')

### Database Configuration
Stored in localStorage as:
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "marketplace",
  "user": "postgres",
  "password": "postgres"
}
```

### Auto-Scroll Behavior
- Automatically scrolls to bottom on new logs
- Pauses when user scrolls up (within 50px of bottom triggers auto-scroll)
- Shows indicator when auto-scroll is paused
- Resumes after 1 second of no manual scrolling

## Accessibility

- Semantic HTML structure
- ARIA labels on interactive elements
- Keyboard navigation support via React Router
- Clear visual feedback for all states
- High contrast color scheme

## Responsiveness

- Flexbox layout adapts to different screen sizes
- Console height calculated as `calc(100vh-12rem)` for full viewport usage
- Responsive header with appropriate spacing
- Mobile-friendly navigation

## Testing Strategy

### Manual Testing Checklist
1. ✅ Build and type-check passes
2. ✅ Linting passes without errors
3. ⏳ Launch experiment and access logs page
4. ⏳ Verify WebSocket connection established
5. ⏳ Verify logs stream in real-time
6. ⏳ Test auto-scroll behavior
7. ⏳ Test manual scroll pausing auto-scroll
8. ⏳ Verify status updates appear correctly
9. ⏳ Test auto-redirect on completion
10. ⏳ Test error handling and reconnection
11. ⏳ Test with slow/interrupted network
12. ⏳ Verify persistence of DB config

### Integration Testing
Since the visualizer doesn't have automated tests, manual integration testing should cover:
- WebSocket connection with backend
- Status polling
- Auto-redirect flow
- Error scenarios
- Multiple concurrent experiments

## Browser Compatibility

Built with:
- React 18.3.1
- TypeScript 5.6.2
- Vite 6.4.1
- React Router DOM 7.13.0

Should work on all modern browsers supporting:
- ES6+ JavaScript
- WebSocket API
- localStorage API
- CSS Grid and Flexbox

## Performance Considerations

1. **WebSocket Efficiency**: Single connection per experiment
2. **Log Buffering**: Logs accumulated in React state
3. **Polling Interval**: 3 seconds for status (balanced trade-off)
4. **Memory**: Old logs not automatically pruned (consider for very long experiments)
5. **Reconnection Backoff**: Prevents overwhelming server during issues

## Future Enhancements

Potential improvements (not in scope):
- Log filtering by level or agent
- Log search functionality
- Download logs as file
- Pause/resume log streaming
- Log retention limits for long-running experiments
- WebSocket compression for high-volume logs
- Multiple experiment monitoring in one view

## Security Considerations

1. **Schema Name Validation**: Backend validates experiment names to prevent SQL injection
2. **Database Credentials**: Stored in localStorage (not ideal for production, but acceptable for demo)
3. **WebSocket Authentication**: None currently (add JWT tokens for production)
4. **XSS Prevention**: React automatically escapes content

## Related Files

- Backend WebSocket endpoint: `packages/magentic-marketplace/src/magentic_marketplace/api/main.py:628-817`
- API models: `packages/magentic-marketplace/src/magentic_marketplace/api/models.py:88-122`
- Build output: `packages/magentic-marketplace/src/magentic_marketplace/ui/static/`
