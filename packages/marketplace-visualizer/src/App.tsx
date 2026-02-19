import { BrowserRouter, Link, Route, Routes } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import RunningExperiment from "./pages/RunningExperiment";
import Visualizer from "./pages/Visualizer";

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

function VisualizerWithNav() {
  return (
    <>
      <nav className="border-b border-gray-200 bg-white">
        <div className="px-8 py-3">
          <Link
            to="/dashboard"
            className="text-sm font-medium text-brand-600 hover:text-brand-700 hover:underline"
          >
            ← Back to Dashboard
          </Link>
        </div>
      </nav>
      <Visualizer />
    </>
  );
}

function DashboardWithNav() {
  return (
    <>
      <nav className="border-b border-gray-200 bg-white">
        <div className="px-8 py-3">
          <div className="flex items-center gap-2">
            <img src="/logo.svg" alt="Magentic Logo" className="h-6 w-6" />
            <h1
              className="bg-clip-text text-lg font-bold text-transparent"
              style={{ backgroundImage: "linear-gradient(120deg, #fb81ff, #922185 30%)" }}
            >
              Magentic Marketplace
            </h1>
          </div>
        </div>
      </nav>
      <Dashboard />
    </>
  );
}

function RunningExperimentWithNav() {
  return (
    <>
      <nav className="border-b border-gray-200 bg-white">
        <div className="px-8 py-3">
          <Link
            to="/dashboard"
            className="text-sm font-medium text-brand-600 hover:text-brand-700 hover:underline"
          >
            ← Back to Dashboard
          </Link>
        </div>
      </nav>
      <RunningExperiment />
    </>
  );
}

export default App;
