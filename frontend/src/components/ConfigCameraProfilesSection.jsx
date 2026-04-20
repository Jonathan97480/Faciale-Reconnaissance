export default function ConfigCameraProfilesSection({
  addCameraProfile,
  newCameraProfile,
  profiles,
  removeCameraProfile,
  setNewCameraProfile,
}) {
  return (
    <div className="panel" style={{ marginTop: 10 }}>
      <h3>Profils camera standards (RTSP/MJPEG/HTTP/HLS)</h3>
      <div className="field-grid">
        <label>
          Nom
          <input
            type="text"
            value={newCameraProfile.name}
            onChange={(event) => setNewCameraProfile({ ...newCameraProfile, name: event.target.value })}
          />
        </label>
        <label>
          Protocole
          <select
            value={newCameraProfile.protocol}
            onChange={(event) => setNewCameraProfile({ ...newCameraProfile, protocol: event.target.value })}
          >
            <option value="rtsp">RTSP</option>
            <option value="mjpeg">MJPEG</option>
            <option value="http">HTTP</option>
            <option value="hls">HLS</option>
          </select>
        </label>
        <label>
          Host/IP
          <input
            type="text"
            value={newCameraProfile.host}
            onChange={(event) => setNewCameraProfile({ ...newCameraProfile, host: event.target.value })}
          />
        </label>
        <label>
          Port
          <input
            type="number"
            min="1"
            max="65535"
            value={newCameraProfile.port}
            onChange={(event) => setNewCameraProfile({ ...newCameraProfile, port: event.target.value })}
          />
        </label>
        <label>
          Path stream
          <input
            type="text"
            value={newCameraProfile.path}
            onChange={(event) => setNewCameraProfile({ ...newCameraProfile, path: event.target.value })}
          />
        </label>
        <label>
          Username
          <input
            type="text"
            value={newCameraProfile.username}
            onChange={(event) => setNewCameraProfile({ ...newCameraProfile, username: event.target.value })}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={newCameraProfile.password}
            onChange={(event) => setNewCameraProfile({ ...newCameraProfile, password: event.target.value })}
          />
        </label>
        <label>
          URL ONVIF (optionnel)
          <input
            type="text"
            value={newCameraProfile.onvif_url}
            onChange={(event) => setNewCameraProfile({ ...newCameraProfile, onvif_url: event.target.value })}
          />
        </label>
      </div>
      <div className="button-row" style={{ marginTop: 8 }}>
        <button type="button" onClick={addCameraProfile}>Ajouter profil camera</button>
      </div>
      {profiles.length === 0 && (
        <p className="status-line">Aucun profil camera standard configure.</p>
      )}
      {profiles.length > 0 && (
        <ul className="history-list">
          {profiles.map((profile, index) => (
            <li key={`${profile.name}-${index}`} className="history-row">
              <span>{profile.name}</span>
              <span>{profile.protocol.toUpperCase()} {profile.host}:{profile.port}{profile.path}</span>
              <button type="button" onClick={() => removeCameraProfile(index)}>Supprimer</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
