import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import UploadPage from "./pages/UploadPage";
import SearchPage from "./pages/SearchPage";
import DependenciesPage from "./pages/DependenciesPage";
import NotFoundPage from "./pages/NotFoundPage";

// Cytoscape is large; only load it when the graph is opened.
const GraphPage = lazy(() => import("./pages/GraphPage"));

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/upload" replace />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="dependencies" element={<DependenciesPage />} />
        <Route
          path="graph"
          element={
            <Suspense fallback={<p className="muted">Loading graph…</p>}>
              <GraphPage />
            </Suspense>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
