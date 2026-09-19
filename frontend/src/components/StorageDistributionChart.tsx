import React, { useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { CategoryDistribution, FileCategory } from '../types';

interface StorageDistributionChartProps {
  categories: CategoryDistribution[];
  totalSizeBytes: number;
  totalSizeFormatted: string;
  onSelectCategory?: (category: FileCategory) => void;
}

export const StorageDistributionChart: React.FC<StorageDistributionChartProps> = ({
  categories,
  totalSizeBytes,
  totalSizeFormatted,
  onSelectCategory,
}) => {
  const [hoveredCategory, setHoveredCategory] = useState<string | null>(null);

  const chartData = categories
    .filter((c) => c.bytes > 0)
    .map((c) => ({
      name: c.category,
      value: c.bytes,
      formatted: c.formatted,
      percentage: c.percentage,
      color: c.color,
      count: c.count,
    }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="rounded-lg bg-slate-950/95 border border-slate-700 p-3 shadow-xl text-xs space-y-1">
          <div className="flex items-center gap-2 font-semibold text-white">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: data.color }}
            />
            <span>{data.name}</span>
          </div>
          <div className="text-slate-300 font-mono">
            {data.formatted} ({data.percentage}%)
          </div>
          <div className="text-[11px] text-slate-400">
            {data.count} file{data.count === 1 ? '' : 's'}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="rounded-xl bg-slate-900/70 border border-slate-800/80 p-5 space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-white tracking-wide">
            Storage Distribution
          </h3>
          <p className="text-xs text-slate-400">
            Breakdown across document classes and media footprints
          </p>
        </div>
        <div className="text-xs text-slate-400 font-mono">
          Total Analyzed:{' '}
          <strong className="text-white">{totalSizeFormatted}</strong>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Donut Visualization */}
        <div className="lg:col-span-5 h-60 relative flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Tooltip content={<CustomTooltip />} />
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={68}
                outerRadius={95}
                paddingAngle={3}
                dataKey="value"
                onMouseEnter={(_, index) =>
                  setHoveredCategory(chartData[index]?.name || null)
                }
                onMouseLeave={() => setHoveredCategory(null)}
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.color}
                    stroke="#0b0f19"
                    strokeWidth={2}
                    className="cursor-pointer transition-opacity hover:opacity-80"
                  />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          {/* Donut Center Info */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
            <span className="text-[11px] uppercase tracking-wider text-slate-500 font-mono">
              {hoveredCategory || 'Active Storage'}
            </span>
            <span className="text-xl font-bold font-mono text-white tracking-tight">
              {hoveredCategory
                ? categories.find((c) => c.category === hoveredCategory)?.formatted
                : totalSizeFormatted}
            </span>
            <span className="text-[10px] text-slate-400">
              {hoveredCategory
                ? `${categories.find((c) => c.category === hoveredCategory)?.percentage}% of total`
                : `${categories.reduce((a, b) => a + b.count, 0)} files`}
            </span>
          </div>
        </div>

        {/* Categories Bar & Grid Breakdown */}
        <div className="lg:col-span-7 space-y-3">
          <div className="space-y-2">
            {categories.map((cat) => (
              <div
                key={cat.category}
                onClick={() => onSelectCategory && onSelectCategory(cat.category)}
                onMouseEnter={() => setHoveredCategory(cat.category)}
                onMouseLeave={() => setHoveredCategory(null)}
                className={`p-2 rounded-lg transition-colors cursor-pointer ${
                  hoveredCategory === cat.category
                    ? 'bg-slate-800/80'
                    : 'hover:bg-slate-800/40'
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: cat.color }}
                    />
                    <span className="font-semibold text-slate-200">
                      {cat.category}
                    </span>
                    <span className="text-slate-500 text-[11px]">
                      ({cat.count} files)
                    </span>
                  </div>
                  <div className="flex items-center gap-3 font-mono text-xs">
                    <span className="text-slate-400">{cat.formatted}</span>
                    <span className="font-bold text-white w-12 text-right">
                      {cat.percentage}%
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.max(cat.percentage, cat.count > 0 ? 2 : 0)}%`,
                      backgroundColor: cat.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
