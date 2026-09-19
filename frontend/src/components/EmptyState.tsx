import React from 'react';
import { LucideIcon, FolderSearch, AlertCircle } from 'lucide-react';

interface EmptyStateProps {
  id?: string;
  icon?: LucideIcon;
  title: string;
  description?: string;
  actionText?: string;
  onAction?: () => void;
  className?: string;
  variant?: 'default' | 'warning' | 'success';
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  id,
  icon: Icon = FolderSearch,
  title,
  description,
  actionText,
  onAction,
  className = '',
  variant = 'default',
}) => {
  const iconColors = {
    default: 'text-slate-400 bg-slate-800/80 border-slate-700/60',
    warning: 'text-amber-400 bg-amber-950/40 border-amber-800/50',
    success: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/50',
  };

  return (
    <div
      id={id}
      className={`rounded-2xl border border-slate-800/80 bg-slate-900/40 p-10 text-center flex flex-col items-center justify-center ${className}`}
    >
      <div
        className={`p-4 rounded-2xl border mb-4 flex items-center justify-center ${iconColors[variant]}`}
      >
        <Icon className="w-8 h-8" />
      </div>

      <h3 className="text-base font-semibold text-white mb-1.5 tracking-tight">
        {title}
      </h3>

      {description && (
        <p className="text-xs text-slate-400 max-w-md leading-relaxed mb-5">
          {description}
        </p>
      )}

      {actionText && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-md shadow-cyan-600/20 transition-all cursor-pointer"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
