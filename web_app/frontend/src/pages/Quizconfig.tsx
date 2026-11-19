import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import quizApi from "../api/quizApi";
import { useQuizState } from "../context/QuizStateContext";

/**
 * Screen 2 — Quiz Configuration (R8-R11).
 * Learning/Testing mode, number of questions (limited to what the document
 * provides), sequential/random order, then Start the quiz.
 */
const Quizconfig: React.FC = () => {
  const navigate = useNavigate();
  const { state, configure, startAttempt } = useQuizState();
  const [questions, setQuestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"learning" | "testing">(state.mode ?? "learning");
  const [questionOrder, setQuestionOrder] = useState<"sequential" | "random">(state.questionOrder ?? "sequential");
  const [questionCount, setQuestionCount] = useState<number>(1);

  useEffect(() => {
    if (!state.documentId) {
      setError("No document selected. Upload a document first.");
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    quizApi
      .documentQuestions(state.documentId)
      .then((data) => {
        if (!cancelled) {
          setQuestions(Array.isArray(data) ? data : []);
          setQuestionCount(Math.min(1, data.length) || 1);
        }
      })
      .catch((err: any) => {
        if (!cancelled) setError(err?.detail || "Could not load the questions of this document");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [state.documentId]);

  const handleStart = useCallback(async () => {
    if (!state.documentId) return;
    setStarting(true);
    setError(null);
    try {
      const result = await quizApi.startQuiz({
        documentId: state.documentId,
        mode,
        questionOrder,
        questionCount,
      });
      configure(mode, questionOrder);
      startAttempt(
        result.attempt.id,
        result.questionIds.length,
        result.mode,
        result.questionOrder
      );
      navigate("/quiz");
    } catch (err: any) {
      setError(err?.detail || "The quiz could not be started");
    } finally {
      setStarting(false);
    }
  }, [configure, mode, navigate, questionCount, questionOrder, startAttempt, state.documentId]);

  if (!state.documentId) {
    return (
      <div className="ds-section">
        <h1 className="ds-heading">Quiz Configuration</h1>
        <div className="ds-notice" role="alert">
          No document selected. Please upload and select a document first.
        </div>
        <button type="button" className="ds-btn ds-btn-primary" style={{ marginTop: "1rem" }} onClick={() => navigate("/")}>
          Go to Document Upload
        </button>
      </div>
    );
  }

  return (
    <div className="ds-section">
      <h1 className="ds-heading">Quiz Configuration</h1>
      <p style={{ color: "var(--ds-muted)", marginTop: 0 }}>
        Document: <strong>{state.documentName}</strong>
      </p>

      {loading ? (
        <p style={{ color: "var(--ds-muted)" }}>Loading the document's questions…</p>
      ) : questions.length === 0 ? (
        <>
          <div className="ds-notice" role="alert">
            This document contains no questions. Please upload a different document.
          </div>
          <button type="button" className="ds-btn" style={{ marginTop: "1rem" }} onClick={() => navigate("/")}>
            Back to Document Upload
          </button>
        </>
      ) : (
        <section className="ds-card" style={{ padding: "1.25rem", maxWidth: "640px" }}>
          <div className="ds-field">
            <span className="ds-label">Mode</span>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <label style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="quiz-mode"
                  value="learning"
                  checked={mode === "learning"}
                  onChange={() => setMode("learning")}
                />
                Learning Mode
              </label>
              <label style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="quiz-mode"
                  value="testing"
                  checked={mode === "testing"}
                  onChange={() => setMode("testing")}
                />
                Testing Mode
              </label>
            </div>
            <span style={{ color: "var(--ds-muted)", fontSize: "0.85rem" }}>
              {mode === "learning"
                ? "Correctness, the correct answer and any explanation are shown right after each answer."
                : "Correctness and answers stay hidden until the quiz is completed."}
            </span>
          </div>

          <div className="ds-field">
            <label className="ds-label" htmlFor="question-count">
              Number of questions ({questions.length} available)
            </label>
            <select
              id="question-count"
              className="ds-input"
              value={questionCount}
              onChange={(event) => setQuestionCount(Number(event.target.value))}
            >
              {questions.map((_, index) => (
                <option key={index + 1} value={index + 1}>
                  {index + 1}
                </option>
              ))}
            </select>
          </div>

          <div className="ds-field">
            <span className="ds-label">Question order</span>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <label style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="question-order"
                  value="sequential"
                  checked={questionOrder === "sequential"}
                  onChange={() => setQuestionOrder("sequential")}
                />
                Sequential
              </label>
              <label style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="question-order"
                  value="random"
                  checked={questionOrder === "random"}
                  onChange={() => setQuestionOrder("random")}
                />
                Random
              </label>
            </div>
          </div>

          {error && (
            <div className="ds-notice" role="alert" style={{ borderColor: "var(--ds-primary)", marginBottom: "1rem" }}>
              {error}
            </div>
          )}

          <button type="button" className="ds-btn ds-btn-primary" onClick={handleStart} disabled={starting}>
            {starting ? "Starting the quiz…" : "Start the quiz"}
          </button>
        </section>
      )}
    </div>
  );
};

export default Quizconfig;
