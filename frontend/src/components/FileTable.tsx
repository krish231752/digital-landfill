import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Eye,
  Trash2,
  FileCode,
  FileSpreadsheet,
  FileImage,
  Video,
  FileText,
  File,
  Sparkles,
} from 'lucide-react';
import { FileCategory, FileItem } from '../types';
import { StatusBadge } from './StatusBadge';

interface FileTableProps {
  files: FileItem[];
  onSelectFile: (file: FileItem) => void;
  onDeleteRequest?: (file: FileItem) => void;
}

export const FileTable: React.FC<FileTableProps> = ({
  files,
  onSelectFile,
  onDeleteRequest,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedSizeFilter, setSelectedSizeFilter] = useState<string>('All');
  const [selectedAgeFilter, setSelectedAgeFilter] = useState<string>('All');
  const [sortField, setSortField] = useState<'name' | 'size' | 'age' | 'category'>('size');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  const getCategoryIcon = (category: FileCategory) => {
    switch (category) {
      case 'Code':
        return <FileCode className="w-4 h-4 text-emerald-400 shrink-0" />;
      case 'Datasets':
        return <FileSpreadsheet className="w-4 h-4 text-amber-400 shrink-0" />;
      case 'Images':
        return <FileImage className="w-4 h-4 text-purple-400 shrink-0" />;
      case 'Videos':
        return <Video className="w-4 h-4 text-rose-400 shrink-0" />;
      case 'Documents':
        return <FileText className="w-4 h-4 text-cyan-400 shrink-0" />;
      default:
        return <File className="w-4 h-4 text-slate-400 shrink-0" />;
    }
  };

  const filteredFiles = useMemo(() => {
    return files.filter((file) => {
      // Search term
      const matchesSearch =
        file.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        file.path.toLowerCase().includes(searchTerm.toLowerCase()) ||
        file.sha256.toLowerCase().includes(searchTerm.toLowerCase());

      // Category
      const matchesCategory =
        selectedCategory === 'All' || file.category === selectedCategory;

      // Size
      let matchesSize = true;
      if (selectedSizeFilter === '<1MB') {
        matchesSize = file.sizeBytes < 1024 * 1024;
      } else if (selectedSizeFilter === '1-50MB') {
        matchesSize =
          file.sizeBytes >= 1024 * 1024 && file.sizeBytes <= 50 * 1024 * 1024;
      } else if (selectedSizeFilter === '>50MB') {
        matchesSize = file.sizeBytes > 50 * 1024 * 1024;
      }

      // Age
      let matchesAge = true;
      if (selectedAgeFilter === '<30d') {
        matchesAge = file.ageDays < 30;
      } else if (selectedAgeFilter === '30-90d') {
        matchesAge = file.ageDays >= 30 && file.ageDays <= 90;
      } else if (selectedAgeFilter === '>90d') {
        matchesAge = file.ageDays > 90;
      } else if (selectedAgeFilter === '>180d') {
        matchesAge = file.ageDays > 180;
      }

      return matchesSearch && matchesCategory && matchesSize && matchesAge;
    });
  }, [files, searchTerm, selectedCategory, selectedSizeFilter, selectedAgeFilter]);

  const sortedFiles = useMemo(() => {
    return [...filteredFiles].sort((a, b) => {
      let comparison = 0;
      if (sortField === 'size') {
        comparison = a.sizeBytes - b.sizeBytes;
      } else if (sortField === 'age') {
        comparison = a.ageDays - b.ageDays;
      } else if (sortField === 'name') {
        comparison = a.name.localeCompare(b.name);
      } else if (sortField === 'category') {
        comparison = a.category.localeCompare(b.category);
      }
      return sortOrder === 'desc' ? -comparison : comparison;
    });
  }, [filteredFiles, sortField, sortOrder]);

  const totalPages = Math.max(1, Math.ceil(sortedFiles.length / itemsPerPage));
  const paginatedFiles = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return sortedFiles.slice(start, start + itemsPerPage);
  }, [sortedFiles, currentPage, itemsPerPage]);

  const handleSort = (field: 'name' | 'size' | 'age' | 'category') => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  return (
    <div className="space-y-4">
      {/* Controls Bar: Search + Filters */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by name, path, hash..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        {/* Category Filter */}
        <div className="relative">
          <select
            value={selectedCategory}
            onChange={(e) => {
              setSelectedCategory(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full px-3 py-2 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition-colors cursor-pointer appearance-none"
          >
            <option value="All">All Categories ({files.length})</option>
            <option value="Documents">Documents</option>
            <option value="Images">Images</option>
            <option value="Code">Code</option>
            <option value="Datasets">Datasets</option>
            <option value="Videos">Videos</option>
            <option value="Other">Other</option>
          </select>
        </div>

        {/* Size Filter */}
        <div className="relative">
          <select
            value={selectedSizeFilter}
            onChange={(e) => {
              setSelectedSizeFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full px-3 py-2 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition-colors cursor-pointer appearance-none"
          >
            <option value="All">All Sizes</option>
            <option value="<1MB">&lt; 1 MB (Small)</option>
            <option value="1-50MB">1 MB - 50 MB (Medium)</option>
            <option value=">50MB">&gt; 50 MB (Heavyweight)</option>
          </select>
        </div>

        {/* Age Filter */}
        <div className="relative">
          <select
            value={selectedAgeFilter}
            onChange={(e) => {
              setSelectedAgeFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full px-3 py-2 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition-colors cursor-pointer appearance-none"
          >
            <option value="All">All Ages</option>
            <option value="<30d">&lt; 30 days (Recent)</option>
            <option value="30-90d">30 - 90 days (Active)</option>
            <option value=">90d">&gt; 90 days (Stale Candidate)</option>
            <option value=">180d">&gt; 180 days (Legacy/Dormant)</option>
          </select>
        </div>
      </div>

      {/* Table Container */}
      <div className="rounded-xl bg-slate-900/70 border border-slate-800 overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/80 text-slate-400 font-mono text-[11px] uppercase tracking-wider">
                <th
                  onClick={() => handleSort('name')}
                  className="py-3 px-4 font-semibold cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Name</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-500" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('category')}
                  className="py-3 px-4 font-semibold cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Category</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-500" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('size')}
                  className="py-3 px-4 font-semibold cursor-pointer hover:text-white transition-colors text-right"
                >
                  <div className="flex items-center justify-end gap-1.5">
                    <span>Size</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-500" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('age')}
                  className="py-3 px-4 font-semibold cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Modified / Age</span>
                    <ArrowUpDown className="w-3 h-3 text-slate-500" />
                  </div>
                </th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">Waste Signals</th>
                <th className="py-3 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-800/60">
              {paginatedFiles.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    No files match the current search filters.
                  </td>
                </tr>
              ) : (
                paginatedFiles.map((file) => (
                  <tr
                    key={file.id}
                    onClick={() => onSelectFile(file)}
                    className="hover:bg-slate-800/40 transition-colors cursor-pointer group"
                  >
                    {/* Name & icon */}
                    <td className="py-3 px-4 max-w-xs">
                      <div className="flex items-center gap-2.5 overflow-hidden">
                        {getCategoryIcon(file.category)}
                        <div className="overflow-hidden">
                          <span className="font-semibold text-white truncate block group-hover:text-cyan-300 transition-colors">
                            {file.name}
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono truncate block">
                            {file.path}
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Category */}
                    <td className="py-3 px-4">
                      <span className="text-slate-300 font-medium">
                        {file.category}
                      </span>
                    </td>

                    {/* Size */}
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-200">
                      {file.sizeFormatted}
                    </td>

                    {/* Modified / Age */}
                    <td className="py-3 px-4">
                      <div className="text-slate-300">{file.modifiedAt}</div>
                      <div className="text-[10px] font-mono text-slate-500">
                        {file.ageDays} days ago
                      </div>
                    </td>

                    {/* Status */}
                    <td className="py-3 px-4">
                      <StatusBadge level={file.status} size="sm" />
                    </td>

                    {/* Waste Signals */}
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {file.isDuplicate && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-purple-950/60 text-purple-300 border border-purple-800/50 font-mono">
                            {file.isDuplicateCopy ? 'Duplicate Copy' : 'Master Dup'}
                          </span>
                        )}
                        {file.isStale && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-800/50 font-mono">
                            Stale ({file.ageDays}d)
                          </span>
                        )}
                        {file.isTemp && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950/60 text-blue-300 border border-blue-800/50 font-mono">
                            Temp/Log
                          </span>
                        )}
                        {file.isLarge && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800/50 font-mono">
                            Large
                          </span>
                        )}
                        {!file.isDuplicate && !file.isStale && !file.isTemp && !file.isLarge && (
                          <span className="text-[10px] text-slate-500 font-mono">
                            Clean
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Actions */}
                    <td className="py-3 px-4 text-right">
                      <div
                        className="flex items-center justify-end gap-1.5"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          type="button"
                          onClick={() => onSelectFile(file)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                          title="View metadata and waste assessment"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        {onDeleteRequest && (
                          <button
                            type="button"
                            onClick={() => onDeleteRequest(file)}
                            className="p-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/50 transition-colors"
                            title="Controlled deletion"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination & Status Footer */}
        <div className="py-3 px-4 border-t border-slate-800 bg-slate-950/60 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
          <div>
            Showing{' '}
            <span className="font-mono text-white">
              {filteredFiles.length === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1}
            </span>{' '}
            to{' '}
            <span className="font-mono text-white">
              {Math.min(currentPage * itemsPerPage, filteredFiles.length)}
            </span>{' '}
            of <span className="font-mono text-white">{filteredFiles.length}</span> files
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:hover:bg-slate-800 cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono text-slate-300 px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              type="button"
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:hover:bg-slate-800 cursor-pointer"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
