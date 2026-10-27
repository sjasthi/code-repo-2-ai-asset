import { NavLink, Outlet } from "react-router-dom";
import { API_URL } from "../api/client";
import { useApiStatus, type ServiceState } from "../hooks/useApiStatus";

const NAV_ITEMS = [
  { to: "/upload", label: "Upload" },
  { to: "/search", label: "Search" },
  { to: "/dependencies", label: "Dependencies" },
];

const STATE_LABEL: Record<ServiceState, string> = {
  checking: "checking",
  up: "connected",
  down: "unreachable",
};

function StatusDot({
  name,
  state,
  title,
}: {
  name: string;
  state: ServiceState;
  title?: string;
}) {
  return (
    <span className="status" title={title}>
      <span className={`status-dot status-dot--${state}`} aria-hidden="true" />
      {name} {STATE_LABEL[state]}
    </span>
  );
}

export default function Layout() {
  const status = useApiStatus();

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/upload" className="brand">
            Code Dependency Graph
          </NavLink>

          <nav aria-label="Main">
            <ul className="nav">
              {NAV_ITEMS.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    className={({ isActive }) =>
                      isActive ? "nav-link nav-link--active" : "nav-link"
                    }
                  >
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <div className="statuses" aria-live="polite">
            <StatusDot name="API" state={status.api} title={API_URL} />
            <StatusDot
              name="Neo4j"
              state={status.database}
              title={status.databaseDetail}
            />
          </div>
        </div>
      </header>

      <main className="page">
        <Outlet />
      </main>
    </div>
  );
}
