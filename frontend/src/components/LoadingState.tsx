import React from 'react';
import { Loader2, Bot, Sparkles } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  subMessage?: string;
  isAI?: boolean;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Processing storage intelligence...',
  subMessage = 'TCET CoE pipeline active',
  isAI = false,
}) => {
  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-12 text-center flex flex-col items-center justify-center space-y-4">
      <div className="relative">
        {isAI ? (
          <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 relative">
            <Bot className="w-8 h-8 animate-bounce" />
            <Sparkles className="w-4 h-4 text-cyan-400 absolute -top-1 -right-1 animate-pulse" />
          </div>
        ) : (
          <div className="p-4 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
        )}
      </div>

      <div className="space-y-1">
        <h4 className="text-sm font-semibold text-white tracking-wide">
          {message}
        </h4>
        {subMessage && (
          <p className="text-xs text-slate-400 font-mono">
            {subMessage}
          </p>
        )}
      </div>
    </div>
  );
};
