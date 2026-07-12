import { Chart as ChartJS, Tooltip, CategoryScale, LinearScale } from "chart.js";
import { MatrixController, MatrixElement } from "chartjs-chart-matrix";
import { Chart } from "react-chartjs-2";
import type { TooltipItem } from "chart.js";

ChartJS.register(Tooltip, CategoryScale, LinearScale, MatrixController, MatrixElement);

interface MatrixCell {
  x: string;
  y: string;
  count: number;
  slugs: string[];
}

interface Dimension {
  id: string;
  label: string;
  x_labels: string[];
  y_labels: string[];
  matrix: MatrixCell[];
}

interface HeatmapChartProps {
  dimension: Dimension;
}

export default function HeatmapChart({ dimension }: HeatmapChartProps) {
  const maxCount = Math.max(1, ...dimension.matrix.map((c) => c.count));

  const data = {
    datasets: [
      {
        label: "报告数",
        data: dimension.matrix.map((cell) => ({
          x: dimension.x_labels.indexOf(cell.x),
          y: dimension.y_labels.indexOf(cell.y),
          v: cell.count,
          slugs: cell.slugs,
        })),
        backgroundColor(ctx: any) {
          const v = (ctx.raw?.v || 0) as number;
          if (v === 0) return "rgba(30, 39, 51, 0.5)"; // 空白 = 灰色
          const alpha = 0.2 + (v / maxCount) * 0.8;
          return `rgba(34, 211, 238, ${alpha})`;
        },
        borderColor: "#1E2733",
        borderWidth: 1,
        width: ({ chart }: any) => {
          const area = chart.chartArea || { width: 600 };
          const xCount = dimension.x_labels.length || 1;
          return (area.width / xCount) * 0.9;
        },
        height: ({ chart }: any) => {
          const area = chart.chartArea || { height: 400 };
          const yCount = dimension.y_labels.length || 1;
          return (area.height / yCount) * 0.9;
        },
      },
    ],
  };

  const options: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      tooltip: {
        callbacks: {
          title: (items: TooltipItem<"matrix">[]) => {
            const item = items[0];
            const raw = item.raw as any;
            return `${dimension.y_labels[raw.y]} × ${dimension.x_labels[raw.x]}`;
          },
          label: (item: TooltipItem<"matrix">) => {
            const raw = item.raw as any;
            if (raw.v === 0) return "研究空白";
            return `${raw.v} 篇报告`;
          },
        },
      },
      legend: { display: false },
    },
    scales: {
      x: {
        type: "category" as const,
        labels: dimension.x_labels,
        offset: true,
        ticks: { color: "#6B7280", font: { size: 10 } },
        grid: { display: false },
      },
      y: {
        type: "category" as const,
        labels: dimension.y_labels,
        offset: true,
        ticks: { color: "#6B7280", font: { size: 10 } },
        grid: { display: false },
      },
    },
  };

  return (
    <div style={{ height: `${Math.max(200, dimension.y_labels.length * 50 + 40)}px` }}>
      <Chart type="matrix" data={data} options={options} />
    </div>
  );
}