import React from 'react';
import { SeverityLevel } from '../types';

interface StatusBadgeProps {
  level: SeverityLevel | 'Active' | 'Duplicate' | 'Redundant' | 'Stale' | 'Temporary' | 'Connected' | 'Online' | 'Analyzed';
  size?: 'sm' | 'md';
  pulse?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  level,
  size = 'md',
  pulse = false,
}) => {
  const sizeClasses =
    size === 'sm'
      ? 'text-xs px-2 py-0.5'
      : 'text-xs font-semibold px-2.5 py-1';

  let colorClasses = 'bg-slate-800/80 text-slate-300 border-slate-700/60';
  let dotColor = 'bg-slate-400';

  switch (level) {
    case 'CRITICAL':
    case 'HIGH':
      colorClasses = 'bg-rose-950/40 text-rose-300 border-rose-800/50';
      dotColor = 'bg-rose-500';
      break;
    case 'MEDIUM':
    case 'Stale':
      colorClasses = 'bg-amber-950/40 text-amber-300 border-amber-800/50';
      dotColor = 'bg-amber-400';
      break;
    case 'LOW':
    case 'Temporary':
      colorClasses = 'bg-blue-950/40 text-blue-300 border-blue-800/50';
      dotColor = 'bg-blue-400';
      break;
    case 'Online':
    case 'Connected':
    case 'Analyzed':
    case 'Active':
      colorClasses = 'bg-emerald-950/40 text-emerald-300 border-emerald-800/50';
      dotColor = 'bg-emerald-400';
      break;
    case 'Duplicate':
    case 'Redundant':
      colorClasses = 'bg-purple-950/40 text-purple-300 border-purple-800/50';
      dotColor = 'bg-purple-400';
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${sizeClasses} ${colorClasses} tracking-wide transition-colors`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${dotColor} ${
          pulse ? 'animate-pulse' : ''
        }`}
      />
      <span>{level}</span>
    </span>
  );
};
