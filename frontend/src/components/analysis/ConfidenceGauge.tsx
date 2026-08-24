import { useMemo } from 'react';

interface ConfidenceGaugeProps {
  score: number;
}

export function ConfidenceGauge({ score }: ConfidenceGaugeProps) {
  const { color, bgColor, label } = useMemo(() => {
    if (score >= 80)
      return { color: 'text-green-600', bgColor: 'stroke-green-500', label: 'High Confidence' };
    if (score >= 60)
      return { color: 'text-amber-600', bgColor: 'stroke-amber-500', label: 'Needs Review' };
    return { color: 'text-red-600', bgColor: 'stroke-red-500', label: 'Significant Gaps' };
  }, [score]);

  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative h-32 w-32">
        <svg className="h-32 w-32 -rotate-90">
          <circle
            cx="64"
            cy="64"
            r="45"
            stroke="#e5e7eb"
            strokeWidth="10"
            fill="none"
          />
          <circle
            cx="64"
            cy="64"
            r="45"
            strokeWidth="10"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={bgColor}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-2xl font-bold ${color}`}>{Math.round(score)}%</span>
        </div>
      </div>
      <p className={`mt-2 text-sm font-medium ${color}`}>{label}</p>
    </div>
  );
}
