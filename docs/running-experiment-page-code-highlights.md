# Running Experiment Page - Code Highlights

## Key Code Snippets

### 1. WebSocket Connection with Auto-Reconnection

```typescript
// src/services/experimentLogs.ts
export class ExperimentLogStream {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second

  connect(): void {
    const wsUrl = `${WS_BASE_URL}/api/experiments/${encodeURIComponent(
      this.options.experimentName
    )}/logs/ws${queryString}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onmessage = (event) => {
      const message: LogStreamMessage = JSON.parse(event.data);
      
      switch (message.type) {
        case "log":
          this.options.onLog?.(message.log);
          break;
        case "status":
          this.options.onStatus?.(message.status);
          break;
        case "error":
          this.options.onError?.(message.error);
          break;
      }
    };

    this.ws.onclose = () => {
      if (!this.intentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect(): void {
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectAttempts++;
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Cap at 30 seconds
      this.connect();
    }, this.reconnectDelay);
  }
}
```

### 2. Terminal-Style Log Console with Auto-Scroll

```typescript
// src/components/LogConsole.tsx
function LogConsole({ logs, autoScroll = true }: LogConsoleProps) {
  const consoleRef = useRef<HTMLDivElement>(null);
  const isUserScrolling = useRef(false);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && consoleRef.current && !isUserScrolling.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  // Detect when user manually scrolls
  const handleScroll = () => {
    if (!consoleRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = consoleRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    isUserScrolling.current = !isAtBottom;
  };

  const getLevelColor = (level: string) => {
    const levelLower = level.toLowerCase();
    switch (levelLower) {
      case "error": return "text-red-400";
      case "warning": return "text-yellow-400";
      case "success": return "text-green-400";
      default: return "text-blue-400";
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-gray-700 bg-gray-900">
      <div ref={consoleRef} onScroll={handleScroll} className="flex-1 overflow-y-auto p-4 font-mono text-xs">
        {logs.map((log, index) => (
          <div key={`${log.timestamp}-${index}`} className="group rounded px-2 py-1">
            <div className="flex items-start gap-2">
              <span className="text-gray-500">[{formatTimestamp(log.timestamp)}]</span>
              <span className={getLevelColor(log.level)}>{log.level}</span>
              {log.agent_id && <span className="text-purple-400">[{log.agent_id}]</span>}
              <span className="text-gray-300">{log.message}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 3. Running Experiment Page with Status Monitoring

```typescript
// src/pages/RunningExperiment.tsx
function RunningExperiment() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [experimentStatus, setExperimentStatus] = useState<string | null>(null);

  useEffect(() => {
    const stream = createLogStream({
      experimentName: name!,
      onLog: (log) => {
        setLogs((prev) => [...prev, log]);
      },
      onStatus: (newStatus) => {
        setExperimentStatus(newStatus);
        
        // Auto-redirect when completed
        if (newStatus === "completed") {
          setTimeout(() => {
            navigate(`/?schema=${encodeURIComponent(name!)}`);
          }, 2000);
        }
      },
      onError: (err) => {
        setError(err);
      },
    });

    // Poll status every 3 seconds
    const interval = setInterval(pollStatus, 3000);

    return () => {
      stream.close();
      clearInterval(interval);
    };
  }, [name, navigate]);

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header with status */}
      <div className="border-b bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <h1>{name}</h1>
          <div className="flex items-center gap-2">
            {getStatusIcon(experimentStatus)}
            <span>{experimentStatus || "Unknown"}</span>
          </div>
        </div>
      </div>

      {/* Log Console */}
      <div className="flex-1 p-6">
        <LogConsole logs={logs} autoScroll={true} />
      </div>

      {/* Completion Banner */}
      {experimentStatus === "completed" && (
        <div className="p-4 bg-green-50 border-green-200">
          <p>Experiment Completed - Redirecting to analyzer view...</p>
        </div>
      )}
    </div>
  );
}
```

### 4. Dashboard Integration

```typescript
// src/pages/Dashboard.tsx
function Dashboard() {
  const handleLaunchExperiment = async (e: React.FormEvent) => {
    // Save DB config to localStorage for log streaming
    localStorage.setItem(
      "experimentDbConfig",
      JSON.stringify({
        host: postgresHost,
        port: postgresPort,
        database: "marketplace",
        user: "postgres",
        password: postgresPassword,
      })
    );

    const status = await orchestratorService.createExperiment(config);
    setRunningExperiments((prev) => new Map(prev).set(status.name, status));
  };

  return (
    <div>
      {/* Running Experiments */}
      {Array.from(runningExperiments.entries()).map(([name, status]) => (
        <div key={name}>
          <span>{name}</span>
          <span>{status.status}</span>
          {(status.status === "pending" || status.status === "running") && (
            <Link to={`/dashboard/experiment/${encodeURIComponent(name)}`}>
              <Eye className="h-3 w-3" />
              View Logs
            </Link>
          )}
        </div>
      ))}
    </div>
  );
}
```

### 5. TypeScript Interfaces

```typescript
// src/types.ts
export interface LogEntry {
  timestamp: string;
  level: string;
  message: string | null;
  data: Record<string, unknown> | null;
  agent_id: string | null;
}

export interface LogStreamMessage {
  type: "log" | "status" | "error";
  log?: LogEntry;
  status?: string;
  error?: string;
}
```

### 6. Route Configuration

```typescript
// src/App.tsx
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<VisualizerWithNav />} />
        <Route path="/dashboard" element={<DashboardWithNav />} />
        <Route path="/dashboard/experiment/:name" element={<RunningExperimentWithNav />} />
      </Routes>
    </BrowserRouter>
  );
}

function RunningExperimentWithNav() {
  return (
    <>
      <nav className="border-b border-gray-200 bg-white">
        <div className="px-8 py-3">
          <Link to="/dashboard">← Back to Dashboard</Link>
        </div>
      </nav>
      <RunningExperiment />
    </>
  );
}
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User Flow                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │    Dashboard     │
                    │  /dashboard      │
                    └────────┬─────────┘
                             │ Launch Experiment
                             │ Click "View Logs"
                             ▼
              ┌──────────────────────────────┐
              │   Running Experiment Page    │
              │ /dashboard/experiment/:name  │
              └──────────┬───────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌──────────────┐  ┌──────────┐  ┌─────────────┐
│ WebSocket    │  │ Status   │  │ LocalStorage│
│ Log Stream   │  │ Polling  │  │ DB Config   │
└──────────────┘  └──────────┘  └─────────────┘
         │               │               
         │               │               
         ▼               ▼               
    ┌────────────────────────────┐
    │      LogConsole            │
    │   (Terminal Display)       │
    └────────────────────────────┘
                 │
                 │ On Completion
                 ▼
         ┌──────────────┐
         │  Analyzer UI │
         │  /?schema=X  │
         └──────────────┘
```

## Component Hierarchy

```
App
├── Routes
│   ├── / → VisualizerWithNav
│   │   └── Visualizer
│   ├── /dashboard → DashboardWithNav
│   │   └── Dashboard
│   └── /dashboard/experiment/:name → RunningExperimentWithNav
│       └── RunningExperiment
│           ├── ExperimentLogStream (service)
│           └── LogConsole (component)
```

## Data Flow

```
1. User launches experiment from Dashboard
   └─> Dashboard saves DB config to localStorage
   └─> Experiment status tracked in runningExperiments Map

2. User clicks "View Logs"
   └─> Navigate to /dashboard/experiment/:name
   └─> RunningExperiment reads DB config from localStorage

3. RunningExperiment establishes WebSocket connection
   └─> ExperimentLogStream connects to backend
   └─> Messages routed to onLog/onStatus/onError handlers
   └─> Auto-reconnection on disconnect (exponential backoff)

4. Logs displayed in LogConsole
   └─> Color-coded by level
   └─> Auto-scroll to bottom
   └─> Pause on manual scroll

5. Status polling every 3 seconds
   └─> Updates experiment status in UI
   └─> Detects completion

6. On completion
   └─> Show completion banner
   └─> Auto-redirect to /?schema={name} after 2 seconds
```

## Key Features Implementation

### Auto-Scroll with Pause Detection
- Uses `useRef` to track user scrolling
- Detects when user is within 50px of bottom
- Shows indicator when paused
- Resumes after 1 second of no manual scrolling

### WebSocket Reconnection
- Exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s (max)
- Maximum 5 reconnection attempts
- Cleans up on unmount to prevent memory leaks
- Intentional close flag prevents unwanted reconnections

### Database Config Persistence
- Saved to localStorage on experiment launch
- Key: `experimentDbConfig`
- Format: `{ host, port, database, user, password }`
- Used by RunningExperiment page for WebSocket connection

### Status Monitoring
- Dual approach: WebSocket status messages + polling
- Polling every 3 seconds as fallback
- Independent of WebSocket connection
- Ensures status updates even if WebSocket fails

### Error Handling
- Connection errors: Show banner with reconnect button
- Invalid experiment: Show error page
- WebSocket disconnect: Automatic reconnection
- Maximum attempts reached: Show clear message

## Styling Approach

### Terminal Theme
- Dark background: `bg-gray-900`
- Monospace font: Monaco, Menlo, Ubuntu Mono
- Console border: `border-gray-700`
- Header: `bg-gray-800`

### Color Coding
- Error: `text-red-400` + `XCircle` icon
- Warning: `text-yellow-400` + `AlertCircle` icon
- Info: `text-blue-400` + `Info` icon
- Success: `text-green-400` + `CheckCircle` icon
- Debug: `text-gray-500`
- Timestamp: `text-gray-500`
- Agent ID: `text-purple-400`

### Responsive Layout
- Flexbox for vertical layout
- Console height: `calc(100vh - 12rem)`
- Max width: `max-w-7xl`
- Padding: Consistent 4-6 spacing units
