import {
  AlertCircle,
  CheckCircle,
  Clock,
  Loader2,
  RefreshCw,
  Terminal,
  WifiOff,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import LogConsole from "../components/LogConsole";
import { createLogStream, ExperimentLogStream } from "../services/experimentLogs";
import { orchestratorService } from "../services/orchestrator";
import { LogEntry } from "../types";

function RunningExperiment() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<string>("connecting");
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [experimentStatus, setExperimentStatus] = useState<string | null>(null);

  const logStreamRef = useRef<ExperimentLogStream | null>(null);
  const statusPollInterval = useRef<number | null>(null);

  // Get database config from localStorage or use defaults
  const getDbConfig = () => {
    try {
      const saved = localStorage.getItem("experimentDbConfig");
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.error("Failed to load DB config:", e);
    }
    return {
      host: "localhost",
      port: 5432,
      database: "marketplace",
      user: "postgres",
      password: "postgres",
    };
  };

  const dbConfig = getDbConfig();

  // Poll experiment status
  const pollStatus = useCallback(async () => {
    if (!name) return;

    try {
      const statusData = await orchestratorService.getExperimentStatus(name);
      setExperimentStatus(statusData.status);

      // Auto-redirect when completed
      if (statusData.status === "completed") {
        // Wait a moment to show final logs
        setTimeout(() => {
          navigate(`/?schema=${encodeURIComponent(name)}`);
        }, 2000);
      }
    } catch (err) {
      console.error("Failed to poll status:", err);
    }
  }, [name, navigate]);

  // Set up WebSocket connection
  useEffect(() => {
    if (!name) {
      setError("No experiment name provided");
      return;
    }

    setStatus("connecting");

    const stream = createLogStream({
      experimentName: name,
      host: dbConfig.host,
      port: dbConfig.port,
      database: dbConfig.database,
      user: dbConfig.user,
      password: dbConfig.password,
      onLog: (log) => {
        setLogs((prev) => [...prev, log]);
      },
      onStatus: (newStatus) => {
        setExperimentStatus(newStatus);
        setStatus("connected");

        // Auto-redirect when completed
        if (newStatus === "completed") {
          setTimeout(() => {
            navigate(`/?schema=${encodeURIComponent(name)}`);
          }, 2000);
        }
      },
      onError: (err) => {
        setError(err);
        setStatus("error");
      },
      onConnect: () => {
        setIsConnected(true);
        setStatus("connected");
        setError(null);
      },
      onDisconnect: () => {
        setIsConnected(false);
        setStatus("disconnected");
      },
    });

    logStreamRef.current = stream;

    // Start polling status
    pollStatus();
    statusPollInterval.current = window.setInterval(pollStatus, 3000);

    // Cleanup
    return () => {
      if (logStreamRef.current) {
        logStreamRef.current.close();
      }
      if (statusPollInterval.current) {
        clearInterval(statusPollInterval.current);
      }
    };
  }, [name, navigate, dbConfig, pollStatus]);

  const handleReconnect = () => {
    setError(null);
    if (logStreamRef.current) {
      logStreamRef.current.close();
    }
    // Force re-mount by clearing and re-creating stream
    window.location.reload();
  };

  const getStatusIcon = (currentStatus: string | null) => {
    if (!currentStatus) return <Clock className="h-5 w-5 animate-pulse text-gray-400" />;

    switch (currentStatus) {
      case "pending":
        return <Clock className="h-5 w-5 animate-pulse text-yellow-500" />;
      case "running":
        return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
      case "completed":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "failed":
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getConnectionStatus = () => {
    if (error) {
      return (
        <div className="flex items-center gap-2 text-red-600">
          <XCircle className="h-4 w-4" />
          <span className="text-sm font-medium">Error</span>
        </div>
      );
    }

    if (status === "connecting") {
      return (
        <div className="flex items-center gap-2 text-yellow-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm font-medium">Connecting...</span>
        </div>
      );
    }

    if (status === "disconnected") {
      return (
        <div className="flex items-center gap-2 text-orange-600">
          <WifiOff className="h-4 w-4" />
          <span className="text-sm font-medium">Disconnected</span>
        </div>
      );
    }

    if (isConnected) {
      return (
        <div className="flex items-center gap-2 text-green-600">
          <div className="h-2 w-2 animate-pulse rounded-full bg-green-600"></div>
          <span className="text-sm font-medium">Live</span>
        </div>
      );
    }

    return null;
  };

  if (!name) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 to-gray-100">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6">
          <AlertCircle className="mx-auto mb-4 h-12 w-12 text-red-500" />
          <h2 className="mb-2 text-xl font-bold text-red-800">Invalid Request</h2>
          <p className="text-red-700">No experiment name provided</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-brand-50 to-gray-50">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4 shadow-sm">
        <div className="mx-auto max-w-7xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Terminal className="h-6 w-6 text-brand-500" />
              <div>
                <h1 className="text-xl font-bold text-gray-800">Running Experiment</h1>
                <p className="text-sm text-gray-600">{name}</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Connection Status */}
              {getConnectionStatus()}

              {/* Experiment Status */}
              <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-4 py-2">
                {getStatusIcon(experimentStatus)}
                <div className="text-left">
                  <div className="text-xs text-gray-500">Status</div>
                  <div className="text-sm font-semibold capitalize text-gray-800">
                    {experimentStatus || "Unknown"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6">
        <div className="mx-auto h-full max-w-7xl">
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <XCircle className="h-5 w-5 flex-shrink-0 text-red-500" />
                  <div>
                    <h3 className="font-semibold text-red-800">Connection Error</h3>
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
                <button
                  onClick={handleReconnect}
                  className="flex items-center gap-2 rounded bg-red-600 px-3 py-1 text-sm font-semibold text-white hover:bg-red-700"
                >
                  <RefreshCw className="h-4 w-4" />
                  Reconnect
                </button>
              </div>
            </div>
          )}

          <div className="h-[calc(100vh-12rem)]">
            <LogConsole logs={logs} autoScroll={true} />
          </div>

          {/* Footer Info */}
          {experimentStatus === "completed" && (
            <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-4">
              <div className="flex items-center gap-3">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <div>
                  <h3 className="font-semibold text-green-800">Experiment Completed</h3>
                  <p className="text-sm text-green-700">
                    Redirecting to analyzer view in a moment...
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default RunningExperiment;
