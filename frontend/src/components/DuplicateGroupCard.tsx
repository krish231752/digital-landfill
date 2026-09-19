import React, { useState } from 'react';
import {
  Copy,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Folder,
  FileCheck,
  Trash2,
  ExternalLink,
} from 'lucide-react';
import { DuplicateGroup, FileItem } from '../types';
import { StatusBadge } from './StatusBadge';

interface DuplicateGroupCardProps {
  group: DuplicateGroup;
  onSendToCleanup?: (file: FileItem) => void;
  onReviewInInventory?: (file: FileItem) => void;
}

export const DuplicateGroupCard: React.FC<DuplicateGroupCardProps> = ({
  group,
  onSendToCleanup,
  onReviewInInventory,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);

  const handleCopyHash = () => {
    navigator.clipboard.writeText(group.sha256);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="rounded-xl bg-slate-900/70 border border-slate-800/80 overflow-hidden transition-all duration-200 hover:border-slate-700/80">
      {/* Top Header Card */}
      <div className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="inline-flex items-center gap-1.5 text-xs font-mono font-semibold text-cyan-400 uppercase tracking-wider">
              <Copy className="w-3.5 h-3.5" />
              Exact Duplicate
            </span>
            <StatusBadge level={group.priority} size="sm" />
            <span className="text-xs text-slate-400 font-mono">
              {group.copyCount} identical files
            </span>
          </div>

          <h3 className="text-base font-semibold text-white tracking-tight">
            {group.originalFileName}
          </h3>

          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>
              Redundant waste:{' '}
              <strong className="text-amber-400 font-mono">
                {group.redundantSizeFormatted}
              </strong>
            </span>
            <span className="text-slate-600">•</span>
            <span>
              Per copy: <span className="font-mono text-slate-300">{group.fileSizeFormatted}</span>
            </span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700/60 transition-colors"
          >
            <span>{isExpanded ? 'Hide Files' : 'View Files'}</span>
            {isExpanded ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setIsExpanded(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 text-xs font-medium text-cyan-300 border border-cyan-500/30 transition-colors"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Review Evidence</span>
          </button>
        </div>
      </div>

      {/* Expanded Evidence and File Location details */}
      {isExpanded && (
        <div className="border-t border-slate-800/80 bg-slate-950/60 p-5 space-y-4">
          {/* Cryptographic SHA-256 evidence block */}
          <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Cryptographic Evidence (SHA-256 Checksum)
              </span>
              <button
                type="button"
                onClick={handleCopyHash}
                className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer"
              >
                {copiedHash ? '✓ Hash Copied' : 'Copy Hash'}
              </button>
            </div>
            <p className="font-mono text-xs text-slate-300 break-all bg-slate-950/80 p-2 rounded border border-slate-800/60 select-all">
              {group.sha256}
            </p>
            <p className="text-[11px] text-slate-400 leading-normal">
              100% byte-for-byte exact match verified. Eliminating redundant copies carries 0% data corruption risk.
            </p>
          </div>

          {/* All duplicate locations */}
          <div>
            <div className="text-xs font-semibold text-slate-300 mb-2.5 flex items-center justify-between">
              <span>Discovered Duplicate Copies ({group.files.length})</span>
              <span className="text-[11px] text-slate-400">
                Controlled Action: Select redundant mirror copies to review or stage for deletion
              </span>
            </div>

            <div className="space-y-2">
              {group.files.map((file, idx) => {
                const isMaster = !file.isDuplicateCopy;
                return (
                  <div
                    key={file.id}
                    className={`p-3 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                      isMaster
                        ? 'bg-emerald-950/20 border-emerald-800/40 text-slate-200'
                        : 'bg-slate-900/80 border-slate-800 text-slate-300'
                    }`}
                  >
                    <div className="flex items-start gap-2.5 overflow-hidden">
                      <div className="mt-0.5 shrink-0">
                        {isMaster ? (
                          <span className="p-1 rounded bg-emerald-500/20 text-emerald-400 inline-flex">
                            <FileCheck className="w-4 h-4" />
                          </span>
                        ) : (
                          <span className="p-1 rounded bg-purple-500/20 text-purple-400 inline-flex">
                            <Copy className="w-4 h-4" />
                          </span>
                        )}
                      </div>

                      <div className="overflow-hidden space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-white truncate">
                            {file.name}
                          </span>
                          {isMaster ? (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-mono">
                              Master Copy (Recommended to Keep)
                            </span>
                          ) : (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 font-mono">
                              Redundant Mirror #{idx}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-2 text-xs text-slate-400 font-mono truncate">
                          <Folder className="w-3 h-3 text-slate-500 shrink-0" />
                          <span className="truncate">{file.path}</span>
                        </div>

                        <div className="text-[11px] text-slate-400">
                          Size: <span className="font-mono text-slate-300">{file.sizeFormatted}</span> • Modified: {file.modifiedAt}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                      {onReviewInInventory && (
                        <button
                          type="button"
                          onClick={() => onReviewInInventory(file)}
                          className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-xs transition-colors"
                          title="Inspect metadata in inventory"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </button>
                      )}

                      {!isMaster && onSendToCleanup && (
                        <button
                          type="button"
                          onClick={() => onSendToCleanup(file)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/50 text-xs font-medium transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                          <span>Review in Cleanup</span>
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
