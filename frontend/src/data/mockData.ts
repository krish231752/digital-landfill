import {
  CategoryDistribution,
  DuplicateGroup,
  FileCategory,
  FileItem,
  QwenAnalysisReport,
  RecommendationItem,
  ScanData,
  SeverityLevel,
} from '../types';

export function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export const CATEGORY_COLORS: Record<FileCategory, string> = {
  Documents: '#38bdf8', // Sky 400
  Images: '#a855f7',    // Purple 500
  Code: '#34d399',      // Emerald 400
  Datasets: '#f59e0b',  // Amber 500
  Videos: '#f43f5e',    // Rose 500
  Other: '#94a3b8',     // Slate 400
};

// Base 18 files totaling ~524 MB with exactly 1.2 MB duplicate waste and 1.3 MB immediate potential recovery
export const INITIAL_FILES: FileItem[] = [
  // Exact duplicate group (3 copies of 0.6 MB = 1.8 MB total, 1.2 MB redundant)
  {
    id: 'f-1',
    name: 'quarterly_financial_summary_2024.pdf',
    path: 'C:\\example\\folder\\reports\\quarterly_financial_summary_2024.pdf',
    category: 'Documents',
    sizeBytes: 629145, // 0.6 MB
    sizeFormatted: '614.4 KB',
    modifiedAt: '2024-03-12 14:22',
    lastModifiedEpoch: 1710253320000,
    ageDays: 190,
    sha256: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
    isDuplicate: true,
    duplicateGroupId: 'dup-1',
    isDuplicateCopy: false, // master
    isLarge: false,
    isStale: true,
    isTemp: false,
    wasteReason: 'Exact SHA-256 duplicate (Master copy)',
    status: 'Duplicate',
  },
  {
    id: 'f-2',
    name: 'quarterly_financial_summary_2024_copy.pdf',
    path: 'C:\\example\\folder\\backup\\quarterly_financial_summary_2024_copy.pdf',
    category: 'Documents',
    sizeBytes: 629145, // 0.6 MB
    sizeFormatted: '614.4 KB',
    modifiedAt: '2024-03-12 14:22',
    lastModifiedEpoch: 1710253320000,
    ageDays: 190,
    sha256: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
    isDuplicate: true,
    duplicateGroupId: 'dup-1',
    isDuplicateCopy: true, // redundant copy 1
    isLarge: false,
    isStale: true,
    isTemp: false,
    wasteReason: 'Redundant clone of quarterly_financial_summary_2024.pdf',
    status: 'Duplicate',
  },
  {
    id: 'f-3',
    name: 'quarterly_financial_summary_2024_v2.pdf',
    path: 'C:\\example\\folder\\downloads\\quarterly_financial_summary_2024_v2.pdf',
    category: 'Documents',
    sizeBytes: 629145, // 0.6 MB
    sizeFormatted: '614.4 KB',
    modifiedAt: '2024-03-12 14:22',
    lastModifiedEpoch: 1710253320000,
    ageDays: 190,
    sha256: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
    isDuplicate: true,
    duplicateGroupId: 'dup-1',
    isDuplicateCopy: true, // redundant copy 2
    isLarge: false,
    isStale: true,
    isTemp: false,
    wasteReason: 'Redundant clone of quarterly_financial_summary_2024.pdf',
    status: 'Duplicate',
  },

  // Stale files
  {
    id: 'f-4',
    name: 'old_contract.pdf',
    path: 'C:\\example\\folder\\legal\\old_contract.pdf',
    category: 'Documents',
    sizeBytes: 19293798, // 18.4 MB
    sizeFormatted: '18.4 MB',
    modifiedAt: '2024-01-12 09:15',
    lastModifiedEpoch: 1705050900000,
    ageDays: 250,
    sha256: '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
    isDuplicate: false,
    isLarge: false,
    isStale: true,
    isTemp: false,
    wasteReason: 'No modification for 250 days',
    status: 'Stale',
  },
  {
    id: 'f-5',
    name: 'legacy_vendor_agreement_2023.docx',
    path: 'C:\\example\\folder\\legal\\legacy_vendor_agreement_2023.docx',
    category: 'Documents',
    sizeBytes: 2411724, // 2.3 MB
    sizeFormatted: '2.3 MB',
    modifiedAt: '2023-11-05 16:40',
    lastModifiedEpoch: 1699202400000,
    ageDays: 318,
    sha256: 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d',
    isDuplicate: false,
    isLarge: false,
    isStale: true,
    isTemp: false,
    wasteReason: 'Unaccessed for 318 days',
    status: 'Stale',
  },

  // Large Files (>50 MB)
  {
    id: 'f-6',
    name: 'neural_checkpoint_epoch20.bin',
    path: 'C:\\example\\folder\\models\\neural_checkpoint_epoch20.bin',
    category: 'Datasets',
    sizeBytes: 262144000, // 250 MB
    sizeFormatted: '250.0 MB',
    modifiedAt: '2024-08-10 22:15',
    lastModifiedEpoch: 1723328100000,
    ageDays: 40,
    sha256: 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
    isDuplicate: false,
    isLarge: true,
    isStale: false,
    isTemp: false,
    status: 'Active',
  },
  {
    id: 'f-7',
    name: 'city_satellite_imagery_raw.tif',
    path: 'C:\\example\\folder\\assets\\city_satellite_imagery_raw.tif',
    category: 'Images',
    sizeBytes: 146800640, // 140 MB
    sizeFormatted: '140.0 MB',
    modifiedAt: '2024-07-28 11:00',
    lastModifiedEpoch: 1722164400000,
    ageDays: 53,
    sha256: 'cb340eed2ee40b3ffdd715102ffc4eb5907409c95d909569055e88fa2b740ef8',
    isDuplicate: false,
    isLarge: true,
    isStale: false,
    isTemp: false,
    status: 'Active',
  },
  {
    id: 'f-8',
    name: 'training_telemetry_dump.parquet',
    path: 'C:\\example\\folder\\telemetry\\training_telemetry_dump.parquet',
    category: 'Datasets',
    sizeBytes: 85983232, // 82 MB
    sizeFormatted: '82.0 MB',
    modifiedAt: '2024-08-20 18:30',
    lastModifiedEpoch: 1724178600000,
    ageDays: 30,
    sha256: '3a5ca800fe7342d1864e1773149ba5ebf3ddbbbe92b0e3f7bc011a7a22025324',
    isDuplicate: false,
    isLarge: true,
    isStale: false,
    isTemp: false,
    status: 'Active',
  },

  // Temp & Cache files
  {
    id: 'f-9',
    name: 'debug_runtime_session.log',
    path: 'C:\\example\\folder\\logs\\debug_runtime_session.log',
    category: 'Other',
    sizeBytes: 68157, // ~66 KB
    sizeFormatted: '66.5 KB',
    modifiedAt: '2024-09-01 03:10',
    lastModifiedEpoch: 1725160200000,
    ageDays: 18,
    sha256: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
    isDuplicate: false,
    isLarge: false,
    isStale: false,
    isTemp: true,
    wasteReason: 'Temporary session logging artifact',
    status: 'Temporary',
  },
  {
    id: 'f-10',
    name: 'intermediate_build.cache',
    path: 'C:\\example\\folder\\.cache\\intermediate_build.cache',
    category: 'Other',
    sizeBytes: 36700, // ~35 KB
    sizeFormatted: '35.8 KB',
    modifiedAt: '2024-09-05 12:00',
    lastModifiedEpoch: 1725537600000,
    ageDays: 14,
    sha256: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
    isDuplicate: false,
    isLarge: false,
    isStale: false,
    isTemp: true,
    wasteReason: 'Orphaned build cache candidate',
    status: 'Temporary',
  },

  // Videos
  {
    id: 'f-11',
    name: 'demo_walkthrough_prototype.mp4',
    path: 'C:\\example\\folder\\media\\demo_walkthrough_prototype.mp4',
    category: 'Videos',
    sizeBytes: 25165824, // 24 MB
    sizeFormatted: '24.0 MB',
    modifiedAt: '2024-08-15 15:45',
    lastModifiedEpoch: 1723736700000,
    ageDays: 35,
    sha256: '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945',
    isDuplicate: false,
    isLarge: false,
    isStale: false,
    isTemp: false,
    status: 'Active',
  },

  // Code files
  {
    id: 'f-12',
    name: 'waste_detector_pipeline.py',
    path: 'C:\\example\\folder\\src\\waste_detector_pipeline.py',
    category: 'Code',
    sizeBytes: 15420,
    sizeFormatted: '15.1 KB',
    modifiedAt: '2024-09-12 11:30',
    lastModifiedEpoch: 1726140600000,
    ageDays: 7,
    sha256: 'ecd71870d1963316a97e3ac3408c9835ad8cf0f3c1bc703527c30265534f75ae',
    isDuplicate: false,
    isLarge: false,
    isStale: false,
    isTemp: false,
    status: 'Active',
  },
  {
    id: 'f-13',
    name: 'hash_calculator.ts',
    path: 'C:\\example\\folder\\src\\hash_calculator.ts',
    category: 'Code',
    sizeBytes: 8430,
    sizeFormatted: '8.2 KB',
    modifiedAt: '2024-09-10 18:20',
    lastModifiedEpoch: 1725992400000,
    ageDays: 9,
    sha256: '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae',
    isDuplicate: false,
    isLarge: false,
    isStale: false,
    isTemp: false,
    status: 'Active',
  },
  {
    id: 'f-14',
    name: 'storage_analytics_schema.sql',
    path: 'C:\\example\\folder\\db\\storage_analytics_schema.sql',
    category: 'Code',
    sizeBytes: 12288,
    sizeFormatted: '12.0 KB',
    modifiedAt: '2024-08-01 10:00',
    lastModifiedEpoch: 1722506400000,
    ageDays: 49,
    sha256: 'fcde2b2edba56bf408601fb721fe9b5c338d10ee429ea04fae5511b68fbf8fb9',
    isDuplicate: false,
    isLarge: false,
    isStale: false,
    isTemp: false,
    status: 'Active',
  },

  // Images
  {
    id: 'f-15',
    name: 'architecture_diagram_v3.png',
    path: 'C:\\example\\folder\\diagrams\\architecture_diagram_v3.png',
    category: 'Images',
    sizeBytes: 3145728, // 3 MB
    sizeFormatted: '3.0 MB',
    modifiedAt: '2024-09-08 17:00',
    lastModifiedEpoch: 1725814800000,
    ageDays: 11,
    sha256: 'b45cffe084dd3d20d928bee85e7b0f21',
    isDuplicate: false,
    isLarge: false,
    isStale: false,
    isTemp: false,
    status: 'Active',
  },
  {
    id: 'f-16',
    name: 'tcet_coe_gateway_badge.svg',
    path: 'C:\\example\\folder\\assets\\tcet_coe_gateway_badge.svg',
    category: 'Images',
    sizeBytes: 51200, // 50 KB
    sizeFormatted: '50.0 KB',
    modifiedAt: '2024-09-14 09:20',
    lastModifiedEpoch: 1726305600000,
    ageDays: 5,
    sha256: 'd5579c46dfcc7f18207013fa5cc6b8656fa61',
    isDuplicate: false,
    isLarge: false,
    isStale: false,
    isTemp: false,
    status: 'Active',
  },

  // Other documents & datasets
  {
    id: 'f-17',
    name: 'benchmark_results_synthetic.csv',
    path: 'C:\\example\\folder\\data\\benchmark_results_synthetic.csv',
    category: 'Datasets',
    sizeBytes: 1572864, // 1.5 MB
    sizeFormatted: '1.5 MB',
    modifiedAt: '2024-09-02 14:10',
    lastModifiedEpoch: 1725286200000,
    ageDays: 17,
    sha256: 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',
    isDuplicate: false,
    isLarge: false,
    isStale: false,
    isTemp: false,
    status: 'Active',
  },
  {
    id: 'f-18',
    name: 'project_onboarding_guide.md',
    path: 'C:\\example\\folder\\docs\\project_onboarding_guide.md',
    category: 'Documents',
    sizeBytes: 28400,
    sizeFormatted: '27.7 KB',
    modifiedAt: '2024-09-15 16:20',
    lastModifiedEpoch: 1726417200000,
    ageDays: 4,
    sha256: '73475cb40a568e8da8a045ced110137e159f890ac4daecf868d308cbde39886b',
    isDuplicate: false,
    isLarge: false,
    isStale: false,
    isTemp: false,
    status: 'Active',
  },
];

