import React, { useState } from 'react';
import {
  AlertTriangle,
  FileText,
  Clock,
  HardDrive,
  Folder,
  ShieldAlert,
  Loader2,
} from 'lucide-react';
import { FileItem } from '../types';

interface ConfirmationModalProps {
  isOpen: boolean;
  file: FileItem | null;
  onCancel: () => void;
  onConfirmDelete: (file: FileItem) => Promise<void> | void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  file,
  onCancel,
  onConfirmDelete,
}) => {
  const [isDeleting, setIsDeleting] = useState(false);

  if (!isOpen || !file) return null;

  const handleConfirm = async () => {
    try {
      setIsDeleting(true);
      await onConfirmDelete(file);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150"
    >
      <div className="w-full max-w-lg rounded-2xl bg-[#0e1424] border border-rose-900/40 p-6 shadow-2xl space-y-5 text-slate-100">
        {/* Warning Banner */}
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 shrink-0">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-white tracking-tight">
              Permanently Delete File?
            </h2>
            <p className="text-xs font-mono uppercase tracking-wider text-rose-400 font-semibold">
              Warning: Controlled user-confirmed deletion
            </p>
          </div>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed bg-rose-950/20 p-3 rounded-lg border border-rose-900/30">
          Are you sure you want to permanently delete this file? This operation cannot be undone. Digital Landfill AI never deletes files automatically.
        </p>

        {/* File Detail Specifications */}
        <div className="space-y-2.5 rounded-xl bg-slate-950/80 p-4 border border-slate-800 text-xs">
          <div className="flex items-start gap-2.5 pb-2 border-b border-slate-800">
            <FileText className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <div className="overflow-hidden">
              <span className="text-[10px] uppercase font-semibold text-slate-500 block">
                Filename
              </span>
              <span className="font-semibold text-white break-all">
                {file.name}
              </span>
            </div>
          </div>

          <div className="flex items-start gap-2.5 pb-2 border-b border-slate-800">
            <Folder className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <div className="overflow-hidden">
              <span className="text-[10px] uppercase font-semibold text-slate-500 block">
                Full Path
              </span>
              <span className="font-mono text-slate-300 break-all text-[11px]">
                {file.path}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="flex items-center gap-2">
              <HardDrive className="w-3.5 h-3.5 text-amber-400" />
              <div>
                <span className="text-[10px] uppercase text-slate-500 block">
                  Size
                </span>
                <span className="font-mono font-bold text-amber-300">
                  {file.sizeFormatted}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <div>
                <span className="text-[10px] uppercase text-slate-500 block">
                  Last Modified
                </span>
                <span className="text-slate-300 text-[11px]">
                  {file.modifiedAt} ({file.ageDays}d ago)
                </span>
              </div>
            </div>
          </div>

          {file.wasteReason && (
            <div className="pt-2 border-t border-slate-800 text-slate-400">
              <span className="text-[10px] uppercase text-slate-500 block font-semibold">
                Reason Flagged
              </span>
              <span className="text-slate-300">{file.wasteReason}</span>
            </div>
          )}
        </div>

        {/* Safety Note */}
        <div className="flex items-center gap-2 text-[11px] text-slate-400">
          <ShieldAlert className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>Explicit user confirmation logged for TCET audit trail.</span>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            disabled={isDeleting}
            onClick={onCancel}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors disabled:opacity-50 cursor-pointer"
          >
            Cancel
          </button>

          <button
            type="button"
            disabled={isDeleting}
            onClick={handleConfirm}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-lg shadow-rose-600/30 transition-all disabled:opacity-50 cursor-pointer"
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Deleting File...</span>
              </>
            ) : (
              <span>Confirm Delete</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
