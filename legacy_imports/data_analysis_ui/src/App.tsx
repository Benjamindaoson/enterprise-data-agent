import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppProvider } from "./store/AppContext";
import { Shell } from "./components/Shell";
import { Today } from "./pages/Today";
import { Analyses } from "./pages/Analyses";
import { AnalysisWorkspace } from "./pages/AnalysisWorkspace";
import { DataPage } from "./pages/DataPage";
import { MetricsPage } from "./pages/MetricsPage";
import { EvaluationPage } from "./pages/EvaluationPage";
import { SettingsPage } from "./pages/SettingsPage";

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<Navigate to="/today" replace />} />
            <Route path="/today" element={<Today />} />
            <Route path="/analyses" element={<Analyses />} />
            <Route path="/analyses/:id" element={<AnalysisWorkspace />} />
            <Route path="/data" element={<DataPage />} />
            <Route path="/metrics" element={<MetricsPage />} />
            <Route path="/evaluation" element={<EvaluationPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}
