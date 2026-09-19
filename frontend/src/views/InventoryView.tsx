import React from 'react';
import { Database, Filter, Layers, HardDrive } from 'lucide-react';
import { FileItem, NavigationTab, ScanData } from '../types';
import { SectionHeader } from '../components/SectionHeader';
import { FileTable } from '../components/FileTable';

interface InventoryViewProps {
  scanData: ScanData;
  onNavigate: (tab: NavigationTab) => void;
  onSelectFile: (file: FileItem) => void;
  onDeleteRequest?: (file: FileItem) => void;
}

export const InventoryView: React.FC<InventoryViewProps> = ({
  scanData,
  onNavigate,
  onSelectFile,
  onDeleteRequest,
}) => {
  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <SectionHeader
        title="Full Inventory Explorer"
        subtitle="Complete catalog of files indexed with cryptographic hashes, decay age, and waste signals."
        badge={
          <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700 font-mono">
            {scanData.totalFiles} Indexed Files ({scanData.totalSizeFormatted})
          </span>
        }
      />

      <FileTable
        files={scanData.files}
        onSelectFile={onSelectFile}
        onDeleteRequest={onDeleteRequest}
      />
    </div>
  );
};
