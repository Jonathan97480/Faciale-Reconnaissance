import { useEffect, useState } from "react";

import { apiClient, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function LoginPanel() {
  const { login, refreshUser } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [setupRequired, setSetupRequired] = useState(false);
  const [status, setStatus] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    apiClient
      .getAuthBootstrapStatus()
      .then((payload) => setSetupRequired(Boolean(payload.setup_required)))
      .catch(() => setSetupRequired(false));
  }, []);

  const onSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setStatus(setupRequired ? "Creation du compte admin..." : "Connexion en cours...");
    try {
      if (setupRequired) {
        await apiClient.bootstrapAdmin({ username, password });
        await refreshUser();
      } else {
        await login(username, password);
      }
      setStatus("");
    } catch (error) {
      if (error instanceof ApiError && error.status === 503 && !setupRequired) {
        setStatus(
          "Authentification non configuree sur le backend. Creez le premier compte admin."
        );
        setSetupRequired(true);
      } else if (error instanceof ApiError && error.status === 409) {
        setStatus("Un compte admin existe deja. Connectez-vous avec ce compte.");
        setSetupRequired(false);
      } else {
        setStatus(
          setupRequired ? "Impossible de creer le compte admin." : "Identifiants invalides."
        );
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
        <h1>{setupRequired ? "Creation du premier administrateur" : "Connexion administrateur"}</h1>
        <p className="subtitle">
          {setupRequired
            ? "Aucun compte admin n'est configure. Creez le premier compte pour initialiser l'application."
            : "Les routes biométriques et de configuration exigent une session valide."}
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
            {submitting
              ? setupRequired
                ? "Creation..."
                : "Connexion..."
              : setupRequired
                ? "Creer le compte admin"
                : "Se connecter"}
          </button>
        </form>
        <p className="status-line">{status}</p>
      </section>
    </main>
  );
}
