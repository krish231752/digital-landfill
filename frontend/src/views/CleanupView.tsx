import React, { useState } from 'react';
import {
  Trash2,
  AlertTriangle,
  Clock,
  Copy,
  FileText,
  CheckCircle2,
  ShieldAlert,
  Eye,
  Folder,
  HardDrive,
  Filter,
} from 'lucide-react';
import { FileItem, NavigationTab, ScanData } from '../types';
import { SectionHeader } from '../components/SectionHeader';
import { ConfirmationModal } from '../components/ConfirmationModal';
import { EmptyState } from '../components/EmptyState';

interface CleanupViewProps {
  scanData: ScanData;
  onNavigate: (tab: NavigationTab) => void;
  onConfirmDeleteFile: (file: FileItem) => Promise<void> | void;
  onInspectFile: (file: FileItem) => void;
  recentlyDeletedNotice: string | null;
  onClearNotice: () => void;
}

export const CleanupView: React.FC<CleanupViewProps> = ({
  scanData,
  onNavigate,
  onConfirmDeleteFile,
  onInspectFile,
  recentlyDeletedNotice,
  onClearNotice,
}) => {
  const [activeCategoryFilter, setActiveCategoryFilter] = useState<
    'ALL' | 'STALE' | 'DUPLICATE' | 'TEMP'
  >('ALL');

  const [modalFile, setModalFile] = useState<FileItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Filter candidate items:
  // Duplicate copies (excluding masters), Stale files, Temp files
  const staleCandidates = scanData.files.filter((f) => f.isStale && !f.isDuplicateCopy);
  const duplicateCopies = scanData.files.filter((f) => f.isDuplicateCopy);
  const tempCandidates = scanData.files.filter((f) => f.isTemp);

  const allCandidates = [...duplicateCopies, ...staleCandidates, ...tempCandidates];

  const displayedCandidates = allCandidates.filter((file) => {
    if (activeCategoryFilter === 'STALE') return file.isStale && !file.isDuplicateCopy;
    if (activeCategoryFilter === 'DUPLICATE') return file.isDuplicateCopy;
    if (activeCategoryFilter === 'TEMP') return file.isTemp;
    return true;
  });

  const handleDeleteClick = (file: FileItem) => {
    setModalFile(file);
    setIsModalOpen(true);
  };

  const handleModalConfirm = async (file: FileItem) => {
    await onConfirmDeleteFile(file);
    setIsModalOpen(false);
    setModalFile(null);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      <SectionHeader
        title="Controlled Cleanup"
        subtitle="Review before removing digital waste."
        badge={
          <span className="text-xs px-2.5 py-1 rounded bg-rose-950/60 text-rose-300 border border-rose-800/50 font-mono">
            Explicit User Confirmation Required
          </span>
        }
      />

      {/* Success Notification Banner */}
      {recentlyDeletedNotice && (
        <div className="rounded-xl bg-emerald-950/40 border border-emerald-800/60 p-4 flex items-center justify-between gap-3 text-xs text-emerald-200 animate-in slide-in-from-top-2">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <span className="font-semibold text-white">
              {recentlyDeletedNotice}
            </span>
          </div>
          <button
            type="button"
            onClick={onClearNotice}
            className="text-xs text-emerald-400 hover:text-emerald-300 font-mono cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Strict Security Policy Notice */}
      <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 flex items-start gap-3.5 text-xs text-slate-300">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold text-white">
            Absolute Safety Guarantee: Deletion is NEVER Automatic
          </div>
          <p className="text-slate-400 leading-relaxed">
            AI agents and automated scanners are strictly forbidden from directly removing files. Every action in this view requires explicit manual confirmation with verified file path and size metrics.
          </p>
        </div>
      </div>

      {/* Candidates Category Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setActiveCategoryFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              activeCategoryFilter === 'ALL'
                ? 'bg-cyan-600 text-white font-semibold'
                : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
            }`}
          >
            All Candidates ({allCandidates.length})
          </button>

          <button
            type="button"
            onClick={() => setActiveCategoryFilter('DUPLICATE')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              activeCategoryFilter === 'DUPLICATE'
                ? 'bg-purple-600 text-white font-semibold'
                : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
            }`}
          >
            Duplicate Copies ({duplicateCopies.length})
          </button>

          <button
            type="button"
            onClick={() => setActiveCategoryFilter('STALE')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              activeCategoryFilter === 'STALE'
                ? 'bg-amber-600 text-white font-semibold'
                : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
            }`}
          >
            Potentially Stale Files ({staleCandidates.length})
          </button>

          <button
            type="button"
            onClick={() => setActiveCategoryFilter('TEMP')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              activeCategoryFilter === 'TEMP'
                ? 'bg-blue-600 text-white font-semibold'
                : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
            }`}
          >
            Temporary/Cache Candidates ({tempCandidates.length})
          </button>
        </div>

        <span className="text-xs text-slate-500 font-mono">
          {displayedCandidates.length} candidate{displayedCandidates.length === 1 ? '' : 's'} available
        </span>
      </div>

      {/* Candidate Cards Grid */}
      {displayedCandidates.length === 0 ? (
        <EmptyState
          title={
            activeCategoryFilter === 'STALE'
              ? 'No potentially stale files detected.'
              : activeCategoryFilter === 'DUPLICATE'
              ? 'No duplicate copies found in candidate list.'
              : 'All cleanup candidates have been reviewed and cleared.'
          }
          description="Your storage target does not have any pending candidates in this filter category."
          variant="success"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {displayedCandidates.map((file) => (
            <div
              key={file.id}
              className="rounded-xl bg-slate-900/70 border border-slate-800 p-5 flex flex-col justify-between gap-4 hover:border-slate-700/80 transition-all"
            >
              {/* Header */}
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-bold text-white break-all leading-snug">
                    {file.name}
                  </h3>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono border border-slate-700 shrink-0">
                    {file.category}
                  </span>
                </div>

                <div className="flex items-center gap-3 text-xs">
                  <span className="font-mono font-bold text-amber-400">
                    {file.sizeFormatted}
                  </span>
                  <span className="text-slate-600">•</span>
                  <span className="text-slate-400 font-mono">
                    {file.ageDays} days old
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800/60 space-y-1 text-xs">
                  <div className="text-[10px] uppercase font-semibold text-slate-500">
                    Reason
                  </div>
                  <div className="text-slate-300 leading-snug">
                    {file.wasteReason || `Flagged as ${file.status} candidate`}
                  </div>
                </div>

                <div className="text-[11px] text-slate-500 font-mono truncate" title={file.path}>
                  <Folder className="w-3 h-3 inline mr-1 text-slate-600" />
                  {file.path}
                </div>
              </div>

              {/* Card Actions: [ View Details ] [ Delete ] */}
              <div className="flex items-center justify-between gap-2 pt-3 border-t border-slate-800/80">
                <button
                  type="button"
                  onClick={() => onInspectFile(file)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors cursor-pointer"
                >
                  <Eye className="w-3.5 h-3.5 text-slate-400" />
                  <span>View Details</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleDeleteClick(file)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-rose-600/90 hover:bg-rose-600 text-white text-xs font-semibold shadow-md shadow-rose-600/20 transition-all cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={isModalOpen}
        file={modalFile}
        onCancel={() => {
          setIsModalOpen(false);
          setModalFile(null);
        }}
        onConfirmDelete={handleModalConfirm}
      />
    </div>
  );
};
