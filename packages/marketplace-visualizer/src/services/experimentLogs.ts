/**
 * Service for streaming experiment logs via WebSocket.
 * Provides methods for connecting to log streams and handling reconnections.
 */

import { LogEntry, LogStreamMessage } from "../types";

const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL ||
  `ws://${window.location.hostname}:${window.location.port || "8000"}`;

export interface LogStreamOptions {
  experimentName: string;
  since?: string;
  host?: string;
  port?: number;
  database?: string;
  user?: string;
  password?: string;
  onLog?: (log: LogEntry) => void;
  onStatus?: (status: string) => void;
  onError?: (error: string) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export class ExperimentLogStream {
  private ws: WebSocket | null = null;
  private options: LogStreamOptions;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private reconnectTimer: number | null = null;
  private intentionallyClosed = false;

  constructor(options: LogStreamOptions) {
    this.options = options;
  }

  /**
   * Connect to the WebSocket log stream
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }

    this.intentionallyClosed = false;
    const params = new URLSearchParams();

    if (this.options.since) params.append("since", this.options.since);
    if (this.options.host) params.append("host", this.options.host);
    if (this.options.port) params.append("port", this.options.port.toString());
    if (this.options.database) params.append("database", this.options.database);
    if (this.options.user) params.append("user", this.options.user);
    if (this.options.password) params.append("password", this.options.password);

    const queryString = params.toString() ? `?${params.toString()}` : "";
    const wsUrl = `${WS_BASE_URL}/api/experiments/${encodeURIComponent(this.options.experimentName)}/logs/ws${queryString}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.options.onConnect?.();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: LogStreamMessage = JSON.parse(event.data);

          switch (message.type) {
            case "log":
              if (message.log) {
                this.options.onLog?.(message.log);
              }
              break;
            case "status":
              if (message.status) {
                this.options.onStatus?.(message.status);
              }
              break;
            case "error":
              if (message.error) {
                this.options.onError?.(message.error);
              }
              break;
          }
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      this.ws.onerror = (event) => {
        console.error("WebSocket error:", event);
      };

      this.ws.onclose = () => {
        this.options.onDisconnect?.();

        // Only attempt reconnection if not intentionally closed and within retry limits
        if (!this.intentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          this.options.onError?.("Maximum reconnection attempts reached. Please refresh the page.");
        }
      };
    } catch (error) {
      console.error("Failed to create WebSocket connection:", error);
      this.options.onError?.(`Failed to connect: ${error}`);
    }
  }

  /**
   * Schedule a reconnection attempt with exponential backoff
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectAttempts++;
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Cap at 30 seconds
      console.log(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
      this.connect();
    }, this.reconnectDelay);
  }

  /**
   * Close the WebSocket connection
   */
  close(): void {
    this.intentionallyClosed = true;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Check if the connection is currently open
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

/**
 * Helper function to create and manage a log stream
 */
export function createLogStream(options: LogStreamOptions): ExperimentLogStream {
  const stream = new ExperimentLogStream(options);
  stream.connect();
  return stream;
}
