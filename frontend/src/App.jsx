import ConfigPanel from "./components/ConfigPanel";
import FaceManager from "./components/FaceManager";
import LoginPanel from "./components/LoginPanel";
import MonitoringPanel from "./components/MonitoringPanel";
import { useAuth, AuthProvider } from "./context/AuthContext";
import { ConfigProvider } from "./context/ConfigContext";
import "./app.css";

function AuthenticatedApp() {
  const { user, loading, isAuthenticated, logout } = useAuth();

  if (loading) {
    return (
      <main className="app-shell">
        <section className="panel" style={{ maxWidth: 420, margin: "12vh auto 0" }}>
          <h1>Chargement de la session</h1>
        </section>
      </main>
    );
  }

  if (!isAuthenticated) {
    return <LoginPanel />;
  }

  return (
    <ConfigProvider>
      <main className="app-shell">
        <header className="command-header">
          <p className="eyebrow">FBI STYLE FIELD CONSOLE</p>
          <h1>Console Reconnaissance Faciale</h1>
          <p className="subtitle">
            Supervision en temps reel, enrollement, et analyse multi-visages.
          </p>
          <div className="button-row" style={{ marginTop: 12 }}>
            <span className="badge ok">Session: {user?.username}</span>
            <button type="button" onClick={logout}>Se deconnecter</button>
          </div>
        </header>

        <section className="grid-layout">
          <div className="grid-column">
            <MonitoringPanel />
          </div>
          <div className="grid-column side-stack">
            <ConfigPanel />
            <FaceManager />
          </div>
        </section>
      </main>
    </ConfigProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AuthenticatedApp />
    </AuthProvider>
  );
}
