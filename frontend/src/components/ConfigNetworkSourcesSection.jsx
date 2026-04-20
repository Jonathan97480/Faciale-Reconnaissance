export default function ConfigNetworkSourcesSection({
  addNetworkSource,
  networkSources,
  newNetworkSource,
  removeNetworkSource,
  setNewNetworkSource,
}) {
  return (
    <div className="panel" style={{ marginTop: 10 }}>
      <h3>Flux caméras réseau (max 10)</h3>
      <div className="button-row">
        <input
          type="text"
          placeholder="rtsp://..., http://..., fichier video..."
          value={newNetworkSource}
          onChange={(event) => setNewNetworkSource(event.target.value)}
          style={{ width: "100%" }}
        />
        <button type="button" onClick={addNetworkSource}>Ajouter flux</button>
      </div>
      {networkSources.length === 0 && (
        <p className="status-line">Aucun flux reseau configure.</p>
      )}
      {networkSources.length > 0 && (
        <ul className="history-list">
          {networkSources.map((source) => (
            <li key={source} className="history-row">
              <span>{source}</span>
              <button type="button" onClick={() => removeNetworkSource(source)}>Supprimer</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
