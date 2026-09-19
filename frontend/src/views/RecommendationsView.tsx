import React, { useState } from 'react';
import { Sparkles, Bot, Filter, ShieldCheck, ArrowRight } from 'lucide-react';
import { NavigationTab, RecommendationItem, ScanData } from '../types';
import { SectionHeader } from '../components/SectionHeader';
import { RecommendationCard } from '../components/RecommendationCard';

interface RecommendationsViewProps {
  scanData: ScanData;
  onNavigate: (tab: NavigationTab) => void;
  onExplainWithQwen: (rec: RecommendationItem) => void;
  onTakeAction?: (rec: RecommendationItem) => void;
}

export const RecommendationsView: React.FC<RecommendationsViewProps> = ({
  scanData,
  onNavigate,
  onExplainWithQwen,
  onTakeAction,
}) => {
  const [selectedFilter, setSelectedFilter] = useState<'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');

  const recs = scanData.recommendations;
  const highCount = recs.filter((r) => r.priority === 'HIGH').length;
  const medCount = recs.filter((r) => r.priority === 'MEDIUM').length;
  const lowCount = recs.filter((r) => r.priority === 'LOW').length;

  const filteredRecs = recs.filter((r) => {
    if (selectedFilter === 'ALL') return true;
    return r.priority === selectedFilter;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      <SectionHeader
        title="AI Waste Recommendations"
        subtitle="Prioritized actions synthesized by TCET CoE Waste Intelligence engine."
        badge={
          <span className="text-xs px-2.5 py-1 rounded bg-indigo-950/60 text-indigo-300 border border-indigo-800/50 font-mono">
            {recs.length} Actionable Items
          </span>
        }
        actions={
          <button
            type="button"
            onClick={() => onNavigate('ai_intelligence')}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 text-xs font-semibold border border-indigo-500/40 transition-colors cursor-pointer"
          >
            <Bot className="w-3.5 h-3.5 text-indigo-400" />
            <span>Open Qwen Intelligence Hub</span>
          </button>
        }
      />

      {/* Top Metrics: HIGH / MEDIUM / LOW */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* HIGH */}
        <button
          type="button"
          onClick={() => setSelectedFilter(selectedFilter === 'HIGH' ? 'ALL' : 'HIGH')}
          className={`p-5 rounded-xl border text-left transition-all cursor-pointer ${
            selectedFilter === 'HIGH'
              ? 'bg-rose-950/40 border-rose-600 ring-1 ring-rose-500/30'
              : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-rose-400 font-mono">
              High Priority
            </span>
            <span className="h-2 w-2 rounded-full bg-rose-500" />
          </div>
          <div className="text-3xl font-extrabold text-white font-mono mt-2">
            {highCount}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Exact bit-for-bit duplicate waste (Instant 1.2 MB recovery)
          </p>
        </button>

        {/* MEDIUM */}
        <button
          type="button"
          onClick={() => setSelectedFilter(selectedFilter === 'MEDIUM' ? 'ALL' : 'MEDIUM')}
          className={`p-5 rounded-xl border text-left transition-all cursor-pointer ${
            selectedFilter === 'MEDIUM'
              ? 'bg-amber-950/40 border-amber-600 ring-1 ring-amber-500/30'
              : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-400 font-mono">
              Medium Priority
            </span>
            <span className="h-2 w-2 rounded-full bg-amber-500" />
          </div>
          <div className="text-3xl font-extrabold text-white font-mono mt-2">
            {medCount}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Dormant legacy documents &gt;90 days unaccessed
          </p>
        </button>

        {/* LOW */}
        <button
          type="button"
          onClick={() => setSelectedFilter(selectedFilter === 'LOW' ? 'ALL' : 'LOW')}
          className={`p-5 rounded-xl border text-left transition-all cursor-pointer ${
            selectedFilter === 'LOW'
              ? 'bg-blue-950/40 border-blue-600 ring-1 ring-blue-500/30'
              : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-blue-400 font-mono">
              Low Priority
            </span>
            <span className="h-2 w-2 rounded-full bg-blue-500" />
          </div>
          <div className="text-3xl font-extrabold text-white font-mono mt-2">
            {lowCount}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Transient session logs and rebuildable cache traces
          </p>
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-xs font-semibold text-slate-400">Filter:</span>
          {(['ALL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => setSelectedFilter(filter)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                selectedFilter === filter
                  ? 'bg-cyan-600 text-white font-semibold'
                  : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
              }`}
            >
              {filter}
            </button>
          ))}
        </div>

        <span className="text-xs text-slate-500 font-mono">
          Showing {filteredRecs.length} recommendation{filteredRecs.length === 1 ? '' : 's'}
        </span>
      </div>

      {/* Recommendation Cards */}
      <div className="space-y-4">
        {filteredRecs.map((rec) => (
          <RecommendationCard
            key={rec.id}
            recommendation={rec}
            onExplainWithQwen={onExplainWithQwen}
            onTakeAction={() => {
              if (onTakeAction) onTakeAction(rec);
              onNavigate('cleanup');
            }}
          />
        ))}
      </div>
    </div>
  );
};
