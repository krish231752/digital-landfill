import React from 'react';
import { Bot, Sparkles, ArrowRight } from 'lucide-react';

interface AIInsightCardProps {
  id?: string;
  quote?: string;
  onAnalyze?: () => void;
  statusText?: string;
  modelName?: string;
}

export const AIInsightCard: React.FC<AIInsightCardProps> = ({
  id,
  quote = 'Your largest measurable recovery opportunity comes from exact duplicate files.',
  onAnalyze,
  statusText = 'TCET CoE Qwen AI Connected',
  modelName = 'Qwen3.6-35B-A3B',
}) => {
  return (
    <div
      id={id}
      className="relative overflow-hidden rounded-xl border border-indigo-900/50 bg-gradient-to-r from-slate-900/90 via-indigo-950/20 to-slate-900/90 p-5 shadow-lg"
    >
      <div className="absolute top-0 right-0 transform translate-x-4 -translate-y-4 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
        <div className="flex items-start gap-3.5 max-w-3xl">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 shrink-0">
            <Bot className="w-5 h-5" />
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-300 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                TCET CoE Qwen
              </span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300/80 border border-indigo-800/40">
                {modelName}
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                {statusText}
              </span>
            </div>

            <p className="text-sm text-slate-200 font-medium leading-relaxed italic">
              "{quote}"
            </p>
          </div>
        </div>

        {onAnalyze && (
          <button
            type="button"
            onClick={onAnalyze}
            className="shrink-0 inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs tracking-wide shadow-md hover:shadow-indigo-500/20 transition-all cursor-pointer border border-indigo-400/30"
          >
            <span>Analyze with Qwen</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};