export function computeScanData(
  files: FileItem[],
  folderPath = 'C:\\example\\folder'
): ScanData {
  const totalFiles = files.length;
  const totalSizeBytes = files.reduce((acc, f) => acc + f.sizeBytes, 0);

  // Calculate Duplicate Groups
  const groupMap = new Map<string, FileItem[]>();
  for (const f of files) {
    if (f.isDuplicate && f.duplicateGroupId) {
      if (!groupMap.has(f.duplicateGroupId)) {
        groupMap.set(f.duplicateGroupId, []);
      }
      groupMap.get(f.duplicateGroupId)!.push(f);
    }
  }

  const duplicateGroups: DuplicateGroup[] = [];
  let duplicateWasteBytes = 0;

  groupMap.forEach((groupFiles, groupId) => {
    if (groupFiles.length > 1) {
      const singleSize = groupFiles[0].sizeBytes;
      const redundantBytes = singleSize * (groupFiles.length - 1);
      duplicateWasteBytes += redundantBytes;
      duplicateGroups.push({
        id: groupId,
        sha256: groupFiles[0].sha256,
        originalFileName: groupFiles[0].name,
        fileSizeFormatted: formatBytes(singleSize),
        fileSizeBytes: singleSize,
        copyCount: groupFiles.length,
        redundantSizeBytes: redundantBytes,
        redundantSizeFormatted: formatBytes(redundantBytes),
        priority: redundantBytes > 1024 * 1024 ? 'HIGH' : 'MEDIUM',
        files: groupFiles,
      });
    }
  });

  // Calculate waste signals
  const largeFilesList = files.filter((f) => f.isLarge);
  const largeFilesBytes = largeFilesList.reduce((acc, f) => acc + f.sizeBytes, 0);

  const staleFilesList = files.filter((f) => f.isStale && !f.isDuplicateCopy);
  const staleFilesBytes = staleFilesList.reduce((acc, f) => acc + f.sizeBytes, 0);

  const tempFilesList = files.filter((f) => f.isTemp);
  const tempFilesBytes = tempFilesList.reduce((acc, f) => acc + f.sizeBytes, 0);

  // Immediate recovery: redundant duplicates (1.2 MB) + temp files (0.1 MB) = 1.3 MB
  const potentialRecoveryBytes = duplicateWasteBytes + tempFilesBytes;

  // Categories distribution
  const categoryOrder: FileCategory[] = [
    'Documents',
    'Images',
    'Code',
    'Datasets',
    'Videos',
    'Other',
  ];

  const categories: CategoryDistribution[] = categoryOrder.map((cat) => {
    const catFiles = files.filter((f) => f.category === cat);
    const bytes = catFiles.reduce((acc, f) => acc + f.sizeBytes, 0);
    const count = catFiles.length;
    const percentage = totalSizeBytes > 0 ? (bytes / totalSizeBytes) * 100 : 0;
    return {
      category: cat,
      count,
      bytes,
      formatted: formatBytes(bytes),
      percentage: Number(percentage.toFixed(1)),
      color: CATEGORY_COLORS[cat],
    };
  });

  // Waste Score & Indicator
  // Normalized score: weight duplicates, stale items, and temp
  let wasteScore = 0;
  if (totalSizeBytes > 0) {
    const dupRatio = (duplicateWasteBytes / totalSizeBytes) * 100;
    const staleRatio = (staleFilesBytes / totalSizeBytes) * 100;
    const tempRatio = (tempFilesBytes / totalSizeBytes) * 100;
    // Weighted composite
    wasteScore = Math.min(
      100,
      Math.round(dupRatio * 15 + staleRatio * 0.8 + tempRatio * 10 + (duplicateGroups.length > 0 ? 30 : 0))
    );
  }

  let wasteIndicator: SeverityLevel = 'LOW';
  if (wasteScore >= 75) wasteIndicator = 'CRITICAL';
  else if (wasteScore >= 45) wasteIndicator = 'HIGH';
  else if (wasteScore >= 20 || duplicateGroups.length > 0) wasteIndicator = 'MEDIUM';
  else wasteIndicator = 'LOW';

  // Signals
  const signals = {
    duplicates: {
      count: files.filter((f) => f.isDuplicateCopy).length,
      storageBytes: duplicateWasteBytes,
      storageFormatted: formatBytes(duplicateWasteBytes),
      severity: (duplicateWasteBytes > 1024 * 1024 ? 'HIGH' : 'MEDIUM') as SeverityLevel,
      description: 'Identical SHA-256 byte hashes discovered in multiple directories',
    },
    largeFiles: {
      count: largeFilesList.length,
      storageBytes: largeFilesBytes,
      storageFormatted: formatBytes(largeFilesBytes),
      severity: (largeFilesBytes > 200 * 1024 * 1024 ? 'HIGH' : 'MEDIUM') as SeverityLevel,
      description: 'High-density files exceeding 50 MB threshold',
    },
    staleFiles: {
      count: staleFilesList.length,
      storageBytes: staleFilesBytes,
      storageFormatted: formatBytes(staleFilesBytes),
      severity: (staleFilesList.length > 2 ? 'MEDIUM' : 'LOW') as SeverityLevel,
      description: 'Dormant files with zero modifications for >90 days',
    },
    tempFiles: {
      count: tempFilesList.length,
      storageBytes: tempFilesBytes,
      storageFormatted: formatBytes(tempFilesBytes),
      severity: (tempFilesList.length > 0 ? 'LOW' : 'LOW') as SeverityLevel,
      description: 'Log caches and transient build artifacts safe for purge',
    },
  };

  // Phase 4 Recommendations
  const recommendations: RecommendationItem[] = [];

  if (duplicateGroups.length > 0) {
    const totalCopies = duplicateGroups.reduce((acc, g) => acc + g.copyCount, 0);
    recommendations.push({
      id: 'rec-1',
      priority: 'HIGH',
      title: 'Exact Duplicate Review',
      affectedCopiesCount: totalCopies,
      potentialRecoveryBytes: duplicateWasteBytes,
      potentialRecoveryFormatted: formatBytes(duplicateWasteBytes),
      whyFlagged: [
        'SHA-256 exact match across disjoint directories',
        `${totalCopies} identical copies verified`,
        'Measurable redundant storage consuming active disk sectors',
      ],
      evidenceConfidence: 'HIGH',
      suggestedAction:
        'Review duplicate copies. Keep the primary master copy in /reports and delete redundant copies in /backup and /downloads.',
      category: 'Documents',
      candidateFileIds: files.filter((f) => f.isDuplicateCopy).map((f) => f.id),
      qwenExplanation:
        'Cryptographic hash verification confirmed identical payload between reports and backup mirrors. Retaining a single authoritative copy frees 1.2 MB with 0% data loss risk.',
    });
  }

  if (tempFilesList.length > 0) {
    recommendations.push({
      id: 'rec-2',
      priority: 'LOW',
      title: 'Purge Temporary & Runtime Log Caches',
      affectedCopiesCount: tempFilesList.length,
      potentialRecoveryBytes: tempFilesBytes,
      potentialRecoveryFormatted: formatBytes(tempFilesBytes),
      whyFlagged: [
        'Transient .log and .cache suffixes detected',
        'No active running process locks identified',
        'Regenerated automatically upon next development build',
      ],
      evidenceConfidence: 'HIGH',
      suggestedAction:
        'Safely remove transient debug traces to eliminate filesystem clutter.',
      category: 'Other',
      candidateFileIds: tempFilesList.map((f) => f.id),
      qwenExplanation:
        'Log buffers from past runtime debugging sessions represent non-recoverable dead history. Purging improves directory indexing speed.',
    });
  }

  if (staleFilesList.length > 0) {
    recommendations.push({
      id: 'rec-3',
      priority: 'MEDIUM',
      title: 'Archive Unmodified Stale Contracts & Documents',
      affectedCopiesCount: staleFilesList.length,
      potentialRecoveryBytes: staleFilesBytes,
      potentialRecoveryFormatted: formatBytes(staleFilesBytes),
      whyFlagged: [
        'Files unmodified for over 250 days',
        'Includes 18.4 MB legacy legal contract scan',
        'Low access frequency metric detected',
      ],
      evidenceConfidence: 'MEDIUM',
      suggestedAction:
        'Transfer dormant contracts to cold cloud archival or review necessity of old_contract.pdf.',
      category: 'Documents',
      candidateFileIds: staleFilesList.map((f) => f.id),
      qwenExplanation:
        'old_contract.pdf occupies 18.4 MB without modification for 250 days. Archiving to compressed storage reduces local disk load without destroying compliance records.',
    });
  }

  return {
    folderPath,
    totalFiles,
    totalSizeBytes,
    totalSizeFormatted: formatBytes(totalSizeBytes),
    duplicateWasteBytes,
    duplicateWasteFormatted: formatBytes(duplicateWasteBytes),
    potentialRecoveryBytes,
    potentialRecoveryFormatted: formatBytes(potentialRecoveryBytes),
    wasteIndicator,
    wasteScore,
    scannedAt: 'Today, ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    categories,
    signals,
    files,
    duplicateGroups,
    recommendations,
  };
}

