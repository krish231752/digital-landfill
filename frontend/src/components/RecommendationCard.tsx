import React from 'react';
import {
  Sparkles,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  FolderOpen,
} from 'lucide-react';
import { RecommendationItem } from '../types';
import { StatusBadge } from './StatusBadge';

interface RecommendationCardProps {
  recommendation: RecommendationItem;
  onExplainWithQwen: (rec: RecommendationItem) => void;
  onTakeAction?: (rec: RecommendationItem) => void;
}

export const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  onExplainWithQwen,
  onTakeAction,
}) => {
  return (
    <div className="rounded-xl bg-slate-900/70 border border-slate-800/80 p-5 space-y-4 hover:border-slate-700/80 transition-all duration-200">
      {/* Header with priority and affected metrics */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge level={recommendation.priority} size="sm" />
            <span className="text-xs text-slate-400 font-mono">
              {recommendation.category} • {recommendation.affectedCopiesCount} copies affected
            </span>
          </div>

          <h3 className="text-base font-semibold text-white tracking-tight">
            {recommendation.title}
          </h3>
        </div>

        <div className="sm:text-right shrink-0">
          <div className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">
            Potential Recovery
          </div>
          <div className="text-lg font-bold text-emerald-400 font-mono">
            {recommendation.potentialRecoveryFormatted}
          </div>
        </div>
      </div>

      {/* Why This Was Flagged */}
      <div className="space-y-2 rounded-lg bg-slate-950/60 p-3.5 border border-slate-800/60">
        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Why this was flagged
        </div>
        <ul className="space-y-1.5 text-xs text-slate-300">
          {recommendation.whyFlagged.map((point, idx) => (
            <li key={idx} className="flex items-start gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
              <span>{point}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Evidence confidence & Suggested Action */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
        <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800/60 space-y-1">
          <div className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider flex items-center gap-1.5">
            <ShieldCheck className="w-3 h-3 text-cyan-400" />
            Evidence Confidence
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-cyan-300 font-mono">
              {recommendation.evidenceConfidence}
            </span>
            <span className="text-[11px] text-slate-400">
              (Deterministic byte analysis)
            </span>
          </div>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800/60 space-y-1">
          <div className="text-[10px] uppercase font-semibold text-slate-500 tracking-wider">
            Suggested Action
          </div>
          <div className="text-xs text-slate-300 leading-snug">
            {recommendation.suggestedAction}
          </div>
        </div>
      </div>

      {/* Bottom actions */}
      <div className="flex items-center justify-between gap-3 pt-2 border-t border-slate-800/60 flex-wrap">
        <button
          type="button"
          onClick={() => onExplainWithQwen(recommendation)}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-indigo-950/60 hover:bg-indigo-900/60 text-indigo-300 border border-indigo-800/50 text-xs font-medium transition-colors cursor-pointer"
        >
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Explain with Qwen</span>
        </button>

        {onTakeAction && (
          <button
            type="button"
            onClick={() => onTakeAction(recommendation)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700/80 transition-colors"
          >
            <FolderOpen className="w-3.5 h-3.5 text-slate-400" />
            <span>Open in Controlled Cleanup</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};
