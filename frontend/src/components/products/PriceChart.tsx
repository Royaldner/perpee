import { useMemo } from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import { format } from "date-fns"
import { formatPrice } from "@/lib/utils"
import type { PriceHistoryItem } from "@/types/api"

interface PriceChartProps {
  history: PriceHistoryItem[]
  currentPrice?: number | null
  className?: string
}

export function PriceChart({ history, currentPrice, className }: PriceChartProps) {
  const chartData = useMemo(() => {
    return history
      .sort((a, b) => new Date(a.scraped_at).getTime() - new Date(b.scraped_at).getTime())
      .map((item) => ({
        date: format(new Date(item.scraped_at), "MMM d"),
        fullDate: format(new Date(item.scraped_at), "MMM d, yyyy h:mm a"),
        price: item.price,
        originalPrice: item.original_price,
        inStock: item.in_stock,
      }))
  }, [history])

  const { minPrice, maxPrice, avgPrice } = useMemo(() => {
    if (chartData.length === 0) {
      return { minPrice: 0, maxPrice: 100, avgPrice: 50 }
    }
    const prices = chartData.map((d) => d.price)
    const min = Math.min(...prices)
    const max = Math.max(...prices)
    const avg = prices.reduce((a, b) => a + b, 0) / prices.length
    return {
      minPrice: min * 0.95,
      maxPrice: max * 1.05,
      avgPrice: avg,
    }
  }, [chartData])

  if (history.length === 0) {
    return (
      <div className={className}>
        <div className="h-64 flex items-center justify-center text-muted-foreground">
          No price history available yet
        </div>
      </div>
    )
  }

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="date"
            className="text-xs fill-muted-foreground"
            tick={{ fontSize: 12 }}
          />
          <YAxis
            domain={[minPrice, maxPrice]}
            tickFormatter={(value) => formatPrice(value)}
            className="text-xs fill-muted-foreground"
            tick={{ fontSize: 12 }}
            width={80}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload
                return (
                  <div className="bg-popover border rounded-lg p-3 shadow-lg">
                    <p className="text-sm font-medium">{data.fullDate}</p>
                    <p className="text-lg font-bold text-primary">
                      {formatPrice(data.price)}
                    </p>
                    {data.originalPrice && data.originalPrice !== data.price && (
                      <p className="text-sm text-muted-foreground">
                        MSRP: {formatPrice(data.originalPrice)}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      {data.inStock ? "In Stock" : "Out of Stock"}
                    </p>
                  </div>
                )
              }
              return null
            }}
          />
          {/* Average price reference line */}
          <ReferenceLine
            y={avgPrice}
            stroke="hsl(var(--muted-foreground))"
            strokeDasharray="5 5"
            label={{
              value: `Avg: ${formatPrice(avgPrice)}`,
              position: "right",
              className: "text-xs fill-muted-foreground",
            }}
          />
          {/* Current price reference line */}
          {currentPrice && (
            <ReferenceLine
              y={currentPrice}
              stroke="hsl(var(--primary))"
              strokeDasharray="3 3"
            />
          )}
          <Line
            type="monotone"
            dataKey="price"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={{ r: 4, fill: "hsl(var(--primary))" }}
            activeDot={{ r: 6, fill: "hsl(var(--primary))" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
