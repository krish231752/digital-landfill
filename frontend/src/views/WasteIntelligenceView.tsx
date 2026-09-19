import React, { useState } from 'react';
import {
  BarChart3,
  HardDrive,
  Clock,
  Trash2,
  Sliders,
  Gauge,
  ArrowRight,
  ShieldAlert,
  FileText,
  FileCheck,
  AlertTriangle,
} from 'lucide-react';
import { FileItem, NavigationTab, ScanData } from '../types';
import { SectionHeader } from '../components/SectionHeader';
import { StatusBadge } from '../components/StatusBadge';
import { StorageDistributionChart } from '../components/StorageDistributionChart';
import { formatBytes } from '../data/mockData';

interface WasteIntelligenceViewProps {
  scanData: ScanData;
  onNavigate: (tab: NavigationTab) => void;
  onSendToCleanup?: (file: FileItem) => void;
}

export const WasteIntelligenceView: React.FC<WasteIntelligenceViewProps> = ({
  scanData,
  onNavigate,
  onSendToCleanup,
}) => {
  // Recovery Simulator State
  const [includeDuplicates, setIncludeDuplicates] = useState(true);
  const [includeTemp, setIncludeTemp] = useState(true);
  const [includeStaleContract, setIncludeStaleContract] = useState(false);

  const duplicateWasteBytes = scanData.duplicateWasteBytes;
  const tempWasteBytes = scanData.signals.tempFiles.storageBytes;
  // Stale contract file
  const staleContractFile = scanData.files.find((f) => f.name === 'old_contract.pdf');
  const staleContractBytes = staleContractFile ? staleContractFile.sizeBytes : 19293798;

  let simulatedRecoveryBytes = 0;
  if (includeDuplicates) simulatedRecoveryBytes += duplicateWasteBytes;
  if (includeTemp) simulatedRecoveryBytes += tempWasteBytes;
  if (includeStaleContract) simulatedRecoveryBytes += staleContractBytes;

  const simulatedRemainingStorage = Math.max(0, scanData.totalSizeBytes - simulatedRecoveryBytes);
  const simulatedWasteScore = Math.max(
    5,
    Math.round(scanData.wasteScore * (1 - simulatedRecoveryBytes / (scanData.totalSizeBytes * 0.1 || 1)))
  );

  const largeFiles = scanData.files.filter((f) => f.isLarge);
  const staleFiles = scanData.files.filter((f) => f.isStale && !f.isDuplicateCopy);
  const tempFiles = scanData.files.filter((f) => f.isTemp);

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      <SectionHeader
        title="Waste Intelligence"
        subtitle="Understand where your digital storage is being consumed."
        badge={<StatusBadge level={scanData.wasteIndicator} size="sm" />}
        actions={
          <button
            type="button"
            onClick={() => onNavigate('cleanup')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-md shadow-cyan-600/20 transition-all cursor-pointer"
          >
            <span>Proceed to Controlled Cleanup</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        }
      />

      {/* 1. Storage Distribution */}
      <section className="space-y-3">
        <StorageDistributionChart
          categories={scanData.categories}
          totalSizeBytes={scanData.totalSizeBytes}
          totalSizeFormatted={scanData.totalSizeFormatted}
        />
      </section>

      {/* 2. Recovery Simulator & Waste Indicator Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Recovery Simulator */}
        <div className="lg:col-span-7 rounded-xl bg-slate-900/70 border border-slate-800/80 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <Sliders className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white tracking-wide">
                  Recovery Simulator
                </h3>
                <p className="text-xs text-slate-400">
                  Model reclaimed disk headroom before applying controlled changes
                </p>
              </div>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">
              Interactive
            </span>
          </div>

          <div className="space-y-3 pt-2">
            <label className="flex items-center justify-between p-3 rounded-lg bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={includeDuplicates}
                  onChange={(e) => setIncludeDuplicates(e.target.checked)}
                  className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500/20 h-4 w-4 bg-slate-900 cursor-pointer"
                />
                <div>
                  <div className="text-xs font-semibold text-white">
                    Exact Duplicate Redundancies
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Eliminate redundant clone copies (Keep single authoritative master)
                  </div>
                </div>
              </div>
              <span className="font-mono text-xs font-bold text-amber-400">
                +{scanData.duplicateWasteFormatted}
              </span>
            </label>

            <label className="flex items-center justify-between p-3 rounded-lg bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={includeTemp}
                  onChange={(e) => setIncludeTemp(e.target.checked)}
                  className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500/20 h-4 w-4 bg-slate-900 cursor-pointer"
                />
                <div>
                  <div className="text-xs font-semibold text-white">
                    Temporary Cache & Log Leftovers
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Purge stale .log and build cache files
                  </div>
                </div>
              </div>
              <span className="font-mono text-xs font-bold text-blue-400">
                +{scanData.signals.tempFiles.storageFormatted}
              </span>
            </label>

            <label className="flex items-center justify-between p-3 rounded-lg bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={includeStaleContract}
                  onChange={(e) => setIncludeStaleContract(e.target.checked)}
                  className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500/20 h-4 w-4 bg-slate-900 cursor-pointer"
                />
                <div>
                  <div className="text-xs font-semibold text-white">
                    Compress / Archive Stale Legal Contracts
                  </div>
                  <div className="text-[11px] text-slate-400">
                    old_contract.pdf (250 days dormant, 18.4 MB)
                  </div>
                </div>
              </div>
              <span className="font-mono text-xs font-bold text-emerald-400">
                +{formatBytes(staleContractBytes)}
              </span>
            </label>
          </div>

          {/* Simulation Outcome Display */}
          <div className="p-4 rounded-xl bg-slate-950 border border-emerald-900/40 grid grid-cols-3 gap-3 text-center">
            <div>
              <span className="text-[10px] uppercase font-mono text-slate-500 block">
                Total Reclaimed
              </span>
              <span className="text-base font-bold text-emerald-400 font-mono">
                {formatBytes(simulatedRecoveryBytes)}
              </span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-mono text-slate-500 block">
                Post-Clean Footprint
              </span>
              <span className="text-base font-bold text-white font-mono">
                {formatBytes(simulatedRemainingStorage)}
              </span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-mono text-slate-500 block">
                Projected Waste Score
              </span>
              <span className="text-base font-bold text-cyan-300 font-mono">
                {simulatedWasteScore} / 100
              </span>
            </div>
          </div>
        </div>

        {/* Waste Indicator Analysis */}
        <div className="lg:col-span-5 rounded-xl bg-slate-900/70 border border-slate-800/80 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
                <Gauge className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white tracking-wide">
                  Waste Indicator
                </h3>
                <p className="text-xs text-slate-400">
                  Algorithmic scoring breakdown
                </p>
              </div>
            </div>
            <StatusBadge level={scanData.wasteIndicator} size="sm" />
          </div>

          <div className="space-y-3 pt-2">
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">Exact Duplicate Index</span>
                <span className="text-amber-400 font-bold">High Impact (3 copies)</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div className="h-full bg-purple-500 w-3/4 rounded-full" />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">Dormant Age Decay</span>
                <span className="text-amber-400 font-bold">Moderate (250d peak)</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div className="h-full bg-amber-500 w-1/2 rounded-full" />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">Temporary Clutter Ratio</span>
                <span className="text-blue-400 font-bold">Low Footprint (0.1 MB)</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div className="h-full bg-blue-500 w-1/4 rounded-full" />
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-300 leading-relaxed">
            <span className="font-semibold text-white">Diagnostic Summary: </span>
            The system rates overall waste at <strong className="text-amber-400 font-mono">MEDIUM</strong>. Eliminating the duplicate quarterly financial reports and purging build logs drops the severity rating directly to <strong className="text-emerald-400 font-mono">LOW</strong>.
          </div>
        </div>
      </div>

      {/* 3. Large Files Section */}
      <section className="rounded-xl bg-slate-900/70 border border-slate-800/80 p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Large Files (&gt;50 MB)
            </h3>
            <p className="text-xs text-slate-400">
              Primary capacity consumers requiring capacity management
            </p>
          </div>
          <div className="text-xs font-mono text-slate-400">
            {largeFiles.length} files • Total:{' '}
            <strong className="text-white">
              {formatBytes(largeFiles.reduce((a, b) => a + b.sizeBytes, 0))}
            </strong>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-mono text-[11px] uppercase">
                <th className="py-2.5 px-3">File Name</th>
                <th className="py-2.5 px-3">Category</th>
                <th className="py-2.5 px-3 text-right">Size</th>
                <th className="py-2.5 px-3">% of Total</th>
                <th className="py-2.5 px-3">Age</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {largeFiles.map((f) => {
                const percent = ((f.sizeBytes / scanData.totalSizeBytes) * 100).toFixed(1);
                return (
                  <tr key={f.id} className="hover:bg-slate-800/30">
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-white">{f.name}</div>
                      <div className="text-[10px] text-slate-500 font-mono truncate max-w-sm">
                        {f.path}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-300">{f.category}</td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold text-amber-400">
                      {f.sizeFormatted}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-400">
                      {percent}%
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 font-mono">
                      {f.ageDays}d
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        type="button"
                        onClick={() => onSendToCleanup && onSendToCleanup(f)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* 4. Potentially Stale Files Section */}
      <section className="rounded-xl bg-slate-900/70 border border-slate-800/80 p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Potentially Stale Files
            </h3>
            <p className="text-xs text-slate-400">
              Dormant assets with zero modification for over 90 days
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {staleFiles.length} dormant files
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {staleFiles.map((file) => (
            <div
              key={file.id}
              className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between gap-3"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <div className="font-semibold text-white text-xs truncate">
                    {file.name}
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 font-mono border border-amber-800/40">
                    {file.ageDays} days old
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 font-mono truncate mb-2">
                  {file.path}
                </div>
                <div className="text-xs text-slate-300 flex items-center gap-3">
                  <span>Size: <strong className="text-white font-mono">{file.sizeFormatted}</strong></span>
                  <span className="text-slate-600">•</span>
                  <span>Modified: <span className="font-mono text-slate-400">{file.modifiedAt}</span></span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between">
                <span className="text-[11px] text-amber-400/90 font-mono">
                  {file.wasteReason}
                </span>
                <button
                  type="button"
                  onClick={() => onSendToCleanup && onSendToCleanup(file)}
                  className="px-2.5 py-1 rounded bg-amber-950/40 hover:bg-amber-900/50 text-amber-300 border border-amber-800/50 text-xs font-medium transition-colors"
                >
                  Review in Cleanup
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 5. Temporary / Cache Candidates Section */}
      <section className="rounded-xl bg-slate-900/70 border border-slate-800/80 p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Temporary / Cache Candidates
            </h3>
            <p className="text-xs text-slate-400">
              Ephemeral run logs and cache dumps safe for instant purge
            </p>
          </div>
          <span className="text-xs font-mono text-blue-400">
            Safe to purge immediately
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tempFiles.map((file) => (
            <div
              key={file.id}
              className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between gap-3"
            >
              <div className="overflow-hidden">
                <div className="font-semibold text-white text-xs truncate">
                  {file.name}
                </div>
                <div className="text-[11px] text-slate-400 font-mono truncate">
                  {file.path}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Size: <strong className="text-cyan-300 font-mono">{file.sizeFormatted}</strong> • {file.wasteReason}
                </div>
              </div>

              <button
                type="button"
                onClick={() => onSendToCleanup && onSendToCleanup(file)}
                className="shrink-0 px-3 py-1.5 rounded-lg bg-blue-950/50 hover:bg-blue-900/60 text-blue-300 border border-blue-800/50 text-xs font-medium transition-colors"
              >
                Clear in Cleanup
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
