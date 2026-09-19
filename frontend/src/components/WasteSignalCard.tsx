import React from 'react';
import { LucideIcon, ArrowRight } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { SeverityLevel } from '../types';

interface WasteSignalCardProps {
  id?: string;
  title: string;
  count: number;
  countUnit?: string;
  storageImpact: string;
  severity: SeverityLevel;
  description: string;
  icon: LucideIcon;
  actionText?: string;
  onAction?: () => void;
}

export const WasteSignalCard: React.FC<WasteSignalCardProps> = ({
  id,
  title,
  count,
  countUnit = 'files',
  storageImpact,
  severity,
  description,
  icon: Icon,
  actionText = 'Review Signal',
  onAction,
}) => {
  return (
    <div
      id={id}
      className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700/80 transition-all duration-200 flex flex-col justify-between"
    >
      <div>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300">
              <Icon className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-white tracking-wide">
              {title}
            </h3>
          </div>
          <StatusBadge level={severity} size="sm" />
        </div>

        <p className="text-xs text-slate-400 mb-4 leading-relaxed line-clamp-2">
          {description}
        </p>

        <div className="grid grid-cols-2 gap-3 py-3 px-3.5 rounded-lg bg-slate-950/60 border border-slate-800/60 mb-4">
          <div>
            <div className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
              Affected Count
            </div>
            <div className="text-base font-bold text-slate-200 font-mono mt-0.5">
              {count} <span className="text-xs font-normal text-slate-400">{countUnit}</span>
            </div>
          </div>
          <div>
            <div className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
              Storage Impact
            </div>
            <div className="text-base font-bold text-amber-400 font-mono mt-0.5">
              {storageImpact}
            </div>
          </div>
        </div>
      </div>

      {onAction && (
        <button
          type="button"
          onClick={onAction}
          className="w-full inline-flex items-center justify-between px-3.5 py-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-xs font-medium text-slate-300 hover:text-white border border-slate-700/60 transition-colors"
        >
          <span>{actionText}</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
        </button>
      )}
    </div>
  );
};
