'use client';

import { useState, useMemo, useCallback } from 'react';
import { CheckCircle2, XCircle, ChevronRight, Trophy, RotateCcw, ChevronDown } from 'lucide-react';

export default function InlineQuizView({ quiz, onClose }) {
  const questions = useMemo(() => quiz?.questions || [], [quiz]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [showExplanation, setShowExplanation] = useState(false);
  const [completed, setCompleted] = useState(false);

  const question = questions[currentIndex];
  const selectedAnswer = answers[currentIndex];
  const isCorrect = selectedAnswer !== undefined && selectedAnswer === question?.correct_answer;
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
        <p className="text-sm text-(--text-muted)">No quiz available</p>
      </div>
    );
  }

  // Score Summary
  if (completed) {
    const pct = Math.round((score / questions.length) * 100);
    return (
      <div className="space-y-4 animate-fade-in text-center py-6">
        <Trophy className={`w-10 h-10 mx-auto ${pct >= 70 ? 'text-yellow-400' : 'text-(--text-muted)'}`} />
        <div>
          <p className="text-2xl font-bold text-(--text-primary)">{pct}%</p>
          <p className="text-sm text-(--text-secondary)">
            {score} of {questions.length} correct
          </p>
        </div>
        <p className="text-xs text-(--text-muted)">
          {pct >= 90 ? 'Excellent!' : pct >= 70 ? 'Great job!' : pct >= 50 ? 'Good attempt!' : 'Keep studying!'}
        </p>
        <button
          onClick={handleRestart}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-(--accent) text-white text-sm hover:bg-(--accent-light) transition-colors"
        >
          <RotateCcw className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Progress */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 rounded-full bg-(--surface) overflow-hidden">
          <div
            className="h-full rounded-full bg-(--accent) transition-all"
            style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
          />
        </div>
        <span className="text-xs text-(--text-muted) tabular-nums">
          {currentIndex + 1}/{questions.length}
        </span>
      </div>

      {/* Question */}
      <div>
        <p className="text-sm font-medium text-(--text-primary) leading-relaxed">
          {question.question || question.text}
        </p>
      </div>

      {/* Options */}
      <div className="space-y-2">
        {(question.options || []).map((opt, i) => {
          const isSelected = selectedAnswer === i;
          const isCorrectOption = i === question.correct_answer;
          let optionClass = 'border-(--border) hover:border-(--text-muted)';

          if (hasAnswered) {
            if (isCorrectOption) {
              optionClass = 'border-green-500/50 bg-green-500/10';
            } else if (isSelected && !isCorrectOption) {
              optionClass = 'border-red-500/50 bg-red-500/10';
            } else {
              optionClass = 'border-(--border) opacity-50';
            }
          } else if (isSelected) {
            optionClass = 'border-(--accent) bg-(--accent)/5';
          }

          return (
            <button
              key={i}
              onClick={() => handleSelect(i)}
              disabled={hasAnswered}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border text-left transition-all ${optionClass}`}
            >
              <span className="w-6 h-6 flex items-center justify-center rounded-full border border-current text-[10px] font-bold shrink-0 text-(--text-secondary)">
                {String.fromCharCode(65 + i)}
              </span>
              <span className="flex-1 text-sm text-(--text-primary)">{typeof opt === 'string' ? opt : opt.text}</span>
              {hasAnswered && isCorrectOption && <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" />}
              {hasAnswered && isSelected && !isCorrectOption && <XCircle className="w-4 h-4 text-red-400 shrink-0" />}
            </button>
          );
        })}
      </div>

      {/* Explanation */}
      {hasAnswered && question.explanation && (
        <div className="animate-fade-in">
          <button
            onClick={() => setShowExplanation(!showExplanation)}
            className="flex items-center gap-1 text-xs text-(--accent) hover:underline"
          >
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showExplanation ? 'rotate-180' : ''}`} />
            {showExplanation ? 'Hide' : 'Show'} explanation
          </button>
          {showExplanation && (
            <p className="mt-2 text-xs text-(--text-secondary) pl-3 border-l-2 border-(--accent)/30 leading-relaxed">
              {question.explanation}
            </p>
          )}
        </div>
      )}

      {/* Next button */}
      {hasAnswered && (
        <button
          onClick={handleNext}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-(--accent) text-white text-sm font-medium hover:bg-(--accent-light) transition-colors animate-fade-in"
        >
          {currentIndex < questions.length - 1 ? (
            <>Next <ChevronRight className="w-4 h-4" /></>
          ) : (
            'See Results'
          )}
        </button>
      )}
    </div>
  );
}
