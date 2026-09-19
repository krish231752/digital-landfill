import React, { useEffect, useState } from 'react';
import {
  Menu,
  X,
  Layers,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import {
  FileItem,
  NavigationTab,
  RecommendationItem,
  ScanData,
} from './types';
import { apiClient, HealthResponse } from './api/client';
import { Sidebar } from './components/Sidebar';
import { FileDetailDrawer } from './components/FileDetailDrawer';
import { ConfirmationModal } from './components/ConfirmationModal';
import { ScanFolderModal } from './components/ScanFolderModal';
import { OverviewView } from './views/OverviewView';
import { WasteIntelligenceView } from './views/WasteIntelligenceView';
import { DuplicatesView } from './views/DuplicatesView';
import { RecommendationsView } from './views/RecommendationsView';
import { AIIntelligenceView } from './views/AIIntelligenceView';
import { CleanupView } from './views/CleanupView';
import { InventoryView } from './views/InventoryView';

export const EMPTY_SCAN_DATA: ScanData = {
  folderPath: 'No folder selected',
  totalFiles: 0,
  totalSizeBytes: 0,
  totalSizeFormatted: '0 B',
  duplicateWasteBytes: 0,
  duplicateWasteFormatted: '0 B',
  potentialRecoveryBytes: 0,
  potentialRecoveryFormatted: '0 B',
  wasteIndicator: 'LOW',
  wasteScore: 0,
  scannedAt: '—',
  categories: [],
  signals: {
    duplicates: {
      count: 0,
      storageBytes: 0,
      storageFormatted: '0 B',
      severity: 'LOW',
      description: 'No duplicates scanned.',
    },
    largeFiles: {
      count: 0,
      storageBytes: 0,
      storageFormatted: '0 B',
      severity: 'LOW',
      description: 'No large files scanned.',
    },
    staleFiles: {
      count: 0,
      storageBytes: 0,
      storageFormatted: '0 B',
      severity: 'LOW',
      description: 'No stale files scanned.',
    },
    tempFiles: {
      count: 0,
      storageBytes: 0,
      storageFormatted: '0 B',
      severity: 'LOW',
      description: 'No temporary files scanned.',
    },
  },
  files: [],
  duplicateGroups: [],
  recommendations: [],
};

export default function App() {
  const [scanData, setScanData] = useState<ScanData>(EMPTY_SCAN_DATA);
  const [currentTab, setCurrentTab] = useState<NavigationTab>('overview');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const [healthInfo, setHealthInfo] = useState<HealthResponse | null>(null);

  // Inspector Drawer state
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Deletion Modal state
  const [fileToDelete, setFileToDelete] = useState<FileItem | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [recentlyDeletedNotice, setRecentlyDeletedNotice] = useState<string | null>(null);
  const [deleteErrorMessage, setDeleteErrorMessage] = useState<string | null>(null);

  // Folder Scan Modal state
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);

  // Active recommendation for Qwen Intelligence
  const [activeRecommendation, setActiveRecommendation] = useState<RecommendationItem | null>(null);

  // Load active scan state from FastAPI backend on mount
  useEffect(() => {
    let isMounted = true;

    async function loadBackendState() {
      try {
        const health = await apiClient.getHealth();
        if (!isMounted) return;
        setIsBackendConnected(true);
        setHealthInfo(health);
        setConnectionError(null);

        if (health.has_active_scan) {
          const data = await apiClient.getScanData();
          if (isMounted) {
            setScanData(data);
          }
        }
      } catch (err: any) {
        if (!isMounted) return;
        setIsBackendConnected(false);
        setConnectionError(err.message || 'Backend disconnected');
      }
    }

    loadBackendState();
    return () => {
      isMounted = false;
    };
  }, []);

  // Handle Controlled File Deletion via Backend Pre-verification
  const handleConfirmDelete = async (file: FileItem) => {
    setDeleteErrorMessage(null);
    try {
      const response = await apiClient.deleteFile(
        file.path,
        file.sizeBytes,
        file.modifiedAt
      );

      // Update state with freshly recomputed scan data from backend
      setScanData(response.data);

      setRecentlyDeletedNotice(
        `✓ File '${file.name}' deleted successfully. Reclaimed ${file.sizeFormatted}.`
      );

      if (selectedFile?.id === file.id) {
        setIsDrawerOpen(false);
        setSelectedFile(null);
      }
    } catch (err: any) {
      setDeleteErrorMessage(
        `Deletion rejected: ${err.message || 'Verification check failed on server.'}`
      );
    }
  };

  const handleInspectFile = (file: FileItem) => {
    setSelectedFile(file);
    setIsDrawerOpen(true);
  };

  const handleOpenDeleteModal = (file: FileItem) => {
    setFileToDelete(file);
    setIsDeleteModalOpen(true);
  };

  const handleExplainWithQwen = (rec: RecommendationItem) => {
    setActiveRecommendation(rec);
    setCurrentTab('ai_intelligence');
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col md:flex-row antialiased font-sans">
      {/* Mobile Top Navigation Bar */}
      <header className="md:hidden flex items-center justify-between p-4 bg-[#0a0e1a] border-b border-slate-800 sticky top-0 z-40">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center text-white font-bold shadow-sm">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold tracking-wider text-white flex items-center gap-1.5">
              <span>DIGITAL LANDFILL</span>
              <span
                className={`text-[8px] font-mono px-1.5 py-0.2 rounded border font-bold ${
                  healthInfo?.deployment_mode === 'demo'
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                }`}
              >
                {healthInfo?.deployment_mode === 'demo' ? 'DEMO' : 'LOCAL'}
              </span>
            </div>
            <div className="text-[10px] font-mono text-cyan-400">
              Waste Intelligence
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white"
        >
          {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* Desktop / Responsive Sidebar */}
      <div className={`${isMobileMenuOpen ? 'block' : 'hidden'} md:block`}>
        <Sidebar
          currentTab={currentTab}
          onSelectTab={(tab) => {
            setCurrentTab(tab);
            setIsMobileMenuOpen(false);
          }}
          scanData={scanData}
          onOpenScanModal={() => setIsScanModalOpen(true)}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          deploymentMode={healthInfo?.deployment_mode || 'local'}
        />
      </div>

      {/* Main Viewport */}
      <main className="flex-1 min-w-0 p-4 sm:p-6 md:p-8 lg:p-10 max-w-7xl mx-auto w-full space-y-6">
        {/* Cloud Demo Environment Notice Banner */}
        {healthInfo?.deployment_mode === 'demo' && (
          <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-800/60 text-amber-200 text-xs flex items-center justify-between gap-3 animate-in fade-in">
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono text-[10px] font-bold border border-amber-500/40 shrink-0">
                CLOUD DEMO MODE
              </span>
              <span className="text-slate-300">
                Running in cloud demo mode on bundled test datasets. Real local Windows drive scanning is available when running locally in Local Mode.
              </span>
            </div>
          </div>
        )}

        {/* Backend Disconnected Banner */}
        {isBackendConnected === false && (
          <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-200 text-xs flex items-center justify-between gap-3 animate-in fade-in">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
              <div>
                <strong>Backend Disconnected:</strong> {connectionError}.
                <div className="text-slate-400 text-[11px] mt-0.5">
                  Make sure FastAPI server is running with <code>uvicorn backend.api:app --reload</code>.
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={async () => {
                try {
                  await apiClient.getHealth();
                  setIsBackendConnected(true);
                  setConnectionError(null);
                  const data = await apiClient.getScanData();
                  setScanData(data);
                } catch (e: any) {
                  setConnectionError(e.message);
                }
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-900/60 hover:bg-rose-800 text-rose-200 border border-rose-700/60 transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Global Deletion Error Banner */}
        {deleteErrorMessage && (
          <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/60 text-amber-200 text-xs flex items-center justify-between gap-3 animate-in slide-in-from-top-2">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
              <span>{deleteErrorMessage}</span>
            </div>
            <button
              type="button"
              onClick={() => setDeleteErrorMessage(null)}
              className="text-xs text-amber-400 hover:text-amber-300 font-mono cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        {currentTab === 'overview' && (
          <OverviewView
            scanData={scanData}
            onNavigate={setCurrentTab}
            onScanFolder={() => setIsScanModalOpen(true)}
          />
        )}

        {currentTab === 'waste_intelligence' && (
          <WasteIntelligenceView
            scanData={scanData}
            onNavigate={setCurrentTab}
            onSendToCleanup={() => {
              setCurrentTab('cleanup');
            }}
          />
        )}

        {currentTab === 'duplicates' && (
          <DuplicatesView
            scanData={scanData}
            onNavigate={setCurrentTab}
            onSendToCleanup={() => {
              setCurrentTab('cleanup');
            }}
            onReviewInInventory={(file) => {
              setSelectedFile(file);
              setIsDrawerOpen(true);
            }}
          />
        )}

        {currentTab === 'recommendations' && (
          <RecommendationsView
            scanData={scanData}
            onNavigate={setCurrentTab}
            onExplainWithQwen={handleExplainWithQwen}
            onTakeAction={() => {
              setCurrentTab('cleanup');
            }}
          />
        )}

        {currentTab === 'ai_intelligence' && (
          <AIIntelligenceView
            scanData={scanData}
            activeRecommendation={activeRecommendation}
            onClearActiveRecommendation={() => setActiveRecommendation(null)}
          />
        )}

        {currentTab === 'cleanup' && (
          <CleanupView
            scanData={scanData}
            onNavigate={setCurrentTab}
            onConfirmDeleteFile={handleConfirmDelete}
            onInspectFile={handleInspectFile}
            recentlyDeletedNotice={recentlyDeletedNotice}
            onClearNotice={() => setRecentlyDeletedNotice(null)}
          />
        )}

        {currentTab === 'inventory' && (
          <InventoryView
            scanData={scanData}
            onNavigate={setCurrentTab}
            onSelectFile={handleInspectFile}
            onDeleteRequest={handleOpenDeleteModal}
          />
        )}
      </main>

      {/* Slide-out File Detail Drawer */}
      <FileDetailDrawer
        file={selectedFile}
        isOpen={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false);
          setSelectedFile(null);
        }}
        onDeleteRequest={handleOpenDeleteModal}
      />

      {/* Global Confirmation Modal for Deletion */}
      <ConfirmationModal
        isOpen={isDeleteModalOpen}
        file={fileToDelete}
        onCancel={() => {
          setIsDeleteModalOpen(false);
          setFileToDelete(null);
        }}
        onConfirmDelete={async (file) => {
          await handleConfirmDelete(file);
          setIsDeleteModalOpen(false);
          setFileToDelete(null);
        }}
      />

      {/* Folder Scanner Modal */}
      <ScanFolderModal
        isOpen={isScanModalOpen}
        onClose={() => setIsScanModalOpen(false)}
        onScanComplete={(newScan) => {
          setScanData(newScan);
          setRecentlyDeletedNotice(null);
          setDeleteErrorMessage(null);
        }}
        currentPath={scanData.folderPath}
        deploymentMode={healthInfo?.deployment_mode || 'local'}
      />
    </div>
  );
}
