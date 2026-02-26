import { AlertCircle, CheckCircle, Info, Terminal, XCircle } from "lucide-react";
import { useEffect, useRef } from "react";

import { LogEntry } from "../services/orchestrator";

interface LogConsoleProps {
  logs: LogEntry[];
  autoScroll?: boolean;
}

function LogConsole({ logs, autoScroll = true }: LogConsoleProps) {
  const consoleRef = useRef<HTMLDivElement>(null);
  const isUserScrolling = useRef(false);
  const scrollTimeout = useRef<number | null>(null);

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

    // Reset user scrolling flag after a delay
    if (scrollTimeout.current) {
      clearTimeout(scrollTimeout.current);
    }
    scrollTimeout.current = window.setTimeout(() => {
      isUserScrolling.current = false;
    }, 1000);
  };

  const getLevelIcon = (level: string) => {
    const levelLower = level.toLowerCase();
    switch (levelLower) {
      case "error":
        return <XCircle className="h-3.5 w-3.5 text-red-500" />;
      case "warning":
        return <AlertCircle className="h-3.5 w-3.5 text-yellow-500" />;
      case "success":
        return <CheckCircle className="h-3.5 w-3.5 text-green-500" />;
      default:
        return <Info className="h-3.5 w-3.5 text-blue-500" />;
    }
  };

  const getLevelColor = (level: string) => {
    const levelLower = level.toLowerCase();
    switch (levelLower) {
      case "error":
        return "text-red-400";
      case "warning":
        return "text-yellow-400";
      case "success":
        return "text-green-400";
      case "debug":
        return "text-gray-500";
      default:
        return "text-blue-400";
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      const timeStr = date.toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      const ms = date.getMilliseconds().toString().padStart(3, "0");
      return `${timeStr}.${ms}`;
    } catch {
      return timestamp;
    }
  };

  const formatLogData = (data: Record<string, unknown> | null) => {
    if (!data) return null;
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-gray-700 bg-gray-900">
      {/* Console Header */}
      <div className="flex items-center gap-2 border-b border-gray-700 bg-gray-800 px-4 py-2">
        <Terminal className="h-4 w-4 text-gray-400" />
        <span className="text-sm font-semibold text-gray-300">Experiment Logs</span>
        <div className="ml-auto text-xs text-gray-500">{logs.length} entries</div>
      </div>

      {/* Console Content */}
      <div
        ref={consoleRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 font-mono text-xs"
        style={{ fontFamily: "'Monaco', 'Menlo', 'Ubuntu Mono', monospace" }}
      >
        {logs.length === 0 ? (
          <div className="flex h-full items-center justify-center text-gray-500">
            <div className="text-center">
              <Terminal className="mx-auto mb-2 h-8 w-8 opacity-50" />
              <p>Waiting for logs...</p>
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            {logs.map((log, index) => (
              <div
                key={`${log.timestamp}-${index}`}
                className="group rounded px-2 py-1 hover:bg-gray-800/50"
              >
                <div className="flex items-start gap-2">
                  {/* Timestamp */}
                  <span className="flex-shrink-0 text-gray-500">
                    [{formatTimestamp(log.timestamp)}]
                  </span>

                  {/* Level Icon & Badge */}
                  <span className="flex flex-shrink-0 items-center gap-1">
                    {getLevelIcon(log.level)}
                    <span className={`font-semibold uppercase ${getLevelColor(log.level)}`}>
                      {log.level}
                    </span>
                  </span>

                  {/* Agent ID */}
                  {log.agent_id && (
                    <span className="flex-shrink-0 text-purple-400">[{log.agent_id}]</span>
                  )}

                  {/* Message */}
                  <span className="flex-1 text-gray-300">{log.message || "(no message)"}</span>
                </div>

                {/* Additional Data */}
                {log.data && (
                  <div className="ml-20 mt-1 text-gray-500">
                    <pre className="whitespace-pre-wrap break-words">{formatLogData(log.data)}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Scroll Indicator */}
      {isUserScrolling.current && (
        <div className="border-t border-gray-700 bg-gray-800 px-4 py-2 text-center text-xs text-yellow-400">
          Auto-scroll paused. Scroll to bottom to resume.
        </div>
      )}
    </div>
  );
}

export default LogConsole;
