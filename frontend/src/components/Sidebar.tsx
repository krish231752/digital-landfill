import React from 'react';
import {
  LayoutDashboard,
  BarChart3,
  Copy,
  Sparkles,
  Bot,
  Trash2,
  Database,
  FolderOpen,
  Folder,
  CheckCircle2,
  Layers,
  ChevronLeft,
  ChevronRight,
  Menu,
} from 'lucide-react';
import { NavigationTab, ScanData } from '../types';

interface SidebarProps {
  currentTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  scanData: ScanData;
  onOpenScanModal: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  deploymentMode?: 'local' | 'demo';
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  scanData,
  onOpenScanModal,
  isCollapsed,
  onToggleCollapse,
  deploymentMode = 'local',
}) => {
  const duplicateCandidateCount = scanData.files.filter((f) => f.isDuplicateCopy).length;
  const staleCandidateCount = scanData.files.filter((f) => f.isStale).length;
  const cleanupTotalCount = duplicateCandidateCount + staleCandidateCount + scanData.files.filter((f) => f.isTemp).length;

  const navItems: {
    id: NavigationTab;
    label: string;
    icon: React.ElementType;
    badge?: string | number;
    badgeColor?: string;
  }[] = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'waste_intelligence', label: 'Waste Intelligence', icon: BarChart3 },
    {
      id: 'duplicates',
      label: 'Duplicates',
      icon: Copy,
      badge: duplicateCandidateCount > 0 ? duplicateCandidateCount : undefined,
      badgeColor: 'bg-purple-900/60 text-purple-300 border-purple-800/60',
    },
    {
      id: 'recommendations',
      label: 'Recommendations',
      icon: Sparkles,
      badge: scanData.recommendations.length,
      badgeColor: 'bg-indigo-900/60 text-indigo-300 border-indigo-800/60',
    },
    { id: 'ai_intelligence', label: 'AI Intelligence', icon: Bot },
    {
      id: 'cleanup',
      label: 'Cleanup',
      icon: Trash2,
      badge: cleanupTotalCount > 0 ? cleanupTotalCount : undefined,
      badgeColor: 'bg-rose-900/60 text-rose-300 border-rose-800/60',
    },
    {
      id: 'inventory',
      label: 'Full Inventory',
      icon: Database,
      badge: scanData.totalFiles,
      badgeColor: 'bg-slate-800 text-slate-300 border-slate-700',
    },
  ];

  return (
    <aside
      className={`h-screen sticky top-0 flex flex-col justify-between bg-[#0a0e1a] border-r border-slate-800/80 transition-all duration-200 z-30 ${
        isCollapsed ? 'w-18' : 'w-64 md:w-72'
      }`}
    >
      {/* Top Header & Brand */}
      <div className="flex flex-col">
        <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
          {!isCollapsed ? (
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center text-white font-bold shadow-md shadow-cyan-500/20 shrink-0">
                <Layers className="w-5 h-5" />
              </div>
              <div className="overflow-hidden">
                <div className="text-sm font-extrabold tracking-wider text-white font-sans truncate">
                  DIGITAL LANDFILL
                </div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-[9px] uppercase font-mono tracking-wider text-cyan-400 font-semibold truncate">
                    Waste Intelligence
                  </span>
                  <span
                    className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold border ${
                      deploymentMode === 'demo'
                        ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                        : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                    }`}
                  >
                    {deploymentMode === 'demo' ? 'DEMO MODE' : 'LOCAL MODE'}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="mx-auto h-9 w-9 rounded-xl bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center text-white font-bold shadow-md shadow-cyan-500/20">
              <Layers className="w-5 h-5" />
            </div>
          )}

          <button
            type="button"
            onClick={onToggleCollapse}
            className="hidden md:flex p-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation items */}
        <div className="p-3 space-y-1">
          {!isCollapsed && (
            <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono">
              Navigation
            </div>
          )}

          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onSelectTab(item.id)}
                  title={item.label}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all cursor-pointer ${
                    isActive
                      ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 font-semibold shadow-xs'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                  } ${isCollapsed ? 'justify-center px-2' : ''}`}
                >
                  <Icon
                    className={`w-4 h-4 shrink-0 ${
                      isActive ? 'text-cyan-400' : 'text-slate-400'
                    }`}
                  />
                  {!isCollapsed && (
                    <span className="truncate tracking-wide flex-1 text-left">
                      {item.label}
                    </span>
                  )}
                  {!isCollapsed && item.badge !== undefined && (
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full border ${item.badgeColor || 'bg-slate-800 text-slate-300'}`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Middle & Bottom Sections: Current Scan, System Status, Actions */}
      <div className="p-3 space-y-3 border-t border-slate-800/80">
        {!isCollapsed ? (
          <>
            {/* CURRENT SCAN BLOCK */}
            <div className="rounded-xl bg-slate-950/70 border border-slate-800/80 p-3 space-y-1.5 text-xs">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono flex items-center gap-1.5">
                <Folder className="w-3 h-3 text-cyan-400" />
                Current Scan
              </div>

              <div className="text-slate-300 font-mono text-[11px] truncate" title={scanData.folderPath}>
                {scanData.folderPath}
              </div>

              <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-800/60 font-mono">
                <span className="text-white font-bold">{scanData.totalFiles} Files</span>
                <span className="text-cyan-400 font-bold">{scanData.totalSizeFormatted}</span>
              </div>
            </div>

            {/* SYSTEM STATUS BLOCK */}
            <div className="rounded-xl bg-slate-950/50 border border-slate-800/60 p-3 space-y-2 text-xs">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-mono">
                System Status
              </div>

              <div className="space-y-1.5 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Scanner</span>
                  <span className="inline-flex items-center gap-1.5 text-emerald-400 font-medium">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Online
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-400">AI Engine</span>
                  <span className="inline-flex items-center gap-1.5 text-emerald-400 font-medium">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    Connected
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Storage</span>
                  <span className="inline-flex items-center gap-1.5 text-cyan-400 font-medium">
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                    Analyzed
                  </span>
                </div>
              </div>
            </div>

            {/* ACTION: SCAN FOLDER */}
            <button
              type="button"
              onClick={onOpenScanModal}
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-md shadow-cyan-600/20 transition-all cursor-pointer border border-cyan-400/30"
            >
              <FolderOpen className="w-4 h-4" />
              <span>Scan Folder</span>
            </button>
          </>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <button
              type="button"
              onClick={onOpenScanModal}
              className="p-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white transition-colors cursor-pointer"
              title="Scan Folder"
            >
              <FolderOpen className="w-5 h-5" />
            </button>
            <div className="h-2 w-2 rounded-full bg-emerald-400" title="System Online" />
          </div>
        )}
      </div>
    </aside>
  );
};
