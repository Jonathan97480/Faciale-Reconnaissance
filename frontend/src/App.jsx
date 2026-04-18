import ConfigPanel from "./components/ConfigPanel";
import FaceManager from "./components/FaceManager";
import MonitoringPanel from "./components/MonitoringPanel";
import { ConfigProvider } from "./context/ConfigContext";
import "./app.css";

export default function App() {
  return (
    <ConfigProvider>
      <main className="app-shell">
        <header className="command-header">
          <p className="eyebrow">FBI STYLE FIELD CONSOLE</p>
          <h1>Console Reconnaissance Faciale</h1>
          <p className="subtitle">
            Supervision en temps reel, enrollement, et analyse multi-visages.
          </p>
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
