import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import quizApi from "../api/quizApi";
import { useQuizState } from "../context/QuizStateContext";

/**
 * Screen 1 — Document Upload (R3-R6). Original page name: UploadedDocument
 * (R1: never renamed to DocumentsPage). Upload a JSON, PDF or Word (.docx)
 * file of MCQs, see validation errors, list uploaded documents, and click one
 * to base the quiz on it (proceeds to Quiz Configuration).
 */
const UploadedDocument: React.FC = () => {
  const navigate = useNavigate();
  const { state, selectDocument } = useQuizState();
  const inputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(state.documentId);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await quizApi.listDocuments();
      const rows = Array.isArray(data) ? data : (data as any)?.data ?? [];
      setDocuments(rows);
    } catch (err: any) {
      setError(err?.detail || "Could not load the uploaded documents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      event.target.value = ""; // allow re-uploading the same file
      if (!file) return;
      const isJson = /\.json$/i.test(file.name) || file.type === "application/json";
      const isPdf = /\.pdf$/i.test(file.name) || file.type === "application/pdf";
      const isWord =
        /\.docx$/i.test(file.name) ||
        file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
      if (!isJson && !isPdf && !isWord) {
        setError("Only JSON, PDF or Word (.docx) files are accepted");
        return;
      }
      setUploading(true);
      setError(null);
      setNotice(null);
      try {
        const result = await quizApi.uploadDocument(file);
        setNotice(
          `Uploaded "${result.document?.fileName ?? file.name}" — ${result.questionCount} question(s) extracted and validated`
        );
        await loadDocuments();
        if (result.document?.id) {
          setSelectedId(result.document.id);
        }
      } catch (err: any) {
        setError(err?.detail || "The document could not be uploaded or validated");
      } finally {
        setUploading(false);
      }
    },
    [loadDocuments]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      setError(null);
      setNotice(null);
      try {
        await quizApi.deleteDocument(id);
        setNotice("Document deleted");
        setSelectedId((previous) => (previous === id ? null : previous));
        await loadDocuments();
      } catch (err: any) {
        setError(err?.detail || "The document could not be deleted");
      }
    },
    [loadDocuments]
  );

  const proceedToConfiguration = useCallback(() => {
    if (!selectedId) return;
    const doc = documents.find((item) => item.id === selectedId);
    selectDocument(selectedId, doc?.fileName ?? "document");
    navigate("/configure");
  }, [documents, navigate, selectDocument, selectedId]);

  return (
    <div className="ds-section">
      <h1 className="ds-heading">Document Upload</h1>
      <p style={{ color: "var(--ds-muted)", marginTop: 0 }}>
        Upload a JSON, PDF or Word (.docx) file that contains multiple-choice questions, answer options and correct
        answers. A Word document may also carry an explanation, a difficulty and an audio sentence per question.
      </p>

      {error && (
        <div className="ds-notice" role="alert" style={{ borderColor: "var(--ds-primary)", marginBottom: "1rem" }}>
          <strong>Validation failed:</strong>&nbsp;{error}
        </div>
      )}
      {notice && (
        <div className="ds-notice" role="status">
          {notice}
        </div>
      )}

      <section className="ds-card" style={{ marginTop: "1rem", padding: "1.25rem" }}>
        <h2 className="ds-heading" style={{ fontSize: "1.2rem" }}>
          Upload a document
        </h2>
        <div className="ds-field">
          <label className="ds-label" htmlFor="quiz-file-input">
            File (JSON, PDF or Word)
          </label>
          <input
            id="quiz-file-input"
            ref={inputRef}
            type="file"
            className="ds-input"
            accept=".json,.pdf,.docx,application/json,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={handleFileChange}
            disabled={uploading}
          />
        </div>
        <button
          type="button"
          className="ds-btn ds-btn-primary"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? "Validating and uploading…" : "Choose a file to upload"}
        </button>
        <p style={{ color: "var(--ds-muted)", marginBottom: 0 }}>
          The document is validated before you can proceed: every question needs at least two options and exactly one
          correct answer.
        </p>
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2 className="ds-heading" style={{ fontSize: "1.2rem" }}>
          Uploaded documents
        </h2>
        {loading ? (
          <p style={{ color: "var(--ds-muted)" }}>Loading documents…</p>
        ) : documents.length === 0 ? (
          <p style={{ color: "var(--ds-muted)" }}>No documents uploaded yet. Start by uploading a JSON, PDF or Word file.</p>
        ) : (
          <div className="ds-table-wrap">
            <table className="ds-table">
              <thead>
                <tr>
                  <th></th>
                  <th>File name</th>
                  <th>Type</th>
                  <th>Size</th>
                  <th>Uploaded</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <input
                        type="radio"
                        name="selected-document"
                        aria-label={`Base the quiz on ${doc.fileName}`}
                        checked={selectedId === doc.id}
                        onChange={() => setSelectedId(doc.id)}
                      />
                    </td>
                    <td>{doc.fileName}</td>
                    <td>{doc.contentType}</td>
                    <td>{(doc.fileSizeBytes ?? 0).toLocaleString()} bytes</td>
                    <td>{doc.uploadDate ? new Date(doc.uploadDate).toLocaleString() : "—"}</td>
                    <td>
                      <button type="button" className="ds-btn" onClick={() => handleDelete(doc.id)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <button
          type="button"
          className="ds-btn ds-btn-primary"
          style={{ marginTop: "1rem" }}
          onClick={proceedToConfiguration}
          disabled={!selectedId}
        >
          Base the quiz on the selected document →
        </button>
      </section>
    </div>
  );
};

export default UploadedDocument;
