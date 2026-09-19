/**
 * Digital Landfill API Client
 *
 * Typesafe bridge connecting the React frontend directly to the FastAPI backend.
 * All business logic, scanning, hashing, and Qwen AI synthesis remain strictly
 * in the Python backend.
 */

import {
  FileItem,
  QwenAnalysisReport,
  RecommendationItem,
  ScanData,
} from '../types';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '') || 'http://127.0.0.1:8000';

async function fetchJson<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {}),
      },
    });

    if (!response.ok) {
      let errorDetail = `HTTP ${response.status} ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorDetail = errorData.detail;
        }
      } catch {
        // Fallback to status text
      }
      throw new Error(errorDetail);
    }

    return await response.json();
  } catch (err: any) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error(
        `Unable to connect to Digital Landfill Backend at ${API_BASE_URL}. Ensure FastAPI server is running.`
      );
    }
    throw err;
  }
}

export interface HealthResponse {
  status: string;
  service: string;
  deployment_mode: 'local' | 'demo';
  is_demo_mode: boolean;
  has_active_scan: boolean;
  scanned_root: string | null;
  total_files: number;
  demo_dir: string | null;
  qwen_gateway: {
    status: 'Connected' | 'Not Configured' | 'Offline';
    badge: string;
    detail: string;
    model: string;
    base_url: string;
  };
}

export interface SummaryResponse {
  root_name: string;
  folder_path: string;
  total_files: number;
  total_size_bytes: number;
  total_size_label: string;
  duplicate_waste_bytes: number;
  duplicate_waste_label: string;
  potential_recovery_bytes: number;
  potential_recovery_label: string;
  waste_score: number;
  waste_indicator: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  scanned_at: string;
  categories: any[];
  signals: any;
}

export interface ScanResponse {
  status: string;
  message: string;
  errors_count: number;
  data: ScanData;
}

export interface DeleteResponse {
  status: string;
  message: string;
  deleted_path: string;
  reclaimed_bytes: number;
  data: ScanData;
}

export interface QwenAnalyzeResponse {
  raw_text: string;
  model_info: {
    model: string;
    gateway: string;
    status: 'Connected' | 'Offline' | 'Analyzing';
    timestamp: string;
  };
}

export interface QwenExplainResponse {
  recommendation_id: string;
  explanation: string;
}

export interface QwenAskResponse {
  query: string;
  answer: string;
  model: string;
}

export const apiClient = {
  /**
   * Check backend health and Qwen AI status
   */
  async getHealth(): Promise<HealthResponse> {
    return fetchJson<HealthResponse>('/api/health');
  },

  /**
   * Get top-level summary metrics (guaranteed root_name)
   */
  async getSummary(): Promise<SummaryResponse> {
    return fetchJson<SummaryResponse>('/api/summary');
  },

  /**
   * Get full ScanData payload matching the UI state
   */
  async getScanData(): Promise<ScanData> {
    return fetchJson<ScanData>('/api/scan_data');
  },

  /**
   * Initiate scanning on a local target directory
   */
  async scanFolder(
    rootPath: string,
    skipHidden = true,
    maxFiles?: number,
    largeThresholdMb = 100,
    staleDaysThreshold = 180
  ): Promise<ScanResponse> {
    return fetchJson<ScanResponse>('/api/scan', {
      method: 'POST',
      body: JSON.stringify({
        root_path: rootPath,
        skip_hidden: skipHidden,
        max_files: maxFiles,
        large_threshold_mb: largeThresholdMb,
        stale_days_threshold: staleDaysThreshold,
      }),
    });
  },

  /**
   * Retrieve filtered file inventory
   */
  async getFiles(params?: {
    search?: string;
    category?: string;
    status?: string;
    is_duplicate?: boolean;
    is_stale?: boolean;
    is_temp?: boolean;
    is_large?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<{ total: number; limit: number; offset: number; files: FileItem[] }> {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.category) query.set('category', params.category);
    if (params?.status) query.set('status', params.status);
    if (params?.is_duplicate !== undefined) query.set('is_duplicate', String(params.is_duplicate));
    if (params?.is_stale !== undefined) query.set('is_stale', String(params.is_stale));
    if (params?.is_temp !== undefined) query.set('is_temp', String(params.is_temp));
    if (params?.is_large !== undefined) query.set('is_large', String(params.is_large));
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));

    const qs = query.toString() ? `?${query.toString()}` : '';
    return fetchJson<{ total: number; limit: number; offset: number; files: FileItem[] }>(
      `/api/files${qs}`
    );
  },

  /**
   * Run executive waste analysis with TCET CoE Qwen
   */
  async analyzeWithQwen(enableThinking = false): Promise<QwenAnalyzeResponse> {
    return fetchJson<QwenAnalyzeResponse>('/api/qwen/analyze', {
      method: 'POST',
      body: JSON.stringify({ enable_thinking: enableThinking }),
    });
  },

  /**
   * Generate explanation for a specific recommendation
   */
  async explainRecommendation(
    recommendationId: string,
    enableThinking = false
  ): Promise<QwenExplainResponse> {
    return fetchJson<QwenExplainResponse>('/api/qwen/explain', {
      method: 'POST',
      body: JSON.stringify({
        recommendation_id: recommendationId,
        enable_thinking: enableThinking,
      }),
    });
  },

  /**
   * Ask Grounded Digital Landfill Q&A Assistant
   */
  async askQwen(
    query: string,
    chatHistory: Array<{ role: string; content: string }> = [],
    enableThinking = false
  ): Promise<QwenAskResponse> {
    return fetchJson<QwenAskResponse>('/api/qwen/ask', {
      method: 'POST',
      body: JSON.stringify({
        query,
        chat_history: chatHistory,
        enable_thinking: enableThinking,
      }),
    });
  },

  /**
   * Controlled, user-confirmed file deletion with pre-check verification
   */
  async deleteFile(
    path: string,
    expectedSize: number,
    expectedModifiedAt?: string
  ): Promise<DeleteResponse> {
    return fetchJson<DeleteResponse>('/api/delete', {
      method: 'POST',
      body: JSON.stringify({
        path,
        expected_size: expectedSize,
        expected_modified_at: expectedModifiedAt,
        confirmed: true,
      }),
    });
  },
};
