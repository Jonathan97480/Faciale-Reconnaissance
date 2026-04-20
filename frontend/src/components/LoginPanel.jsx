import { useState } from "react";

import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function LoginPanel() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setStatus("Connexion en cours...");
    try {
      await login(username, password);
      setStatus("");
    } catch (error) {
      if (error instanceof ApiError && error.status === 503) {
        setStatus("Authentification non configuree sur le backend.");
      } else {
        setStatus("Identifiants invalides.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="app-shell">
      <section
        className="panel"
        style={{ maxWidth: 440, margin: "12vh auto 0" }}
      >
        <p className="eyebrow">SECURE ACCESS</p>
        <h1>Connexion administrateur</h1>
        <p className="subtitle">
          Les routes biométriques et de configuration exigent une session
          valide.
        </p>
        <form className="field-grid" onSubmit={onSubmit}>
          <label>
            Nom d&apos;utilisateur
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
            />
          </label>
          <label>
            Mot de passe
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>
          <button type="submit" disabled={submitting}>
            {submitting ? "Connexion..." : "Se connecter"}
          </button>
        </form>
        <p className="status-line">{status}</p>
      </section>
    </main>
  );
}
