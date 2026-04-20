import { useEffect, useState } from "react";

import { apiClient } from "../api/client";

export default function FaceManager() {
  const [faces, setFaces] = useState([]);
  const [name, setName] = useState("");
  const [adresse, setAdresse] = useState("");
  const [metier, setMetier] = useState("");
  const [lieuNaissance, setLieuNaissance] = useState("");
  const [age, setAge] = useState("");
  const [anneeNaissance, setAnneeNaissance] = useState("");
  const [autresInfos, setAutresInfos] = useState("");
  const [status, setStatus] = useState("");
  const [enrolling, setEnrolling] = useState(false);

  const loadFaces = async () => {
    const data = await apiClient.listFaces();
    setFaces(data);
  };

  useEffect(() => {
    loadFaces().catch(() => setStatus("Impossible de charger les visages."));
  }, []);

  const resetFields = () => {
    setName("");
    setAdresse("");
    setMetier("");
    setLieuNaissance("");
    setAge("");
    setAnneeNaissance("");
    setAutresInfos("");
  };

  const addFace = async () => {
    if (!name.trim()) {
      setStatus("Le nom est obligatoire.");
      return;
    }
    try {
      await apiClient.createFace({
        name,
        encoding: null,
        adresse: adresse || null,
        metier: metier || null,
        lieu_naissance: lieuNaissance || null,
        age: age ? Number(age) : null,
        annee_naissance: anneeNaissance ? Number(anneeNaissance) : null,
        autres_infos: autresInfos || null,
      });
      resetFields();
      setStatus("Visage ajouté (sans encodage).");
      await loadFaces();
    } catch {
      setStatus("Echec de création du visage.");
    }
  };

  const enrollFace = async () => {
    if (!name.trim()) {
      setStatus("Le nom est obligatoire avant d'enroler.");
      return;
    }
    setEnrolling(true);
    setStatus("Capture webcam en cours...");
    try {
      await apiClient.enrollFace({
        name,
        adresse: adresse || null,
        metier: metier || null,
        lieu_naissance: lieuNaissance || null,
        age: age ? Number(age) : null,
        annee_naissance: anneeNaissance ? Number(anneeNaissance) : null,
        autres_infos: autresInfos || null,
      });
      resetFields();
      setStatus("Visage enrole avec succès.");
      await loadFaces();
    } catch (err) {
      setStatus(err.message || "Echec de l'enrolement.");
    } finally {
      setEnrolling(false);
    }
  };

  const removeFace = async (id) => {
    try {
      await apiClient.deleteFace(id);
      setStatus("Visage supprime.");
      await loadFaces();
    } catch {
      setStatus("Echec de suppression.");
    }
  };

  return (
    <section className="panel">
      <h2>Gestion des visages</h2>
      <div className="field-grid">
        <input
          type="text"
          value={name}
          placeholder="Nom du visage"
          onChange={(event) => setName(event.target.value)}
        />
        <input
          type="text"
          value={adresse}
          placeholder="Adresse (optionnel)"
          onChange={(e) => setAdresse(e.target.value)}
        />
        <input
          type="text"
          value={metier}
          placeholder="Métier (optionnel)"
          onChange={(e) => setMetier(e.target.value)}
        />
        <input
          type="text"
          value={lieuNaissance}
          placeholder="Lieu de naissance (optionnel)"
          onChange={(e) => setLieuNaissance(e.target.value)}
        />
        <input
          type="number"
          value={age}
          placeholder="Âge (optionnel)"
          onChange={(e) => setAge(e.target.value)}
        />
        <input
          type="number"
          value={anneeNaissance}
          placeholder="Année de naissance (optionnel)"
          onChange={(e) => setAnneeNaissance(e.target.value)}
        />
        <textarea
          value={autresInfos}
          placeholder="Autres infos (texte, optionnel)"
          onChange={(e) => setAutresInfos(e.target.value)}
        />
        <div className="button-row">
          <button onClick={addFace}>Ajouter (sans encodage)</button>
          <button onClick={enrollFace} disabled={enrolling}>
            {enrolling ? "Capture..." : "Enroler depuis webcam"}
          </button>
        </div>
      </div>
      <ul className="face-list">
        {faces.map((face) => (
          <li className="face-row" key={face.id}>
            <div>
              <strong>{face.name}</strong>
              <div>
                #{face.id} {face.has_encoding ? "Encode" : "Sans encodage"}
              </div>
              {face.adresse && (
                <div>
                  <b>Adresse:</b> {face.adresse}
                </div>
              )}
              {face.metier && (
                <div>
                  <b>Métier:</b> {face.metier}
                </div>
              )}
              {face.lieu_naissance && (
                <div>
                  <b>Lieu naissance:</b> {face.lieu_naissance}
                </div>
              )}
              {face.age !== undefined && face.age !== null && (
                <div>
                  <b>Âge:</b> {face.age}
                </div>
              )}
              {face.annee_naissance !== undefined &&
                face.annee_naissance !== null && (
                  <div>
                    <b>Année naissance:</b> {face.annee_naissance}
                  </div>
                )}
              {face.autres_infos && (
                <div>
                  <b>Autres infos:</b> {face.autres_infos}
                </div>
              )}
            </div>
            <button onClick={() => removeFace(face.id)}>Supprimer</button>
          </li>
        ))}
      </ul>
      <p className="status-line">{status}</p>
    </section>
  );
}
