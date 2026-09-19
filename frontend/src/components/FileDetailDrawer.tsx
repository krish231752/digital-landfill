import React from 'react';
import {
  X,
  FileText,
  Folder,
  HardDrive,
  Clock,
  ShieldCheck,
  AlertTriangle,
  Copy,
  Trash2,
} from 'lucide-react';
import { FileItem } from '../types';
import { StatusBadge } from './StatusBadge';

interface FileDetailDrawerProps {
  file: FileItem | null;
  isOpen: boolean;
  onClose: () => void;
  onDeleteRequest?: (file: FileItem) => void;
}

export const FileDetailDrawer: React.FC<FileDetailDrawerProps> = ({
  file,
  isOpen,
  onClose,
  onDeleteRequest,
}) => {
  if (!isOpen || !file) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-40 flex justify-end bg-black/60 backdrop-blur-xs animate-in fade-in"
    >
      <div className="w-full max-w-md h-full bg-[#0d121f] border-l border-slate-800 p-6 flex flex-col justify-between overflow-y-auto shadow-2xl">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between gap-3 pb-4 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-cyan-400">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white break-all leading-snug">
                  {file.name}
                </h3>
                <span className="text-xs text-slate-400 font-mono">
                  {file.category}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Status & Signal tags */}
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge level={file.status} size="sm" />
            {file.isDuplicate && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-950/40 text-purple-300 border border-purple-800/40 font-mono">
                Exact Duplicate
              </span>
            )}
            {file.isStale && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-950/40 text-amber-300 border border-amber-800/40 font-mono">
                Stale (&gt;90d)
              </span>
            )}
            {file.isTemp && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-950/40 text-blue-300 border border-blue-800/40 font-mono">
                Temporary
              </span>
            )}
            {file.isLarge && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-rose-950/40 text-rose-300 border border-rose-800/40 font-mono">
                Large File (&gt;50MB)
              </span>
            )}
          </div>

          {/* Metadata Grid */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              File Metadata
            </h4>
            <div className="rounded-xl bg-slate-950/80 border border-slate-800/80 p-4 space-y-3 text-xs">
              <div className="space-y-1">
                <span className="text-[10px] uppercase font-semibold text-slate-500 flex items-center gap-1.5">
                  <Folder className="w-3 h-3 text-slate-400" />
                  Full Filesystem Path
                </span>
                <p className="font-mono text-slate-300 break-all bg-slate-900/80 p-2 rounded border border-slate-800 text-[11px]">
                  {file.path}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <span className="text-[10px] uppercase font-semibold text-slate-500 flex items-center gap-1">
                    <HardDrive className="w-3 h-3 text-amber-400" />
                    Storage Size
                  </span>
                  <div className="font-mono font-bold text-white text-sm mt-0.5">
                    {file.sizeFormatted}
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono">
                    {file.sizeBytes.toLocaleString()} bytes
                  </div>
                </div>

                <div>
                  <span className="text-[10px] uppercase font-semibold text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-cyan-400" />
                    Last Modified
                  </span>
                  <div className="font-semibold text-white text-xs mt-0.5">
                    {file.modifiedAt}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">
                    {file.ageDays} days ago
                  </div>
                </div>
              </div>

              {/* SHA-256 Hash */}
              <div className="space-y-1 pt-2 border-t border-slate-800">
                <span className="text-[10px] uppercase font-semibold text-slate-500 flex items-center gap-1.5">
                  <ShieldCheck className="w-3 h-3 text-emerald-400" />
                  SHA-256 Checksum Fingerprint
                </span>
                <p className="font-mono text-slate-300 break-all bg-slate-900/80 p-2 rounded border border-slate-800 text-[11px] select-all">
                  {file.sha256}
                </p>
              </div>
            </div>
          </div>

          {/* Waste Signal Analysis */}
          {file.wasteReason && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Waste Intelligence Assessment
              </h4>
              <div className="rounded-xl bg-amber-950/20 border border-amber-800/40 p-3.5 space-y-1.5 text-xs">
                <div className="flex items-center gap-2 text-amber-300 font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  <span>Flagged by Scanner</span>
                </div>
                <p className="text-slate-300 text-xs leading-relaxed">
                  {file.wasteReason}
                </p>
                {file.isDuplicateCopy && (
                  <p className="text-[11px] text-purple-300 font-mono pt-1">
                    Redundant copy. Master copy exists in primary folder.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="pt-6 border-t border-slate-800 space-y-3">
          {onDeleteRequest && (
            <button
              type="button"
              onClick={() => {
                onClose();
                onDeleteRequest(file);
              }}
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-rose-600/90 hover:bg-rose-600 text-white text-xs font-semibold shadow-lg shadow-rose-600/20 transition-all cursor-pointer"
            >
              <Trash2 className="w-4 h-4" />
              <span>Review in Controlled Cleanup</span>
            </button>
          )}

          <button
            type="button"
            onClick={onClose}
            className="w-full py-2 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors cursor-pointer"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
