# Manual Test Plan: Running Experiment Details Page

## Prerequisites
- Backend server running with WebSocket support
- PostgreSQL database accessible
- At least one dataset available for experiments
- Browser with WebSocket and localStorage support

## Test Environment Setup

1. Start the unified server:
   ```bash
   magentic-marketplace serve --host localhost --port 8000
   ```

2. Ensure PostgreSQL is running:
   ```bash
   docker-compose up -d postgres
   ```

3. Start the frontend dev server:
   ```bash
   cd packages/marketplace-visualizer
   npm run dev
   ```

## Test Cases

### TC-01: Navigate to Running Experiment Page
**Objective**: Verify user can access the running experiment page

**Steps**:
1. Navigate to `http://localhost:5173/dashboard`
2. Launch a new experiment
3. Click "View Logs" button on the running experiment

**Expected Results**:
- ✅ URL changes to `/dashboard/experiment/{experiment-name}`
- ✅ Page loads without errors
- ✅ Navigation header shows "Back to Dashboard" link
- ✅ Page header displays experiment name
- ✅ Connection status indicator appears

### TC-02: WebSocket Connection Establishment
**Objective**: Verify WebSocket connection is established successfully

**Steps**:
1. Open browser DevTools → Network tab → WS filter
2. Navigate to running experiment page
3. Observe WebSocket connection

**Expected Results**:
- ✅ WebSocket connection to `/api/experiments/{name}/logs/ws` is established
- ✅ Connection status shows "Live" with green indicator
- ✅ No console errors appear

### TC-03: Log Streaming
**Objective**: Verify logs stream in real-time

**Steps**:
1. Navigate to running experiment page
2. Observe the log console
3. Wait for logs to appear

**Expected Results**:
- ✅ Logs appear in the console as they are generated
- ✅ Timestamps are displayed correctly
- ✅ Log levels (INFO, DEBUG, WARNING, ERROR) are color-coded
- ✅ Agent IDs are displayed when available
- ✅ Console auto-scrolls to show newest logs

### TC-04: Auto-Scroll Behavior
**Objective**: Verify auto-scroll works correctly and can be paused

**Steps**:
1. Navigate to running experiment page with active logs
2. Let logs accumulate to scroll
3. Scroll up manually
4. Wait 1 second
5. Observe behavior

**Expected Results**:
- ✅ Console auto-scrolls to bottom as new logs arrive
- ✅ Auto-scroll pauses when user scrolls up
- ✅ Yellow indicator appears: "Auto-scroll paused. Scroll to bottom to resume."
- ✅ Auto-scroll resumes after 1 second of no manual scrolling
- ✅ Auto-scroll resumes immediately when scrolling to bottom

### TC-05: Experiment Status Display
**Objective**: Verify experiment status is displayed and updated

**Steps**:
1. Navigate to running experiment page
2. Observe status indicator in header
3. Wait for status changes

**Expected Results**:
- ✅ Initial status displays correctly (pending/running)
- ✅ Status icon matches status (clock, spinner, check, X)
- ✅ Status text is capitalized properly
- ✅ Status updates every 3 seconds via polling

### TC-06: Auto-Redirect on Completion
**Objective**: Verify auto-redirect to Analyzer UI when experiment completes

**Steps**:
1. Navigate to running experiment page for a nearly-complete experiment
2. Wait for experiment to complete
3. Observe completion message and redirect

**Expected Results**:
- ✅ Green completion banner appears: "Experiment Completed"
- ✅ Message shows: "Redirecting to analyzer view in a moment..."
- ✅ After 2 seconds, browser redirects to `/?schema={experiment-name}`
- ✅ Analyzer UI loads with experiment data

### TC-07: Connection Error Handling
**Objective**: Verify error handling when WebSocket connection fails

**Steps**:
1. Stop the backend server
2. Navigate to running experiment page
3. Observe error handling
4. Restart backend
5. Click "Reconnect" button

**Expected Results**:
- ✅ Red error banner appears with connection error message
- ✅ Connection status shows "Error" or "Disconnected"
- ✅ "Reconnect" button is visible and functional
- ✅ Clicking reconnect re-establishes connection
- ✅ Logs resume streaming after reconnection

### TC-08: Automatic Reconnection
**Objective**: Verify automatic reconnection with exponential backoff

**Steps**:
1. Navigate to running experiment page
2. Open browser DevTools → Network tab → WS filter
3. Temporarily block WebSocket connections (browser DevTools)
4. Observe reconnection attempts
5. Unblock connections

**Expected Results**:
- ✅ Connection attempts made automatically
- ✅ Delay increases between attempts (1s, 2s, 4s, 8s, 16s, 30s max)
- ✅ Maximum 5 reconnection attempts
- ✅ Error message after max attempts: "Maximum reconnection attempts reached"
- ✅ Connection succeeds when network is restored

### TC-09: Invalid Experiment Name
**Objective**: Verify handling of invalid experiment name

**Steps**:
1. Navigate to `/dashboard/experiment/invalid_name_that_doesnt_exist`
2. Observe error handling

**Expected Results**:
- ✅ Page loads without crashing
- ✅ Error message indicates experiment not found
- ✅ No logs are displayed
- ✅ Connection status shows error

### TC-10: Database Configuration Persistence
**Objective**: Verify DB config is saved and used correctly

**Steps**:
1. Navigate to Dashboard
2. Set PostgreSQL configuration (host, port, password)
3. Launch experiment
4. Click "View Logs"
5. Open browser DevTools → Application → Local Storage
6. Verify `experimentDbConfig` key exists

