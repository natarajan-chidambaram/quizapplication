import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import quizApi, { ApiError } from "../api/quizApi";
import { useQuizState, QuizAnswer } from "../context/QuizStateContext";

/**
 * Screen 3 — Quiz Session (R12-R20).
 * ONE question per page, options extracted from the uploaded document,
 * single immutable answer, no skipping, progress bar and a Next button
 * that stays disabled until the current question is answered.
 * Learning Mode: immediate feedback (correct answer + explanation) and a
 * cheerful Jerry avatar that claps on correct answers.
 * Testing Mode: no correctness or answers are revealed here (R20).
 */
const Quizsession: React.FC = () => {
  const navigate = useNavigate();
  const { state, recordAnswer, nextQuestion, selectDocument } = useQuizState();
  const attemptId = state.attemptId;
  const currentIndex = state.currentIndex;
  const mode = state.mode;

  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [answerResult, setAnswerResult] = useState<any>(null);
  // Document picker (R34): the user clicks which uploaded document the quiz
  // is based on, directly on the Quiz Session screen, then proceeds.
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(state.documentId);
  const [docsLoading, setDocsLoading] = useState(false);

  // Timer (R29-R33): driven by the TimerSetting chosen on the configuration
  // screen and persisted with the attempt. "per_question" restarts for every
  // question; "per_session" counts the whole quiz. Green while more than 25%
  // of the allotted time remains, red once 75% of it has elapsed.
  const timerEnabled = session?.timer ? Boolean(session.timer.enabled) : true;
  const timerScope = ((session?.timer?.scope as "per_question" | "per_session" | undefined) ?? state.timerScope ?? "per_question");
  const allottedSeconds = session?.timer?.durationSeconds ?? state.timerDurationSeconds ?? 60;
  const [remainingSeconds, setRemainingSeconds] = useState<number>(allottedSeconds);
  const [timeUp, setTimeUp] = useState(false);
  const timerAnchors = useRef<{ sessionStart: number | null; questionIndex: number; questionStart: number }>({
    sessionStart: null,
    questionIndex: -1,
    questionStart: 0,
  });

  useEffect(() => {
    if (!attemptId || !timerEnabled) return;
    // Restore the anchors so a page reload does not reset the countdown.
    try {
      const raw = window.localStorage.getItem("quizTimerState");
      if (raw) {
        const saved = JSON.parse(raw);
        if (saved.attemptId === attemptId && saved.scope === timerScope) {
          timerAnchors.current = {
            sessionStart: saved.sessionStart ?? null,
            questionIndex: typeof saved.questionIndex === "number" ? saved.questionIndex : -1,
            questionStart: saved.questionStart ?? 0,
          };
        }
      }
    } catch {
      // no saved timer state: start fresh
    }
    const now = Date.now();
    if (timerScope === "per_session" && timerAnchors.current.sessionStart == null) {
      timerAnchors.current.sessionStart = now;
    }
    if (timerScope === "per_question" && timerAnchors.current.questionIndex !== currentIndex) {
      timerAnchors.current.questionIndex = currentIndex; // reset for this question (R30)
      timerAnchors.current.questionStart = now;
    }
    setTimeUp(false);
    const computeRemaining = () => {
      const anchor =
        timerScope === "per_session"
          ? timerAnchors.current.sessionStart ?? Date.now()
          : timerAnchors.current.questionStart || Date.now();
      const elapsed = Math.max(0, Math.floor((Date.now() - anchor) / 1000));
      return Math.max(0, allottedSeconds - elapsed);
    };
    setRemainingSeconds(computeRemaining());
    const interval = window.setInterval(() => {
      const remaining = computeRemaining();
      setRemainingSeconds(remaining);
      try {
        window.localStorage.setItem(
          "quizTimerState",
          JSON.stringify({
            attemptId,
            scope: timerScope,
            sessionStart: timerAnchors.current.sessionStart,
            questionIndex: timerAnchors.current.questionIndex,
            questionStart: timerAnchors.current.questionStart,
          })
        );
      } catch {
        // storage unavailable: the timer still works for this page load
      }
      if (remaining <= 0) {
        setTimeUp(true);
        window.clearInterval(interval);
      }
    }, 1000);
    return () => window.clearInterval(interval);
  }, [attemptId, currentIndex, timerEnabled, timerScope, allottedSeconds]);

  const formatTime = (seconds: number): string => {
    const safe = Math.max(0, seconds);
    const minutes = Math.floor(safe / 60);
    const rest = safe % 60;
    return `${minutes}:${rest.toString().padStart(2, "0")}`;
  };
  // Red once 75% of the allotted time has elapsed (R33).
  const timerWarning = remainingSeconds <= Math.ceil(allottedSeconds * 0.25);

  const loadSession = useCallback(
    async (index: number, attempt: string) => {
      setLoading(true);
      setError(null);
      try {
        const data = await quizApi.getSession(attempt, index);
        setSession(data);
        setSelectedOptionId(data.selectedOptionId ?? null);
        setAnswerResult(null);
      } catch (err: any) {
        setError(err?.detail || "The quiz session could not be loaded");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (!attemptId) {
      setError("No quiz in progress. Configure and start a quiz first.");
      setLoading(false);
      return;
    }
    loadSession(currentIndex, attemptId);
  }, [attemptId, currentIndex, loadSession]);

  // Document picker (R34): load the uploaded documents when no quiz is running.
  useEffect(() => {
    if (attemptId) return;
    let cancelled = false;
    setDocsLoading(true);
    quizApi
      .listDocuments()
      .then((data: any) => {
        if (!cancelled) setDocuments(Array.isArray(data) ? data : data?.data ?? []);
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setDocsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attemptId]);

  // Document picker (R34): click a document to base the quiz on and proceed
  // to Quiz Configuration, which starts the session for that document.
  const proceedToConfiguration = useCallback(() => {
    if (!selectedDocId) return;
    const doc = documents.find((item) => item.id === selectedDocId);
    selectDocument(selectedDocId, doc?.fileName ?? "document");
    navigate("/configure");
  }, [documents, navigate, selectDocument, selectedDocId]);

  const alreadyAnswered = Boolean(session?.answered);

  const handleSelect = (optionId: string) => {
    if (alreadyAnswered || submitting) return;
    setSelectedOptionId(optionId);
  };

  const handleSubmit = useCallback(async () => {
    if (!attemptId || !session?.question || !selectedOptionId || alreadyAnswered) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await quizApi.submitAnswer(attemptId, session.question.id, selectedOptionId);
      const selectedOption = session.question.options.find(
        (option: any) => option.id === selectedOptionId
      );
      const answer: QuizAnswer = {
        questionId: session.question.id,
        selectedOptionId,
        selectedOptionText: selectedOption?.optionText ?? "",
      };
      if (mode === "learning") {
        answer.isCorrect = result.isMarkedCorrect;
        answer.correctOptionId = result.correctOptionId;
        answer.correctOptionText = result.correctOptionText;
        answer.explanation = result.explanation;
      }
      setAnswerResult(result);
      recordAnswer(answer);
      // reflect the immutability immediately (R14)
      setSession((previous: any) => ({ ...previous, answered: true, selectedOptionId }));
    } catch (err: any) {
      setError(err?.detail || "The answer could not be saved");
    } finally {
      setSubmitting(false);
    }
  }, [alreadyAnswered, attemptId, mode, recordAnswer, selectedOptionId, session]);

  const handleNext = useCallback(() => {
    if (!alreadyAnswered) return;
    nextQuestion(); // the context sets completed=true after the last question
    if (currentIndex + 1 >= state.totalQuestions) {
      navigate("/results");
    }
  }, [alreadyAnswered, currentIndex, navigate, nextQuestion, state.totalQuestions]);

  if (!attemptId) {
    return (
      <div className="ds-section">
        <h1 className="ds-heading">Quiz Session</h1>
        <div className="ds-notice" role="alert">
          No quiz in progress. Pick an uploaded document to base the quiz on.
        </div>

        {/* Document picker (R34): click which document to base the quiz on. */}
        <section className="ds-card" style={{ marginTop: "1rem", padding: "1.25rem", maxWidth: "720px" }}>
          <h2 className="ds-heading" style={{ fontSize: "1.2rem" }}>
            Choose the document for this quiz
          </h2>
          {docsLoading ? (
            <p style={{ color: "var(--ds-muted)" }}>Loading documents…</p>
          ) : documents.length === 0 ? (
            <p style={{ color: "var(--ds-muted)" }}>
              No documents uploaded yet — upload one on the Document Upload screen first.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  type="button"
                  className={`quiz-option ${selectedDocId === doc.id ? "quiz-option--selected" : ""}`}
                  onClick={() => setSelectedDocId(doc.id)}
                  aria-pressed={selectedDocId === doc.id}
                >
                  <span>{selectedDocId === doc.id ? "🔘" : "⚪"}</span>
                  <span>{doc.fileName}</span>
                </button>
              ))}
            </div>
          )}
          <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem", flexWrap: "wrap" }}>
            <button
              type="button"
              className="ds-btn ds-btn-primary"
              onClick={proceedToConfiguration}
              disabled={!selectedDocId}
            >
              Proceed to Quiz Configuration →
            </button>
            <button type="button" className="ds-btn" onClick={() => navigate("/")}>
              Upload a document instead
            </button>
          </div>
        </section>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="ds-section">
        <h1 className="ds-heading">Quiz Session</h1>
        <p style={{ color: "var(--ds-muted)" }}>Loading question…</p>
      </div>
    );
  }

  if (error && !session) {
    return (
      <div className="ds-section">
        <h1 className="ds-heading">Quiz Session</h1>
        <div className="ds-notice" role="alert">
          {error}
        </div>
        <button type="button" className="ds-btn ds-btn-primary" style={{ marginTop: "1rem" }} onClick={() => navigate("/configure")}>
          Go to Quiz Configuration
        </button>
      </div>
    );
  }

  const question = session?.question;
  const total = session?.totalQuestions ?? state.totalQuestions;
  const answeredCount = session?.answeredCount ?? 0;
  const isLearning = mode === "learning";
  const isCorrect = isLearning && answerResult?.isMarkedCorrect === true;
  const isWrong = isLearning && answerResult && answerResult.isMarkedCorrect === false;

  return (
    <div className="ds-section">
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
        <h1 className="ds-heading" style={{ marginBottom: 0 }}>
          Question {currentIndex + 1} of {total}
        </h1>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
          {timerEnabled && (
            <div
              className={`quiz-timer ${timerWarning ? "quiz-timer--warning" : ""}`}
              role="timer"
              aria-label={
                timerScope === "per_question"
                  ? "Remaining time for this question"
                  : "Remaining time for the entire session"
              }
            >
              <span aria-hidden="true">⏱</span>
              <span>
                {timeUp
                  ? "Time is up"
                  : `${formatTime(remainingSeconds)} ${timerScope === "per_question" ? "left for this question" : "left in the session"}`}
              </span>
            </div>
          )}
          <span className="ds-badge">{isLearning ? "Learning Mode" : "Testing Mode"}</span>
        </div>
      </div>

      <div className="quiz-progress" style={{ marginTop: "0.75rem" }} aria-label="Quiz progress">
        <div className="quiz-progress-bar" style={{ width: `${total ? Math.round(((currentIndex + (alreadyAnswered ? 1 : 0)) / total) * 100) : 0}%` }} />
      </div>
      <p style={{ color: "var(--ds-muted)" }}>
        {answeredCount} of {total} answered — every question must be answered before the Results unlock.
      </p>

      {error && (
        <div className="ds-notice" role="alert" style={{ borderColor: "var(--ds-primary)", marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {question && (
        <section className="ds-card" style={{ padding: "1.25rem", maxWidth: "720px" }}>
          <p style={{ fontWeight: 700, fontSize: "1.15rem", marginTop: 0 }}>{question.text}</p>

          <div>
            {question.options.map((option: any) => {
              const selected = selectedOptionId === option.id;
              let extraClass = "";
              if (isLearning && alreadyAnswered) {
                if (option.id === answerResult?.correctOptionId) extraClass = "quiz-option--correct";
                else if (selected) extraClass = "quiz-option--incorrect";
              }
              return (
                <button
                  key={option.id}
                  type="button"
                  className={`quiz-option ${selected ? "quiz-option--selected" : ""} ${extraClass}`}
                  onClick={() => handleSelect(option.id)}
                  disabled={alreadyAnswered || submitting}
                  aria-pressed={selected}
                >
                  <span>{selected ? "🔘" : "⚪"}</span>
                  <span>{option.optionText}</span>
                </button>
              );
            })}
          </div>

          {isLearning && alreadyAnswered && (
            <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", marginTop: "1rem", flexWrap: "wrap" }}>
              <div
                className={`jerry-avatar ${isCorrect ? "jerry-avatar--cheer" : ""}`}
                role="img"
                aria-label={isCorrect ? "Jerry the mouse clapping" : "Jerry the mouse"}
              >
                {isCorrect ? "🐭👏" : "🐭"}
              </div>
              <div>
                {isCorrect && (
                  <>
                    <p className="feedback-correct" style={{ margin: 0 }}>
                      Correct answer! Jerry is clapping for you 🎉
                    </p>
                  </>
                )}
                {isWrong && (
                  <p className="feedback-incorrect" style={{ margin: 0 }}>
                    Not quite — here is the correct answer.
                  </p>
                )}
                {answerResult?.correctOptionText && (
                  <p style={{ margin: "0.25rem 0 0" }}>
                    Correct answer: <strong>{answerResult.correctOptionText}</strong>
                  </p>
                )}
                {answerResult?.explanation && (
                  <p style={{ margin: "0.25rem 0 0", color: "var(--ds-muted)" }}>
                    Explanation: {answerResult.explanation}
                  </p>
                )}
              </div>
            </div>
          )}

          <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.25rem", flexWrap: "wrap" }}>
            <button
              type="button"
              className="ds-btn ds-btn-primary"
              onClick={handleSubmit}
              disabled={!selectedOptionId || alreadyAnswered || submitting}
            >
              {submitting ? "Saving your answer…" : alreadyAnswered ? "Answer saved (cannot be changed)" : "Submit answer"}
            </button>
            <button type="button" className="ds-btn" onClick={handleNext} disabled={!alreadyAnswered}>
              {currentIndex + 1 >= total ? "Finish and see results →" : "Next question →"}
            </button>
          </div>
          {!alreadyAnswered && (
            <p style={{ color: "var(--ds-muted)", marginBottom: 0 }}>
              You cannot skip this question — answer it to move on.
            </p>
          )}
        </section>
      )}
    </div>
  );
};

export default Quizsession;
