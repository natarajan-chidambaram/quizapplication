import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

/**
 * Quiz state shared across the four screens (R26). Persisted in
 * localStorage so the workflow survives navigation and reloads.
 */
export interface QuizAnswer {
  questionId: string;
  selectedOptionId: string;
  selectedOptionText: string;
  isCorrect?: boolean;
  correctOptionId?: string;
  correctOptionText?: string;
  explanation?: string | null;
}

export interface QuizState {
  documentId: string | null;
  documentName: string | null;
  mode: "learning" | "testing" | null;
  questionOrder: "sequential" | "random" | null;
  timerEnabled: boolean;
  timerScope: "per_question" | "per_session" | null;
  timerDurationSeconds: number;
  attemptId: string | null;
  totalQuestions: number;
  currentIndex: number;
  answers: Record<string, QuizAnswer>;
  completed: boolean;
  timerExpired: boolean;
}

const STORAGE_KEY = "quizAppState";

const EMPTY_STATE: QuizState = {
  documentId: null,
  documentName: null,
  mode: null,
  questionOrder: null,
  timerEnabled: true,
  timerScope: null,
  timerDurationSeconds: 60,
  attemptId: null,
  totalQuestions: 0,
  currentIndex: 0,
  answers: {},
  completed: false,
  timerExpired: false,
};

function loadState(): QuizState {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY_STATE };
    const parsed = JSON.parse(raw);
    return { ...EMPTY_STATE, ...parsed, answers: parsed.answers ?? {} };
  } catch {
    return { ...EMPTY_STATE };
  }
}

interface QuizStateContextValue {
  state: QuizState;
  selectDocument: (documentId: string, documentName: string) => void;
  configure: (
    mode: "learning" | "testing",
    questionOrder: "sequential" | "random",
    timerScope: "per_question" | "per_session",
    timerDurationSeconds: number,
    timerEnabled: boolean
  ) => void;
  startAttempt: (
    attemptId: string,
    totalQuestions: number,
    mode: "learning" | "testing",
    questionOrder: "sequential" | "random"
  ) => void;
  recordAnswer: (answer: QuizAnswer) => void;
  nextQuestion: () => void;
  markCompleted: () => void;
  markTimerExpired: () => void;
  resetSession: () => void;
}

const QuizStateContext = createContext<QuizStateContextValue | undefined>(undefined);

export const QuizStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<QuizState>(() => loadState());

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // storage unavailable: state still works in-memory for this page load
    }
  }, [state]);

  const selectDocument = useCallback((documentId: string, documentName: string) => {
    setState((previous) => ({ ...previous, documentId, documentName }));
  }, []);

  const configure = useCallback(
    (
      mode: "learning" | "testing",
      questionOrder: "sequential" | "random",
      timerScope: "per_question" | "per_session",
      timerDurationSeconds: number,
      timerEnabled: boolean
    ) => {
      setState((previous) => ({ ...previous, mode, questionOrder, timerEnabled, timerScope, timerDurationSeconds }));
    },
    []
  );

  const startAttempt = useCallback(
    (
      attemptId: string,
      totalQuestions: number,
      mode: "learning" | "testing",
      questionOrder: "sequential" | "random"
    ) => {
      setState((previous) => ({
        ...previous,
        attemptId,
        mode,
        questionOrder,
        totalQuestions,
        currentIndex: 0,
        answers: {},
        completed: false,
        timerExpired: false,
      }));
    },
    []
  );

  const recordAnswer = useCallback((answer: QuizAnswer) => {
    setState((previous) => ({
      ...previous,
      answers: { ...previous.answers, [answer.questionId]: answer },
    }));
  }, []);

  const nextQuestion = useCallback(() => {
    setState((previous) => {
      if (previous.currentIndex + 1 >= previous.totalQuestions) {
        return { ...previous, completed: true };
      }
      return { ...previous, currentIndex: previous.currentIndex + 1 };
    });
  }, []);

  const markCompleted = useCallback(() => {
    setState((previous) => ({ ...previous, completed: true }));
  }, []);

  // Timer expiry: the countdown hit 00:00, so Results must open even with
  // unanswered questions (they are reported in the UNANSWERED tile).
  const markTimerExpired = useCallback(() => {
    setState((previous) => ({ ...previous, completed: true, timerExpired: true }));
  }, []);

  const resetSession = useCallback(() => {
    // Restart (R25): keep only the chosen document, go back to configuration.
    setState((previous) => ({
      documentId: previous.documentId,
      documentName: previous.documentName,
      mode: null,
      questionOrder: null,
      timerEnabled: previous.timerEnabled,
      timerScope: previous.timerScope,
      timerDurationSeconds: previous.timerDurationSeconds,
      attemptId: null,
      totalQuestions: 0,
      currentIndex: 0,
      answers: {},
      completed: false,
      timerExpired: false,
    }));
  }, []);

  const value = useMemo(
    () => ({ state, selectDocument, configure, startAttempt, recordAnswer, nextQuestion, markCompleted, markTimerExpired, resetSession }),
    [state, selectDocument, configure, startAttempt, recordAnswer, nextQuestion, markCompleted, markTimerExpired, resetSession]
  );

  return <QuizStateContext.Provider value={value}>{children}</QuizStateContext.Provider>;
};

export function useQuizState(): QuizStateContextValue {
  const context = useContext(QuizStateContext);
  if (!context) {
    throw new Error("useQuizState must be used inside a QuizStateProvider");
  }
  return context;
}