**Expected Results**:
- ✅ DB config saved to localStorage on experiment launch
- ✅ Config includes: host, port, database, user, password
- ✅ RunningExperiment page uses saved config for WebSocket connection
- ✅ Config persists across page reloads

### TC-11: Multiple Log Levels
**Objective**: Verify different log levels are displayed correctly

**Steps**:
1. Navigate to running experiment page
2. Observe logs of different levels (INFO, DEBUG, WARNING, ERROR)
3. Compare visual styling

**Expected Results**:
- ✅ INFO logs: Blue icon and text
- ✅ DEBUG logs: Gray icon and text
- ✅ WARNING logs: Yellow icon and text
- ✅ ERROR logs: Red icon and text
- ✅ SUCCESS logs: Green icon and text
- ✅ Icons match log level (Info, AlertCircle, XCircle, CheckCircle)

### TC-12: Log Data Formatting
**Objective**: Verify additional log data is formatted correctly

**Steps**:
1. Navigate to running experiment page
2. Find logs with additional data fields
3. Observe formatting

**Expected Results**:
- ✅ Additional data is displayed below log message
- ✅ JSON data is pretty-printed with indentation
- ✅ Data is indented and gray-colored
- ✅ Long data doesn't break layout

### TC-13: Back Navigation
**Objective**: Verify back to dashboard navigation works

**Steps**:
1. Navigate to running experiment page
2. Click "← Back to Dashboard" in navigation header
3. Verify navigation

**Expected Results**:
- ✅ Browser navigates to `/dashboard`
- ✅ Dashboard loads with experiment list
- ✅ WebSocket connection on running experiment page is closed cleanly

### TC-14: Direct URL Access
**Objective**: Verify page works when accessed via direct URL

**Steps**:
1. Copy running experiment URL
2. Open new browser tab
3. Paste URL and navigate

**Expected Results**:
- ✅ Page loads correctly
- ✅ DB config loaded from localStorage
- ✅ WebSocket connection established
- ✅ Logs stream correctly
- ✅ No errors in console

### TC-15: Browser Compatibility
**Objective**: Verify page works across different browsers

**Browsers to Test**:
- Chrome/Edge (Chromium)
- Firefox
- Safari (if available)

**Steps**:
1. Navigate to running experiment page in each browser
2. Verify all functionality

**Expected Results**:
- ✅ Page renders correctly in all browsers
- ✅ WebSocket connection works
- ✅ Auto-scroll behavior consistent
- ✅ Styling appears correctly
- ✅ No browser-specific errors

## Performance Tests

### PT-01: High Volume Log Streaming
**Objective**: Verify performance with high log volume

**Steps**:
1. Run experiment that generates many logs per second
2. Observe console performance
3. Monitor browser memory usage

**Expected Results**:
- ✅ Logs render without significant lag
- ✅ Auto-scroll remains smooth
- ✅ Memory usage is reasonable (consider pagination for production)
- ✅ No UI freezing or stuttering

### PT-02: Long Running Experiment
**Objective**: Verify performance over extended time

**Steps**:
1. Let experiment run for 10+ minutes
2. Observe page behavior
3. Check for memory leaks

**Expected Results**:
- ✅ Page remains responsive
- ✅ WebSocket connection stable
- ✅ No memory leaks (check DevTools Memory profiler)
- ✅ Status polling continues

## Regression Tests

### RT-01: Existing Dashboard Functionality
**Objective**: Verify changes don't break dashboard

**Steps**:
1. Navigate to Dashboard
2. Test all existing features

**Expected Results**:
- ✅ Dataset selection works
- ✅ Experiment launching works
- ✅ Running experiments display
- ✅ Completed experiments display
- ✅ "View" buttons for completed experiments work

### RT-02: Existing Visualizer Functionality
**Objective**: Verify changes don't break visualizer

**Steps**:
1. Navigate to Visualizer with schema parameter
2. Test visualization features

**Expected Results**:
- ✅ Visualizer loads correctly
- ✅ Customer and business data displays
- ✅ Messages and conversations work
- ✅ Analytics display correctly

## Test Results Summary

| Test Case | Status | Notes |
|-----------|--------|-------|
| TC-01 | ⏳ Pending | Requires running backend |
| TC-02 | ⏳ Pending | Requires running backend |
| TC-03 | ⏳ Pending | Requires running backend |
| TC-04 | ⏳ Pending | Requires running backend |
| TC-05 | ⏳ Pending | Requires running backend |
| TC-06 | ⏳ Pending | Requires running backend |
| TC-07 | ⏳ Pending | Requires running backend |
| TC-08 | ⏳ Pending | Requires running backend |
| TC-09 | ⏳ Pending | Requires running backend |
| TC-10 | ⏳ Pending | Requires running backend |
| TC-11 | ⏳ Pending | Requires running backend |
| TC-12 | ⏳ Pending | Requires running backend |
| TC-13 | ⏳ Pending | Requires running backend |
| TC-14 | ⏳ Pending | Requires running backend |
| TC-15 | ⏳ Pending | Requires multiple browsers |
| PT-01 | ⏳ Pending | Requires stress test scenario |
| PT-02 | ⏳ Pending | Requires long-running test |
| RT-01 | ⏳ Pending | Can be tested with mock data |
| RT-02 | ⏳ Pending | Can be tested with mock data |

## Notes for Future Testing

- Consider adding automated WebSocket tests with mock server
- Consider adding Playwright e2e tests for full user flows
- Consider adding Jest/Vitest unit tests for components
- Performance testing should be done with realistic experiment data
- Security testing should include SQL injection attempts on experiment names
