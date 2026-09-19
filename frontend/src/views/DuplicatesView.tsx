import React from 'react';
import {
  Copy,
  ShieldCheck,
  FolderOpen,
  ArrowRight,
  Info,
  CheckCircle2,
} from 'lucide-react';
import { DuplicateGroup, FileItem, NavigationTab, ScanData } from '../types';
import { SectionHeader } from '../components/SectionHeader';
import { MetricCard } from '../components/MetricCard';
import { DuplicateGroupCard } from '../components/DuplicateGroupCard';
import { EmptyState } from '../components/EmptyState';

interface DuplicatesViewProps {
  scanData: ScanData;
  onNavigate: (tab: NavigationTab) => void;
  onSendToCleanup: (file: FileItem) => void;
  onReviewInInventory: (file: FileItem) => void;
}

export const DuplicatesView: React.FC<DuplicatesViewProps> = ({
  scanData,
  onNavigate,
  onSendToCleanup,
  onReviewInInventory,
}) => {
  const groups = scanData.duplicateGroups;

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      <SectionHeader
        title="Duplicate Intelligence"
        subtitle="Cryptographically verified bit-for-bit duplicate files across scanned folders."
        actions={
          <button
            type="button"
            onClick={() => onNavigate('cleanup')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-md shadow-cyan-600/20 transition-all cursor-pointer"
          >
            <span>Review Duplicates in Cleanup</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        }
      />

      {/* Top Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          id="duplicate-groups-metric"
          label="Duplicate Groups"
          value={groups.length}
          subtext="Unique file content hashes"
          icon={Copy}
          iconColor="text-purple-400"
          iconBg="bg-purple-500/10 border-purple-500/20"
          trend={{ value: `${scanData.signals.duplicates.count} redundant copies`, isNeutral: true }}
        />

        <MetricCard
          id="redundant-storage-metric"
          label="Redundant Storage"
          value={scanData.duplicateWasteFormatted}
          subtext="Unnecessary disk footprint"
          icon={ShieldCheck}
          iconColor="text-amber-400"
          iconBg="bg-amber-500/10 border-amber-500/20"
          trend={{ value: 'Measurable waste', isPositive: false }}
        />

        <MetricCard
          id="duplicate-recovery-metric"
          label="Potential Recovery"
          value={scanData.duplicateWasteFormatted}
          subtext="Reclaimable without data loss"
          icon={CheckCircle2}
          iconColor="text-emerald-400"
          iconBg="bg-emerald-500/10 border-emerald-500/20"
          trend={{ value: '100% Risk-free', isPositive: true }}
        />
      </div>

      {/* Safeguard Assurance Notice */}
      <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 flex items-start gap-3.5 text-xs text-slate-300">
        <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-semibold text-white">
            Digital Landfill Safety Protocol:
          </span>{' '}
          Duplicates are detected via SHA-256 byte hashing. Deletion is{' '}
          <strong className="text-white">never automated</strong>. You can expand each group below to view identical paths, inspect SHA-256 evidence, and choose individual redundant copies to stage in Controlled Cleanup.
        </div>
      </div>

      {/* Duplicate Groups List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono">
            Detected Duplicate Groups ({groups.length})
          </h2>
          <span className="text-xs text-slate-500">
            Click "View Files" or "Review Evidence" to inspect
          </span>
        </div>

        {groups.length === 0 ? (
          <EmptyState
            title="No exact duplicates detected."
            description="All indexed files have distinct cryptographic SHA-256 checksums. No byte-level redundancy was identified."
            variant="success"
          />
        ) : (
          <div className="space-y-4">
            {groups.map((group) => (
              <DuplicateGroupCard
                key={group.id}
                group={group}
                onSendToCleanup={onSendToCleanup}
                onReviewInInventory={onReviewInInventory}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