export const DEFAULT_QWEN_REPORT: QwenAnalysisReport = {
  summary:
    'Storage analysis indicates an active project repository holding 524 MB across 18 distinct files. Waste telemetry identifies immediate, risk-free reclamation opportunities in duplicate documents and orphaned runtime cache files.',
  keyFindings: [
    'Exact duplicate files account for 1.2 MB of pure byte redundancy validated by cryptographic SHA-256 signatures.',
    'Heavyweight model checkpoints and satellite imagery comprise ~74% of gross storage footprint (390 MB).',
    'Dormant legal scans (e.g. old_contract.pdf, 18.4 MB) have experienced zero write operations for over 250 days.',
    'Transient cache and log artifacts can be cleared immediately with zero application impact.',
  ],
  wasteAnalysis: [
    {
      topic: 'Exact Duplicate Redundancy',
      detail:
        'Three bit-for-bit identical copies of quarterly financial summaries exist across /reports, /backup, and /downloads directories.',
      impact: '1.2 MB redundant space',
    },
    {
      topic: 'Dormant Cold Assets',
      detail:
        'Uncompressed PDF contract scans from Q1 2024 sit in primary active storage without archival compression.',
      impact: '18.4 MB stale space',
    },
    {
      topic: 'Session Cache Leftovers',
      detail:
        'Runtime debug trace and build cache files linger after execution sessions without auto-cleanup hooks.',
      impact: '102.3 KB temporary clutter',
    },
  ],
  reviewRecommendations: [
    {
      action: 'Consolidate duplicate quarterly summary into single master under /reports',
      rationale:
        'SHA-256 byte parity guarantees zero data variance. Deleting the two mirrors frees 1.2 MB immediately.',
      riskLevel: 'Low',
    },
    {
      action: 'Purge intermediate_build.cache and debug_runtime_session.log',
      rationale: 'Logs and caches will be cleanly recreated if needed during future pipelines.',
      riskLevel: 'Low',
    },
    {
      action: 'Migrate old_contract.pdf to compressed zip or cold archival storage',
      rationale:
        'File is legally important but not accessed in 250 days. Compression or relocation saves 18 MB.',
      riskLevel: 'Moderate',
    },
  ],
  potentialRecovery: {
    immediate: '1.3 MB (100% risk-free)',
    withArchival: '19.7 MB (includes cold document compression)',
    projectedWasteReduction: '68% waste index drop',
  },
  limitations: [
    'AI recommendations do NOT execute autonomously. Deletion requires explicit user confirmation per file.',
    'Model inference evaluates metadata, headers, and cryptographic fingerprints; sensitive document contents remain private.',
    'Large neural model checkpoints (.bin, .parquet) are classified as active project assets and excluded from purge suggestions.',
  ],
  modelInfo: {
    model: 'Qwen3.6-35B-A3B',
    gateway: 'TCET CoE AI Gateway',
    status: 'Connected',
    timestamp: '2026-09-19',
  },
};
