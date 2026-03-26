'use client';

import { useState, useMemo } from 'react';
import { CheckCircle2, XCircle, ChevronRight, Trophy, RotateCcw, ChevronDown } from 'lucide-react';

export default function InlineQuizView({ quiz, onClose }) {
  const questions = useMemo(() => quiz?.questions || [], [quiz]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [showExplanation, setShowExplanation] = useState(false);
  const [completed, setCompleted] = useState(false);

  const question = questions[currentIndex];
  const selectedAnswer = answers[currentIndex];
  const hasAnswered = selectedAnswer !== undefined;

  const score = useMemo(() => {
    let correct = 0;
    Object.entries(answers).forEach(([idx, ans]) => {
      if (questions[Number(idx)]?.correct_answer === ans) correct++;
    });
    return correct;
  }, [answers, questions]);

  const handleSelect = (optionIndex) => {
    if (hasAnswered) return;
    setAnswers((prev) => ({ ...prev, [currentIndex]: optionIndex }));
    setShowExplanation(true);
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((i) => i + 1);
      setShowExplanation(false);
    } else {
      setCompleted(true);
    }
  };

  const handleRestart = () => {
    setCurrentIndex(0);
    setAnswers({});
    setShowExplanation(false);
    setCompleted(false);
  };

  if (!questions.length) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-sm text-[var(--text-muted)]">No quiz available</p>
      </div>
    );
  }

  
  if (completed) {
    const pct = Math.round((score / questions.length) * 100);
    return (
      <div className="space-y-5 animate-fade-in py-3">
        <div
          className="relative overflow-hidden rounded-2xl border border-[var(--border)] p-5 text-center"
          style={{
            background:
              'radial-gradient(circle at top right, var(--accent-subtle), transparent 45%), linear-gradient(180deg, var(--surface-raised), var(--surface))',
          }}
        >
          <Trophy className={`mx-auto h-10 w-10 ${pct >= 70 ? 'text-yellow-400' : 'text-[var(--text-muted)]'}`} />
          <p className="mt-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-muted)]">Final Score</p>
          <p className="mt-1 text-4xl font-bold text-[var(--text-primary)]">{pct}%</p>
          <p className="text-sm text-[var(--text-secondary)]">
            {score} of {questions.length} correct answers
          </p>
          <div className="mx-auto mt-4 h-2 w-full max-w-xs overflow-hidden rounded-full bg-[var(--surface-overlay)]">
            <div className="h-full rounded-full bg-[var(--accent)] transition-all duration-700" style={{ width: `${pct}%` }} />
          </div>
        </div>

        <p className="text-center text-xs text-[var(--text-muted)]">
          {pct >= 90 ? 'Excellent!' : pct >= 70 ? 'Great job!' : pct >= 50 ? 'Good attempt!' : 'Keep studying!'}
        </p>

        <div className="flex items-center justify-center gap-2">
          <button
            onClick={handleRestart}
            className="inline-flex items-center gap-2 rounded-lg border border-[var(--accent-border)] bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-light)]"
          >
            <RotateCcw className="h-4 w-4" /> Retry Quiz
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      <div
        className="rounded-2xl border border-[var(--border)] p-3 sm:p-4"
        style={{
          background:
            'radial-gradient(circle at top right, var(--accent-subtle), transparent 45%), linear-gradient(180deg, var(--surface-raised), var(--surface))',
        }}
      >
        <div className="mb-2 flex items-center justify-between text-[11px] text-[var(--text-muted)]">
          <span className="uppercase tracking-[0.16em]">Quiz Progress</span>
          <span className="font-semibold text-[var(--text-secondary)] tabular-nums">
            {currentIndex + 1}/{questions.length}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--surface-overlay)]">
            <div
              className="h-full rounded-full bg-[var(--accent)] transition-all duration-500"
              style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
            />
          </div>
          <span className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-[10px] uppercase tracking-[0.1em] text-[var(--text-secondary)]">
            {Math.round(((currentIndex + 1) / questions.length) * 100)}%
          </span>
        </div>
      </div>

      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-raised)] p-4 sm:p-5">
        <div className="mb-3 inline-flex rounded-full border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
          Question
        </div>
        <p className="text-lg font-semibold leading-relaxed text-[var(--text-primary)]">
          {question.question || question.text}
        </p>
      </div>

      <div className="space-y-2.5">
        {(question.options || []).map((opt, i) => {
          const isSelected = selectedAnswer === i;
          const isCorrectOption = i === question.correct_answer;
          let optionClass = 'border-[var(--border)] bg-[var(--surface-raised)] hover:border-[var(--accent-border)] hover:bg-[var(--surface)]';

          if (hasAnswered) {
            if (isCorrectOption) {
              optionClass = 'border-green-500/50 bg-green-500/10';
            } else if (isSelected && !isCorrectOption) {
              optionClass = 'border-red-500/50 bg-red-500/10';
            } else {
              optionClass = 'border-[var(--border)] bg-[var(--surface-raised)] opacity-60';
            }
          } else if (isSelected) {
            optionClass = 'border-[var(--accent)] bg-[var(--accent-subtle)]';
          }

          return (
            <button
              key={i}
              onClick={() => handleSelect(i)}
              disabled={hasAnswered}
              className={`w-full rounded-xl border px-4 py-3 text-left transition-all ${optionClass}`}
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[var(--border-strong)] text-[11px] font-bold text-[var(--text-secondary)]">
                  {String.fromCharCode(65 + i)}
                </span>
                <span className="flex-1 text-[15px] font-medium text-[var(--text-primary)]">
                  {typeof opt === 'string' ? opt : opt.text}
                </span>
                {hasAnswered && isCorrectOption && <CheckCircle2 className="h-[18px] w-[18px] shrink-0 text-green-400" />}
                {hasAnswered && isSelected && !isCorrectOption && <XCircle className="h-[18px] w-[18px] shrink-0 text-red-400" />}
              </div>
            </button>
          );
        })}
      </div>

      {hasAnswered && question.explanation && (
        <div className="animate-fade-in rounded-xl border border-[var(--accent-border)] bg-[var(--accent-subtle)] p-3">
          <button
            onClick={() => setShowExplanation(!showExplanation)}
            className="flex items-center gap-1 text-xs font-medium text-[var(--accent)]"
          >
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${showExplanation ? 'rotate-180' : ''}`} />
            {showExplanation ? 'Hide' : 'Show'} explanation
          </button>
          {showExplanation && (
            <p className="mt-2 border-l-2 border-[var(--accent-border)] pl-3 text-sm leading-relaxed text-[var(--text-secondary)]">
              {question.explanation}
            </p>
          )}
        </div>
      )}

      {hasAnswered && (
        <button
          onClick={handleNext}
          className="w-full animate-fade-in rounded-xl bg-[var(--accent)] py-3 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-light)]"
        >
          <span className="inline-flex items-center justify-center gap-2">
            {currentIndex < questions.length - 1 ? (
              <>Next Question <ChevronRight className="h-4 w-4" /></>
            ) : (
              'See Results'
            )}
          </span>
        </button>
      )}
    </div>
  );
}
