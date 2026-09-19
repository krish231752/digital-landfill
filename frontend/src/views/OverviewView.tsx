import React from 'react';
import {
  Files,
  HardDrive,
  Copy,
  TrendingDown,
  Gauge,
  Sparkles,
  AlertTriangle,
  Clock,
  Trash2,
  Maximize2,
  FolderOpen,
} from 'lucide-react';
import { FileCategory, FileItem, NavigationTab, ScanData } from '../types';
import { MetricCard } from '../components/MetricCard';
import { WasteSignalCard } from '../components/WasteSignalCard';
import { StorageDistributionChart } from '../components/StorageDistributionChart';
import { AIInsightCard } from '../components/AIInsightCard';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';

interface OverviewViewProps {
  scanData: ScanData;
  onNavigate: (tab: NavigationTab) => void;
  onSelectCategory?: (category: FileCategory) => void;
  onScanFolder: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  scanData,
  onNavigate,
  onSelectCategory,
  onScanFolder,
}) => {
  if (scanData.totalFiles === 0) {
    return (
      <div className="space-y-6">
        <div className="border-b border-slate-800/80 pb-4">
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Digital Landfill — Digital Waste Intelligence
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Understand your storage. Recover what matters.
          </p>
        </div>
        <EmptyState
          title="Select a folder to begin analyzing your digital storage."
          description="Point Digital Landfill at any target directory to evaluate cryptographic duplicates, stale assets, and reclaimable waste."
          actionText="Select & Scan Folder"
          onAction={onScanFolder}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white font-sans">
              Digital Landfill
            </h1>
            <span className="text-xs px-2.5 py-1 rounded-md bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 font-mono font-semibold">
              Digital Waste Intelligence
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Understand your storage. Recover what matters.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <div className="text-[10px] uppercase font-mono text-slate-500">
              Active Folder Target
            </div>
            <div className="text-xs text-slate-300 font-mono max-w-xs truncate" title={scanData.folderPath}>
              {scanData.folderPath}
            </div>
          </div>
          <button
            type="button"
            onClick={onScanFolder}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors cursor-pointer"
          >
            <FolderOpen className="w-3.5 h-3.5 text-cyan-400" />
            <span>Switch Folder</span>
          </button>
        </div>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* TOTAL FILES */}
        <MetricCard
          id="metric-total-files"
          label="Total Files"
          value={scanData.totalFiles}
          subtext="Indexed & hashed"
          icon={Files}
          iconColor="text-cyan-400"
          iconBg="bg-cyan-500/10 border-cyan-500/20"
          trend={{ value: 'Full scan', isNeutral: true }}
          onClick={() => onNavigate('inventory')}
        />

        {/* TOTAL STORAGE */}
        <MetricCard
          id="metric-total-storage"
          label="Total Storage"
          value={scanData.totalSizeFormatted}
          subtext="Physical disk allocation"
          icon={HardDrive}
          iconColor="text-indigo-400"
          iconBg="bg-indigo-500/10 border-indigo-500/20"
          trend={{ value: '18 items total', isNeutral: true }}
          onClick={() => onNavigate('waste_intelligence')}
        />

        {/* DUPLICATE WASTE */}
        <MetricCard
          id="metric-duplicate-waste"
          label="Duplicate Waste"
          value={scanData.duplicateWasteFormatted}
          subtext="Byte redundancy"
          icon={Copy}
          iconColor="text-purple-400"
          iconBg="bg-purple-500/10 border-purple-500/20"
          trend={{ value: `${scanData.duplicateGroups.length} groups found`, isPositive: false }}
          onClick={() => onNavigate('duplicates')}
        />

        {/* POTENTIAL RECOVERY */}
        <MetricCard
          id="metric-potential-recovery"
          label="Potential Recovery"
          value={scanData.potentialRecoveryFormatted}
          subtext="Risk-free immediate"
          icon={TrendingDown}
          iconColor="text-emerald-400"
          iconBg="bg-emerald-500/10 border-emerald-500/20"
          trend={{ value: '100% safe', isPositive: true }}
          onClick={() => onNavigate('cleanup')}
        />

        {/* WASTE INDICATOR */}
        <MetricCard
          id="metric-waste-indicator"
          label="Waste Indicator"
          value={scanData.wasteIndicator}
          subtext={`Score: ${scanData.wasteScore}/100`}
          icon={Gauge}
          iconColor="text-amber-400"
          iconBg="bg-amber-500/10 border-amber-500/20"
          badge={<StatusBadge level={scanData.wasteIndicator} size="sm" />}
          trend={{ value: 'Optimization recommended', isPositive: false }}
          onClick={() => onNavigate('waste_intelligence')}
        />
      </div>

      {/* Storage Distribution Chart */}
      <StorageDistributionChart
        categories={scanData.categories}
        totalSizeBytes={scanData.totalSizeBytes}
        totalSizeFormatted={scanData.totalSizeFormatted}
        onSelectCategory={(cat) => {
          if (onSelectCategory) onSelectCategory(cat);
          onNavigate('inventory');
        }}
      />

      {/* Waste Signals Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Waste Signals
            </h2>
            <p className="text-xs text-slate-400">
              Heuristic indicators across storage redundancy, aging decay, and transient footprint
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigate('waste_intelligence')}
            className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer"
          >
            Detailed Analytics →
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Duplicate Files */}
          <WasteSignalCard
            id="signal-duplicates"
            title="Duplicate Files"
            count={scanData.signals.duplicates.count}
            storageImpact={scanData.signals.duplicates.storageFormatted}
            severity={scanData.signals.duplicates.severity}
            description={scanData.signals.duplicates.description}
            icon={Copy}
            actionText="Inspect Duplicates"
            onAction={() => onNavigate('duplicates')}
          />

          {/* Large Files */}
          <WasteSignalCard
            id="signal-large-files"
            title="Large Files"
            count={scanData.signals.largeFiles.count}
            storageImpact={scanData.signals.largeFiles.storageFormatted}
            severity={scanData.signals.largeFiles.severity}
            description={scanData.signals.largeFiles.description}
            icon={Maximize2}
            actionText="Review Large Files"
            onAction={() => onNavigate('waste_intelligence')}
          />

          {/* Potentially Stale */}
          <WasteSignalCard
            id="signal-stale"
            title="Potentially Stale"
            count={scanData.signals.staleFiles.count}
            storageImpact={scanData.signals.staleFiles.storageFormatted}
            severity={scanData.signals.staleFiles.severity}
            description={scanData.signals.staleFiles.description}
            icon={Clock}
            actionText="Inspect Dormant Files"
            onAction={() => onNavigate('cleanup')}
          />

          {/* Temp / Cache */}
          <WasteSignalCard
            id="signal-temp"
            title="Temp / Cache"
            count={scanData.signals.tempFiles.count}
            storageImpact={scanData.signals.tempFiles.storageFormatted}
            severity={scanData.signals.tempFiles.severity}
            description={scanData.signals.tempFiles.description}
            icon={Trash2}
            actionText="Clear Cache Files"
            onAction={() => onNavigate('cleanup')}
          />
        </div>
      </div>

      {/* AI Insight Highlight Card */}
      <AIInsightCard
        id="overview-ai-insight"
        quote="Your largest measurable recovery opportunity comes from exact duplicate files."
        onAnalyze={() => onNavigate('ai_intelligence')}
      />
    </div>
  );
};
