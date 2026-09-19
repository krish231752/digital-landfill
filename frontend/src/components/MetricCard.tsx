import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  id?: string;
  label: string;
  value: string | number;
  subtext?: string;
  icon: LucideIcon;
  iconColor?: string;
  iconBg?: string;
  badge?: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
    isNeutral?: boolean;
  };
  onClick?: () => void;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  id,
  label,
  value,
  subtext,
  icon: Icon,
  iconColor = 'text-cyan-400',
  iconBg = 'bg-cyan-500/10 border-cyan-500/20',
  badge,
  trend,
  onClick,
}) => {
  return (
    <div
      id={id}
      onClick={onClick}
      className={`relative p-5 rounded-xl bg-slate-900/70 border border-slate-800/80 transition-all duration-200 ${
        onClick
          ? 'cursor-pointer hover:border-slate-700 hover:bg-slate-900/90'
          : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-3">
        <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
          {label}
        </span>
        <div
          className={`p-2 rounded-lg border ${iconBg} ${iconColor} flex items-center justify-center`}
        >
          <Icon className="w-4 h-4" />
        </div>
      </div>

      <div className="flex items-baseline justify-between gap-3">
        <div className="text-2xl font-bold tracking-tight text-white font-mono">
          {value}
        </div>
        {badge}
      </div>

      {(subtext || trend) && (
        <div className="mt-2.5 flex items-center gap-2 text-xs text-slate-400">
          {trend && (
            <span
              className={`font-medium ${
                trend.isNeutral
                  ? 'text-slate-400'
                  : trend.isPositive
                  ? 'text-emerald-400'
                  : 'text-amber-400'
              }`}
            >
              {trend.value}
            </span>
          )}
          {subtext && <span className="truncate">{subtext}</span>}
        </div>
      )}
    </div>
  );
};
