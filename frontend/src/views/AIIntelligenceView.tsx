import React, { useEffect, useState } from 'react';
import {
  Bot,
  Sparkles,
  ShieldCheck,
  Zap,
  TrendingDown,
  AlertCircle,
  AlertTriangle,
  RefreshCw,
  HelpCircle,
  CheckCircle2,
  Terminal,
  Layers,
  Send,
  MessageSquare,
} from 'lucide-react';
import { RecommendationItem, ScanData } from '../types';
import { apiClient } from '../api/client';
import { LoadingState } from '../components/LoadingState';

interface AIIntelligenceViewProps {
  scanData: ScanData;
  activeRecommendation?: RecommendationItem | null;
  onClearActiveRecommendation?: () => void;
}

export const AIIntelligenceView: React.FC<AIIntelligenceViewProps> = ({
  scanData,
  activeRecommendation,
}) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisText, setAnalysisText] = useState<string | null>(null);
  const [selectedRecId, setSelectedRecId] = useState<string>(
    activeRecommendation ? activeRecommendation.id : scanData.recommendations[0]?.id || ''
  );
  const [isExplainingRec, setIsExplainingRec] = useState(false);
  const [explanationOutput, setExplanationOutput] = useState<string | null>(
    activeRecommendation ? activeRecommendation.qwenExplanation : null
  );
  const [enableThinking, setEnableThinking] = useState(false);
  const [gatewayStatus, setGatewayStatus] = useState<'Connected' | 'Not Configured' | 'Offline'>('Connected');
  const [gatewayDetail, setGatewayDetail] = useState<string>('TCET CoE Qwen Gateway active');

  // Interactive Grounded Q&A Assistant state
  const [askQuery, setAskQuery] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [chatHistory, setChatHistory] = useState<Array<{ role: string; content: string }>>([]);

  useEffect(() => {
    async function checkHealth() {
      try {
        const health = await apiClient.getHealth();
        setGatewayStatus(health.qwen_gateway.status);
        setGatewayDetail(health.qwen_gateway.detail);
      } catch {
        setGatewayStatus('Offline');
        setGatewayDetail('Unable to reach Digital Landfill backend');
      }
    }
    checkHealth();
  }, []);

  const handleAnalyze = async () => {
    if (scanData.totalFiles === 0) {
      alert('Please scan a folder first to analyze digital waste.');
      return;
    }

    setIsAnalyzing(true);
    setAnalysisText(null);

    try {
      const response = await apiClient.analyzeWithQwen(enableThinking);
      setAnalysisText(response.raw_text);
    } catch (err: any) {
      setAnalysisText(`🔴 Error during analysis: ${err.message || err}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleExplainRecommendation = async () => {
    const targetRec = scanData.recommendations.find((r) => r.id === selectedRecId);
    if (!targetRec) return;

    setIsExplainingRec(true);
    setExplanationOutput(null);

    try {
      const response = await apiClient.explainRecommendation(selectedRecId, enableThinking);
      setExplanationOutput(response.explanation);
    } catch (err: any) {
      setExplanationOutput(`🔴 Error during explanation: ${err.message || err}`);
    } finally {
      setIsExplainingRec(false);
    }
  };

  const handleAskSubmit = async (queryText: string) => {
    const q = queryText.trim();
    if (!q) return;

    if (scanData.totalFiles === 0) {
      alert('Please scan a folder first to ask questions about your data.');
      return;
    }

    const newHistory = [...chatHistory, { role: 'user', content: q }];
    setChatHistory(newHistory);
    setAskQuery('');
    setIsAsking(true);

    try {
      const response = await apiClient.askQwen(q, chatHistory, enableThinking);
      setChatHistory([...newHistory, { role: 'assistant', content: response.answer }]);
    } catch (err: any) {
      setChatHistory([
        ...newHistory,
        { role: 'assistant', content: `🔴 Error: ${err.message || err}` },
      ]);
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header with Qwen info */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Bot className="w-7 h-7 text-indigo-400" />
              <span>TCET CoE Qwen AI Intelligence</span>
            </h1>
            <span
              className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${
                gatewayStatus === 'Connected'
                  ? 'bg-emerald-950/50 text-emerald-300 border-emerald-800/60'
                  : gatewayStatus === 'Not Configured'
                  ? 'bg-amber-950/50 text-amber-300 border-amber-800/60'
                  : 'bg-rose-950/50 text-rose-300 border-rose-800/60'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  gatewayStatus === 'Connected' ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
                }`}
              />
              <span>{gatewayStatus}</span>
            </span>
          </div>
          <p className="text-sm text-slate-400">
            Natural-language reasoning over filesystem topology, SHA-256 byte redundancy, and storage recovery tiers.
          </p>
        </div>

        {/* Model and Gateway badges */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
            <span className="text-slate-500">Model: </span>
            <span className="text-indigo-300 font-semibold">Qwen3.6-35B-A3B</span>
          </div>

          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
            <span className="text-slate-500">Gateway: </span>
            <span className="text-cyan-300 font-semibold">https://ai.tcetcercd.in/v1</span>
          </div>

          <label className="flex items-center gap-2 text-xs text-slate-300 bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-800 cursor-pointer">
            <input
              type="checkbox"
              checked={enableThinking}
              onChange={(e) => setEnableThinking(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-indigo-500 focus:ring-0"
            />
            <span>Deep Reasoning</span>
          </label>
        </div>
      </div>

      {gatewayStatus !== 'Connected' && (
        <div className="rounded-xl bg-amber-950/30 border border-amber-800/50 p-5 flex items-start gap-4 text-xs text-amber-200">
          <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-bold text-white text-sm">
              Gateway Status: {gatewayStatus}
            </div>
            <p className="text-slate-300 leading-relaxed">
              {gatewayDetail}. Local Digital Landfill intelligence (Phase 1–4) remains fully operational.
            </p>
          </div>
        </div>
      )}

      {/* Large AI Analysis Panel */}
      <div className="rounded-2xl bg-gradient-to-b from-slate-900 via-slate-900/80 to-[#0c111e] border border-indigo-900/40 p-6 md:p-8 space-y-6 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10 border-b border-slate-800/80 pb-5">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-indigo-400 font-semibold">
              <Sparkles className="w-3.5 h-3.5" />
              Automated Reasoning Engine
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight mt-1">
              Storage Waste & Recovery Synthesis
            </h2>
          </div>

          <button
            type="button"
            disabled={isAnalyzing}
            onClick={handleAnalyze}
            className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-xs font-bold tracking-wide shadow-lg shadow-indigo-600/30 transition-all cursor-pointer border border-indigo-400/30 shrink-0"
          >
            {isAnalyzing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Qwen Reasoning...</span>
              </>
            ) : (
              <>
                <span>🚀 Analyze Current Storage</span>
              </>
            )}
          </button>
        </div>

        {isAnalyzing ? (
          <div className="py-12">
            <LoadingState
              message="Qwen is analyzing your storage intelligence..."
              subMessage="Evaluating cryptographic SHA-256 duplicates, decay timelines, and safety constraints"
              isAI={true}
            />
          </div>
        ) : analysisText ? (
          <div className="space-y-4 p-5 rounded-xl bg-slate-950/90 border border-slate-800 text-slate-200 text-sm leading-relaxed whitespace-pre-wrap font-sans">
            {analysisText}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-400 text-xs space-y-2">
            <Bot className="w-10 h-10 text-indigo-400 mx-auto opacity-70" />
            <div className="text-sm font-semibold text-white">No Analysis Generated Yet</div>
            <p>Click "Analyze Current Storage" above to generate a full executive synthesis from TCET CoE Qwen.</p>
          </div>
        )}
      </div>

      {/* Interactive Grounded Q&A Section */}
      <div className="rounded-xl bg-slate-900/70 border border-slate-800/80 p-5 space-y-4">
        <div className="flex items-center gap-2.5 border-b border-slate-800/80 pb-3">
          <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <MessageSquare className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Ask Digital Landfill — Grounded Q&A Assistant
            </h3>
            <p className="text-xs text-slate-400">
              Ask questions about your scanned files, duplicate redundancies, or cleanup suggestions.
            </p>
          </div>
        </div>

        {/* Quick prompt chips */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] text-slate-500 font-mono">Suggestions:</span>
          {[
            'What are my largest files?',
            'Where are my top duplicates?',
            'Summarize high priority recommendations',
            'Can I safely clean temp files?',
          ].map((prompt, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleAskSubmit(prompt)}
              className="text-xs px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition-colors cursor-pointer"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Chat message history */}
        {chatHistory.length > 0 && (
          <div className="space-y-3 max-h-80 overflow-y-auto p-3 rounded-xl bg-slate-950/80 border border-slate-800/60">
            {chatHistory.map((msg, i) => (
              <div
                key={i}
                className={`p-3.5 rounded-xl text-xs leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-cyan-950/40 border border-cyan-800/50 text-cyan-100 ml-8'
                    : 'bg-slate-900 border border-slate-800 text-slate-200 mr-8 whitespace-pre-wrap'
                }`}
              >
                <div className="font-mono text-[10px] text-slate-500 mb-1 uppercase font-bold">
                  {msg.role === 'user' ? 'You' : 'TCET CoE Qwen'}
                </div>
                {msg.content}
              </div>
            ))}
          </div>
        )}

        {/* Chat input */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={askQuery}
            onChange={(e) => setAskQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleAskSubmit(askQuery);
            }}
            placeholder="Ask anything about your active scan context..."
            className="flex-1 px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
          <button
            type="button"
            disabled={isAsking || !askQuery.trim()}
            onClick={() => handleAskSubmit(askQuery)}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-semibold cursor-pointer"
          >
            {isAsking ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
            <span>Ask</span>
          </button>
        </div>
      </div>

      {/* Deep-Dive Action: Explain Selected Recommendation */}
      <div className="rounded-xl bg-slate-900/70 border border-slate-800/80 p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <HelpCircle className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide">
                Explain Selected Recommendation
              </h3>
              <p className="text-xs text-slate-400">
                Request Qwen to provide deterministic safety rationale and byte evidence
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <select
            value={selectedRecId}
            onChange={(e) => {
              setSelectedRecId(e.target.value);
              setExplanationOutput(null);
            }}
            className="w-full sm:w-80 px-3 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
          >
            {scanData.recommendations.map((rec) => (
              <option key={rec.id} value={rec.id}>
                [{rec.priority}] {rec.title}
              </option>
            ))}
          </select>

          <button
            type="button"
            disabled={isExplainingRec}
            onClick={handleExplainRecommendation}
            className="w-full sm:w-auto px-4 py-2.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/40 text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50"
          >
            {isExplainingRec ? 'Generating Rationale...' : 'Explain with Qwen'}
          </button>
        </div>

        {explanationOutput && (
          <div className="rounded-xl bg-slate-950 border border-indigo-900/50 p-4 space-y-2 text-xs font-mono animate-in fade-in">
            <div className="flex items-center justify-between text-indigo-400 font-semibold border-b border-slate-800 pb-2">
              <span className="flex items-center gap-1.5">
                <Bot className="w-3.5 h-3.5" />
                Qwen3.6-35B Inference
              </span>
            </div>
            <pre className="text-slate-300 whitespace-pre-wrap leading-relaxed">
              {explanationOutput}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
