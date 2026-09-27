import { useEffect, useState } from "react";
import { HashRouter, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import ContainerDetail from "./pages/ContainerDetail";
import WhatChanged from "./pages/WhatChanged";
import Incidents from "./pages/Incidents";
import IncidentDetail from "./pages/IncidentDetail";
import Login from "./pages/Login";
import SetupWizard from "./pages/SetupWizard";
import DatabaseSettings from "./pages/DatabaseSettings";
import About from "./pages/About";
import { getMe, getSetupStatus } from "./api/client";

export default function App() {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [dbConfigured, setDbConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    getMe()
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false));
  }, []);

  useEffect(() => {
    if (authed !== true) return;
    getSetupStatus()
      .then((status) => setDbConfigured(status.configured))
      .catch(() => setDbConfigured(false));
  }, [authed]);

  if (authed === null) {
    return <div className="min-h-full" />;
  }

  if (!authed) {
    return <Login onLoggedIn={() => setAuthed(true)} />;
  }

  if (dbConfigured === null) {
    return <div className="min-h-full" />;
  }

  if (!dbConfigured) {
    return <SetupWizard onComplete={() => setDbConfigured(true)} />;
  }

  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/containers/:containerId" element={<ContainerDetail />} />
        <Route path="/changes" element={<WhatChanged />} />
        <Route path="/incidents" element={<Incidents />} />
        <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
        <Route path="/settings/database" element={<DatabaseSettings />} />
        <Route path="/about" element={<About />} />
      </Routes>
    </HashRouter>
  );
}
