import { AlertCircle, Beaker, CheckCircle, Clock, Eye, Loader2, Play, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  DatasetInfo,
  ExperimentCreate,
  ExperimentInfo,
  ExperimentStatus,
  orchestratorService,
} from "../services/orchestrator";

function Dashboard() {
  // Helper to load running experiments from localStorage
  const loadRunningExperimentsFromStorage = (): Map<string, ExperimentStatus> => {
    try {
      const stored = localStorage.getItem("runningExperiments");
      if (stored) {
        const parsed = JSON.parse(stored) as Array<[string, ExperimentStatus]>;
        return new Map(parsed);
      }
    } catch (e) {
      console.error("Failed to load running experiments from storage:", e);
    }
    return new Map();
  };

  // Helper to save running experiments to localStorage
  const saveRunningExperimentsToStorage = (experiments: Map<string, ExperimentStatus>) => {
    try {
      localStorage.setItem("runningExperiments", JSON.stringify(Array.from(experiments.entries())));
    } catch (e) {
      console.error("Failed to save running experiments to storage:", e);
    }
  };

  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [experiments, setExperiments] = useState<ExperimentInfo[]>([]);
  const [runningExperiments, setRunningExperiments] = useState<Map<string, ExperimentStatus>>(
    loadRunningExperimentsFromStorage(),
  );

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);

  // Form state
  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [experimentName, setExperimentName] = useState<string>("");
  const [searchAlgorithm, setSearchAlgorithm] = useState<string>("simple");
  const [searchBandwidth, setSearchBandwidth] = useState<number>(10);
  const [customerMaxSteps, setCustomerMaxSteps] = useState<number | undefined>(undefined);
  const [postgresHost, setPostgresHost] = useState<string>("localhost");
  const [postgresPort, setPostgresPort] = useState<number>(5432);
  const [postgresPassword, setPostgresPassword] = useState<string>("postgres");

  const loadExperiments = useCallback(async () => {
    try {
      const experimentsData = await orchestratorService.getExperiments({
        host: postgresHost,
        port: postgresPort,
        password: postgresPassword,
      });
      setExperiments(experimentsData);

      // Check status of each experiment and populate runningExperiments Map
      const runningStatuses = new Map<string, ExperimentStatus>();
      for (const exp of experimentsData) {
        try {
          const status = await orchestratorService.getExperimentStatus(exp.schema_name);
          if (status.status === "pending" || status.status === "running") {
            runningStatuses.set(exp.schema_name, status);
          }
        } catch (err) {
          // Experiment might not have status info, skip it
          console.debug(`No status for experiment ${exp.schema_name}:`, err);
        }
      }

      if (runningStatuses.size > 0) {
        setRunningExperiments(
          (prev: Map<string, ExperimentStatus>) => new Map([...prev, ...runningStatuses]),
        );
      }
    } catch (err) {
      console.error("Failed to load experiments:", err);
    }
  }, [postgresHost, postgresPort, postgresPassword]);

  const loadInitialData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [datasetsData, settingsData] = await Promise.all([
        orchestratorService.getDatasets(),
        orchestratorService.getSettings(),
      ]);
      setDatasets(datasetsData);

      // Set defaults from settings
      if (settingsData) {
        setSearchAlgorithm(settingsData.default_search_algorithm);
        setSearchBandwidth(settingsData.default_search_bandwidth);
        setPostgresHost(settingsData.default_postgres_host);
        setPostgresPort(settingsData.default_postgres_port);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load initial data");
    } finally {
      setLoading(false);
    }
  }, []);

  const pollRunningExperiments = useCallback(async () => {
    const statusUpdates = new Map<string, ExperimentStatus>();

    for (const [name, status] of runningExperiments.entries()) {
      if (status.status === "pending" || status.status === "running") {
        try {
          const updatedStatus = await orchestratorService.getExperimentStatus(name);
          statusUpdates.set(name, updatedStatus);
        } catch (err) {
          console.error(`Failed to poll experiment ${name}:`, err);
        }
      }
    }

    if (statusUpdates.size > 0) {
      setRunningExperiments((prev: Map<string, ExperimentStatus>) => {
        const updated = new Map([...prev, ...statusUpdates]);
        // Remove completed or failed experiments from the running experiments map
        for (const [name, status] of updated.entries()) {
          if (status.status === "completed" || status.status === "failed") {
            updated.delete(name);
          }
        }
        return updated;
      });

      // Reload experiments list if any completed
      const hasCompleted = Array.from(statusUpdates.values()).some(
        (s) => s.status === "completed" || s.status === "failed",
      );
      if (hasCompleted) {
        loadExperiments();
      }
    }
  }, [runningExperiments, loadExperiments]);

  // Load initial data
  useEffect(() => {
    loadInitialData();
    loadExperiments();
  }, [loadInitialData, loadExperiments]);

  // Poll running experiments immediately on mount (for experiments loaded from storage)
  useEffect(() => {
    pollRunningExperiments();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Save running experiments to localStorage whenever they change
  useEffect(() => {
    saveRunningExperimentsToStorage(runningExperiments);
  }, [runningExperiments]);

  // Poll experiment status
  useEffect(() => {
    const interval = setInterval(() => {
      pollRunningExperiments();
    }, 3000);

    return () => clearInterval(interval);
  }, [pollRunningExperiments]);

  const handleLaunchExperiment = async (e: React.FormEvent) => {
    e.preventDefault();
    setLaunching(true);
    setError(null);

    try {
      const config: ExperimentCreate = {
        dataset: selectedDataset,
        experiment_name: experimentName || undefined,
        search_algorithm: searchAlgorithm,
        search_bandwidth: searchBandwidth,
        customer_max_steps: customerMaxSteps,
        postgres_host: postgresHost,
        postgres_port: postgresPort,
        postgres_password: postgresPassword,
      };

      // Save DB config to localStorage for the running experiment page
      localStorage.setItem(
        "experimentDbConfig",
        JSON.stringify({
          host: postgresHost,
          port: postgresPort,
          database: "marketplace",
          user: "postgres",
          password: postgresPassword,
        }),
      );

      const status = await orchestratorService.createExperiment(config);
      setRunningExperiments((prev: Map<string, ExperimentStatus>) =>
        new Map(prev).set(status.name, status),
      );

      // Clear form
      setExperimentName("");
      setSelectedDataset("");

      // Reload experiments list
      loadExperiments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to launch experiment");
    } finally {
      setLaunching(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case "running":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return "N/A";
    return new Date(timestamp).toLocaleString();
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 to-gray-100">
        <div className="text-center">
          <Loader2 className="mx-auto mb-4 h-12 w-12 animate-spin text-brand-500" />
          <h2 className="mb-2 text-2xl font-bold text-gray-800">Loading Dashboard...</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-gray-50 p-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8">
          <h1 className="mb-2 text-3xl font-bold text-gray-800">Experiment Launcher</h1>
          <p className="text-gray-600">Configure and launch new marketplace experiments</p>
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-500" />
              <div>
                <h3 className="font-semibold text-red-800">Error</h3>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Launch Form */}
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold text-gray-800">
              <Beaker className="h-5 w-5 text-brand-500" />
              Launch New Experiment
            </h2>

            <form onSubmit={handleLaunchExperiment} className="space-y-4">
              {/* Dataset Selection */}
              <div>
                <label htmlFor="dataset" className="mb-1 block text-sm font-medium text-gray-700">
                  Dataset <span className="text-red-500">*</span>
                </label>
                <select
                  id="dataset"
                  value={selectedDataset}
                  onChange={(e) => setSelectedDataset(e.target.value)}
                  required
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                >
                  <option value="">Select a dataset...</option>
                  {datasets.map((dataset) => (
                    <option key={dataset.name} value={dataset.name}>
                      {dataset.name} ({dataset.num_customers} customers, {dataset.num_businesses}{" "}
                      businesses)
                    </option>
                  ))}
                </select>
              </div>

              {/* Experiment Name */}
              <div>
                <label
                  htmlFor="experimentName"
                  className="mb-1 block text-sm font-medium text-gray-700"
                >
                  Experiment Name <span className="text-xs text-gray-500">(optional)</span>
                </label>
                <input
                  id="experimentName"
                  type="text"
                  value={experimentName}
                  onChange={(e) => setExperimentName(e.target.value)}
                  placeholder="Leave blank for auto-generated name"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              {/* Search Algorithm */}
              <div>
                <label
                  htmlFor="searchAlgorithm"
                  className="mb-1 block text-sm font-medium text-gray-700"
                >
                  Search Algorithm
                </label>
                <input
                  id="searchAlgorithm"
                  type="text"
                  value={searchAlgorithm}
                  onChange={(e) => setSearchAlgorithm(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              {/* Search Bandwidth */}
              <div>
                <label
                  htmlFor="searchBandwidth"
                  className="mb-1 block text-sm font-medium text-gray-700"
                >
                  Search Bandwidth
                </label>
                <input
                  id="searchBandwidth"
                  type="number"
                  value={searchBandwidth}
                  onChange={(e) => setSearchBandwidth(parseInt(e.target.value, 10))}
                  min={1}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              {/* Customer Max Steps */}
              <div>
                <label
                  htmlFor="customerMaxSteps"
                  className="mb-1 block text-sm font-medium text-gray-700"
                >
                  Customer Max Steps <span className="text-xs text-gray-500">(optional)</span>
                </label>
                <input
                  id="customerMaxSteps"
                  type="number"
                  value={customerMaxSteps ?? ""}
                  onChange={(e) =>
                    setCustomerMaxSteps(e.target.value ? parseInt(e.target.value, 10) : undefined)
                  }
                  min={1}
                  placeholder="No limit"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              {/* PostgreSQL Settings */}
              <div className="space-y-3 rounded-md border border-gray-200 bg-gray-50 p-4">
                <h3 className="text-sm font-semibold text-gray-700">PostgreSQL Settings</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="postgresHost"
                      className="mb-1 block text-xs font-medium text-gray-600"
                    >
                      Host
                    </label>
                    <input
                      id="postgresHost"
                      type="text"
                      value={postgresHost}
                      onChange={(e) => setPostgresHost(e.target.value)}
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="postgresPort"
                      className="mb-1 block text-xs font-medium text-gray-600"
                    >
                      Port
                    </label>
                    <input
                      id="postgresPort"
                      type="number"
                      value={postgresPort}
                      onChange={(e) => setPostgresPort(parseInt(e.target.value, 10))}
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    />
                  </div>
                </div>
                <div>
                  <label
                    htmlFor="postgresPassword"
                    className="mb-1 block text-xs font-medium text-gray-600"
                  >
                    Password
                  </label>
                  <input
                    id="postgresPassword"
                    type="password"
                    value={postgresPassword}
                    onChange={(e) => setPostgresPassword(e.target.value)}
                    className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={launching || !selectedDataset}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-brand-500 px-4 py-2 font-semibold text-white transition-colors hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {launching ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Launching...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    Launch Experiment
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Running/Recent Experiments */}
          <div className="space-y-6">
            {/* Running Experiments */}
            {runningExperiments.size > 0 && (
              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                <h2 className="mb-4 text-xl font-semibold text-gray-800">Running Experiments</h2>
                <div className="space-y-3">
                  {Array.from(runningExperiments.entries()).map(([name, status]) => (
                    <div key={name} className="rounded-md border border-gray-200 bg-gray-50 p-4">
                      <div className="mb-2 flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(status.status)}
                          <span className="font-semibold text-gray-800">{name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs uppercase tracking-wide text-gray-500">
                            {status.status}
                          </span>
                          {(status.status === "pending" || status.status === "running") && (
                            <Link
                              to={`/dashboard/experiment/${encodeURIComponent(name)}`}
                              className="flex items-center gap-1 rounded bg-blue-500 px-2 py-1 text-xs font-semibold text-white hover:bg-blue-600"
                            >
                              <Eye className="h-3 w-3" />
                              View Logs
                            </Link>
                          )}
                        </div>
                      </div>
                      <div className="text-xs text-gray-600">
                        {status.started_at && (
                          <div>Started: {formatTimestamp(status.started_at)}</div>
                        )}
                        {status.completed_at && (
                          <div>Completed: {formatTimestamp(status.completed_at)}</div>
                        )}
                        {status.error && (
                          <div className="mt-1 text-red-600">Error: {status.error}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Completed Experiments */}
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-xl font-semibold text-gray-800">Available Experiments</h2>
              {experiments.length === 0 ? (
                <p className="text-sm text-gray-500">No experiments found in database</p>
              ) : (
                <div className="space-y-2">
                  {experiments.map((exp) => (
                    <div
                      key={exp.schema_name}
                      className="rounded-md border border-gray-200 bg-gray-50 p-3 hover:bg-gray-100"
                    >
                      <div className="mb-1 flex items-start justify-between">
                        <span className="font-semibold text-gray-800">{exp.schema_name}</span>
                        <a
                          href={`/?schema=${exp.schema_name}`}
                          className="rounded bg-brand-500 px-2 py-1 text-xs font-semibold text-white hover:bg-brand-600"
                        >
                          View
                        </a>
                      </div>
                      <div className="text-xs text-gray-600">
                        <div>Agents: {exp.agents_count}</div>
                        <div>Actions: {exp.actions_count}</div>
                        {exp.last_activity && <div>Last: {formatTimestamp(exp.last_activity)}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
