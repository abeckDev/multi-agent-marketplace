import { AlertCircle, CheckCircle, Clock, Loader2, Terminal, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import LogConsole from "../components/LogConsole";
import { orchestratorService } from "../services/orchestrator";
import { LogEntry } from "../services/orchestrator";

function RunningExperiment() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [experimentStatus, setExperimentStatus] = useState<string | null>(null);

  const pollTimer = useRef<number | null>(null);
  const lastTimestamp = useRef<string | null>(null);
  const isMounted = useRef(true);

  // Get database config from localStorage or use defaults
  const getDbConfig = useCallback(() => {
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
  }, []);

  // Poll logs and status
  const poll = useCallback(async () => {
    if (!name || !isMounted.current) return;

    const dbConfig = getDbConfig();

    try {
      // Poll experiment status
      const statusData = await orchestratorService.getExperimentStatus(name);
      if (!isMounted.current) return;
      setExperimentStatus(statusData.status);

      // Poll logs
      const logsData = await orchestratorService.getExperimentLogs(name, {
        since: lastTimestamp.current || undefined,
        limit: 200,
        host: dbConfig.host,
        port: dbConfig.port,
        database: dbConfig.database,
        user: dbConfig.user,
        password: dbConfig.password,
      });
      if (!isMounted.current) return;

      if (logsData.logs.length > 0) {
        setLogs((prev) => [...prev, ...logsData.logs]);
        // Track the last timestamp for incremental fetching
        lastTimestamp.current = logsData.logs[logsData.logs.length - 1].timestamp;
      }

      setError(null);

      // Auto-redirect when completed
      if (statusData.status === "completed") {
        setTimeout(() => {
          if (isMounted.current) {
            navigate(`/?schema=${encodeURIComponent(name)}`);
          }
        }, 3000);
        return; // Stop polling
      }

      // Stop polling on failure
      if (statusData.status === "failed") {
        return;
      }
    } catch (err) {
      if (!isMounted.current) return;
      const msg = err instanceof Error ? err.message : "Failed to fetch logs";
      setError(msg);
    }

    // Schedule next poll
    if (isMounted.current) {
      pollTimer.current = window.setTimeout(poll, 2000);
    }
  }, [name, navigate, getDbConfig]);

  // Start polling on mount
  useEffect(() => {
    isMounted.current = true;
    poll();

    return () => {
      isMounted.current = false;
      if (pollTimer.current) {
        clearTimeout(pollTimer.current);
      }
    };
  }, [poll]);

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

            {/* Experiment Status */}
            <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-4 py-2">
              {getStatusIcon(experimentStatus)}
              <div className="text-left">
                <div className="text-xs text-gray-500">Status</div>
                <div className="text-sm font-semibold capitalize text-gray-800">
                  {experimentStatus || "Loading..."}
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
              <div className="flex items-start gap-3">
                <XCircle className="h-5 w-5 flex-shrink-0 text-red-500" />
                <div>
                  <h3 className="font-semibold text-red-800">Error</h3>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <div className="h-[calc(100vh-12rem)]">
            <LogConsole logs={logs} autoScroll={true} />
          </div>

          {/* Completion banner */}
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

          {/* Failure banner */}
          {experimentStatus === "failed" && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
              <div className="flex items-center gap-3">
                <XCircle className="h-5 w-5 text-red-500" />
                <div>
                  <h3 className="font-semibold text-red-800">Experiment Failed</h3>
                  <p className="text-sm text-red-700">
                    Check the logs above for details on the failure.
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
