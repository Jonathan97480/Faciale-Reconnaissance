export default function MonitoringImageAnalysisPanel({
  imageAnalysis,
  runImageAnalysis,
  setSelectedImage,
}) {
  return (
    <section className="history-panel">
      <h3>Analyse d&apos;image (API)</h3>
      <div className="button-row">
        <input
          type="file"
          accept="image/*"
          onChange={(event) =>
            setSelectedImage(event.target.files?.[0] ?? null)
          }
        />
        <button onClick={runImageAnalysis}>Analyser image</button>
      </div>
      {imageAnalysis?.faces?.length > 0 && (
        <div className="crop-grid">
          {imageAnalysis.faces.map((face, index) => (
            <article key={`crop-${index}`} className="crop-card">
              {face.face_image_base64 ? (
                <img
                  src={`data:image/jpeg;base64,${face.face_image_base64}`}
                  alt={`Visage detecte ${index + 1}`}
                />
              ) : (
                <div className="crop-missing">Crop indisponible</div>
              )}
              <div>
                <strong>{face.face_name || `Inconnu #${index + 1}`}</strong>
                <div>Statut: {face.status}</div>
                <div>
                  Score:{" "}
                  {typeof face.score === "number"
                    ? `${(face.score * 100).toFixed(1)}%`
                    : "--"}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
      {imageAnalysis && (
        <pre className="block-json">
          {JSON.stringify(imageAnalysis, null, 2)}
        </pre>
      )}
    </section>
  );
}
