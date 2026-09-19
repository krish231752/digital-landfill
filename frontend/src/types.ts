export type NavigationTab =
  | 'overview'
  | 'waste_intelligence'
  | 'duplicates'
  | 'recommendations'
  | 'ai_intelligence'
  | 'cleanup'
  | 'inventory';

export type FileCategory =
  | 'Documents'
  | 'Images'
  | 'Code'
  | 'Datasets'
  | 'Videos'
  | 'Other';

export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface FileItem {
  id: string;
  name: string;
  path: string;
  category: FileCategory;
  sizeBytes: number;
  sizeFormatted: string;
  modifiedAt: string;
  lastModifiedEpoch: number;
  ageDays: number;
  sha256: string;
  isDuplicate: boolean;
  duplicateGroupId?: string;
  isDuplicateCopy?: boolean; // redundant clone vs original
  isLarge: boolean; // >50MB
  isStale: boolean; // >90 days
  isTemp: boolean; // temporary or cache
  wasteReason?: string;
  status: 'Active' | 'Duplicate' | 'Stale' | 'Temporary';
}

export interface DuplicateGroup {
  id: string;
  sha256: string;
  originalFileName: string;
  fileSizeFormatted: string;
  fileSizeBytes: number;
  copyCount: number;
  redundantSizeBytes: number;
  redundantSizeFormatted: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  files: FileItem[];
}

export interface WasteSignalSummary {
  count: number;
  storageBytes: number;
  storageFormatted: string;
  severity: SeverityLevel;
  description: string;
}

export interface RecommendationItem {
  id: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  affectedCopiesCount: number;
  potentialRecoveryBytes: number;
  potentialRecoveryFormatted: string;
  whyFlagged: string[];
  evidenceConfidence: 'HIGH' | 'MEDIUM' | 'LOW';
  suggestedAction: string;
  category: FileCategory;
  candidateFileIds: string[];
  qwenExplanation: string;
}

export interface CategoryDistribution {
  category: FileCategory;
  count: number;
  bytes: number;
  formatted: string;
  percentage: number;
  color: string;
}

export interface ScanData {
  folderPath: string;
  totalFiles: number;
  totalSizeBytes: number;
  totalSizeFormatted: string;
  duplicateWasteBytes: number;
  duplicateWasteFormatted: string;
  potentialRecoveryBytes: number;
  potentialRecoveryFormatted: string;
  wasteIndicator: SeverityLevel;
  wasteScore: number; // 0 - 100
  scannedAt: string;
  categories: CategoryDistribution[];
  signals: {
    duplicates: WasteSignalSummary;
    largeFiles: WasteSignalSummary;
    staleFiles: WasteSignalSummary;
    tempFiles: WasteSignalSummary;
  };
  files: FileItem[];
  duplicateGroups: DuplicateGroup[];
  recommendations: RecommendationItem[];
}

export interface QwenAnalysisReport {
  summary: string;
  keyFindings: string[];
  wasteAnalysis: {
    topic: string;
    detail: string;
    impact: string;
  }[];
  reviewRecommendations: {
    action: string;
    rationale: string;
    riskLevel: 'Low' | 'Moderate' | 'High';
  }[];
  potentialRecovery: {
    immediate: string;
    withArchival: string;
    projectedWasteReduction: string;
  };
  limitations: string[];
  modelInfo: {
    model: string;
    gateway: string;
    status: 'Connected' | 'Offline' | 'Analyzing';
    timestamp: string;
  };
}
