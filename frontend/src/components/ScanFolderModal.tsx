import React, { useState } from 'react';
import {
  FolderOpen,
  X,
  HardDrive,
  CheckCircle2,
  Loader2,
  FolderSearch,
  Sparkles,
  AlertCircle,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { ScanData } from '../types';

interface ScanFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onScanComplete: (newScanData: ScanData) => void;
  currentPath: string;
  deploymentMode?: 'local' | 'demo';
}

export const ScanFolderModal: React.FC<ScanFolderModalProps> = ({
  isOpen,
  onClose,
  onScanComplete,
  currentPath,
  deploymentMode = 'local',
}) => {
  const [folderPath, setFolderPath] = useState(
    currentPath === 'No folder selected' ? 'test_waste_sample' : currentPath
  );
  const [isScanning, setIsScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleStartScan = async (targetFolder: string) => {
    if (!targetFolder.trim()) {
      setErrorMessage('Please enter a folder path.');
      return;
    }

    setIsScanning(true);
    setErrorMessage(null);
    setProgress(15);
    setCurrentStep('Connecting to Digital Landfill Python Scanner...');

    try {
      setProgress(40);
      setCurrentStep('Walking directory tree & extracting metadata...');

      const response = await apiClient.scanFolder(targetFolder.trim());

      setProgress(80);
      setCurrentStep('Evaluating SHA-256 duplicates & waste telemetry...');

      setTimeout(() => {
        setProgress(100);
        setCurrentStep('Analysis complete.');
        onScanComplete(response.data);
        setIsScanning(false);
        onClose();
      }, 400);
    } catch (err: any) {
      setIsScanning(false);
      setErrorMessage(err.message || 'Scanning failed. Ensure the folder exists.');
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150"
    >
      <div className="w-full max-w-lg rounded-2xl bg-[#0e1424] border border-slate-800 p-6 shadow-2xl space-y-5 text-slate-100">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <FolderSearch className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Scan Storage Target
              </h2>
              <p className="text-xs text-slate-400">
                Analyze local directory for duplicate, stale, and cache waste
              </p>
            </div>
          </div>
          <button
            type="button"
            disabled={isScanning}
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {errorMessage && (
          <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-xs text-rose-200 flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {isScanning ? (
          /* Scanning in progress */
          <div className="py-6 space-y-4 text-center">
            <div className="p-4 inline-flex rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Loader2 className="w-8 h-8 animate-spin" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-white">
                Scanning Directory Storage...
              </h3>
              <p className="text-xs text-cyan-300 font-mono">{currentStep}</p>
            </div>

            {/* Progress bar */}
            <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="text-[11px] text-slate-500 font-mono">
              {progress}% completed
            </div>
          </div>
        ) : (
          /* Folder selection form */
          <div className="space-y-4">
            {deploymentMode === 'demo' && (
              <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-800/60 text-xs text-amber-200 flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <div className="font-semibold text-white">Cloud Demo Environment Active</div>
                  <p className="text-[11px] text-slate-300">
                    A cloud-hosted server cannot access client local drives. Please select the bundled demo dataset (<code className="text-amber-300">test_waste_sample</code>) below.
                  </p>
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                {deploymentMode === 'demo' ? 'Target Demo Fixture' : 'Target Folder Path (Absolute or Relative)'}
              </label>
              <div className="relative">
                <FolderOpen className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={folderPath}
                  onChange={(e) => setFolderPath(e.target.value)}
                  placeholder={deploymentMode === 'demo' ? 'test_waste_sample' : 'test_waste_sample or C:\\path\\to\\folder'}
                  className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 font-mono text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
                />
              </div>
            </div>

            {/* Quick Preset targets */}
            <div className="space-y-2">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                {deploymentMode === 'demo' ? 'Available Demo Datasets' : 'Workspace Fixtures & Targets'}
              </span>
              <div className="grid grid-cols-1 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setFolderPath('test_waste_sample');
                    handleStartScan('test_waste_sample');
                  }}
                  className="p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-slate-800 text-left transition-all flex items-center justify-between cursor-pointer"
                >
                  <div className="overflow-hidden">
                    <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                      <span>test_waste_sample</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 font-mono">
                        {deploymentMode === 'demo' ? 'Standard Demo Fixture' : 'Workspace Fixture'}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      Multi-category files • Duplicate sets • Large & Stale files
                    </div>
                  </div>
                  <Sparkles className="w-4 h-4 text-cyan-400 shrink-0" />
                </button>

                {deploymentMode === 'local' && (
                  <button
                    type="button"
                    onClick={() => {
                      setFolderPath('.');
                      handleStartScan('.');
                    }}
                    className="p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-slate-800 text-left transition-all flex items-center justify-between cursor-pointer"
                  >
                    <div>
                      <div className="text-xs font-semibold text-white">
                        Current Project Directory (.)
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Full digital-landfill repository analysis
                      </div>
                    </div>
                    <HardDrive className="w-4 h-4 text-slate-500 shrink-0" />
                  </button>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors cursor-pointer"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={() => handleStartScan(folderPath)}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-md shadow-cyan-600/20 transition-all cursor-pointer"
              >
                <span>Begin Analysis</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
