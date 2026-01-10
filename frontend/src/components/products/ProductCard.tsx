import { Link } from "react-router-dom"
import { ExternalLink, RefreshCw, Trash2, Pause, Play } from "lucide-react"
import { cn, formatPrice, formatRelativeTime, calculatePriceChange } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { ProductListItem, ProductStatus } from "@/types/api"

interface ProductCardProps {
  product: ProductListItem
  onRefresh?: (id: number) => void
  onDelete?: (id: number) => void
  onToggleStatus?: (id: number, status: ProductStatus) => void
  isRefreshing?: boolean
}

const statusBadgeMap: Record<ProductStatus, { variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning"; label: string }> = {
  active: { variant: "success", label: "Active" },
  paused: { variant: "secondary", label: "Paused" },
  error: { variant: "destructive", label: "Error" },
  needs_attention: { variant: "warning", label: "Needs Attention" },
  price_unavailable: { variant: "warning", label: "Price N/A" },
  archived: { variant: "outline", label: "Archived" },
}

export function ProductCard({
  product,
  onRefresh,
  onDelete,
  onToggleStatus,
  isRefreshing = false,
}: ProductCardProps) {
  const priceChange = calculatePriceChange(
    product.original_price,
    product.current_price
  )
  const statusBadge = statusBadgeMap[product.status]

  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow">
      <CardContent className="p-0">
        <div className="flex gap-4 p-4">
          {/* Product Image */}
          <Link to={`/products/${product.id}`} className="shrink-0">
            {product.image_url ? (
              <img
                src={product.image_url}
                alt={product.name}
                className="h-20 w-20 object-contain rounded-md bg-muted"
              />
            ) : (
              <div className="h-20 w-20 rounded-md bg-muted flex items-center justify-center text-muted-foreground">
                No image
              </div>
            )}
          </Link>

          {/* Product Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <Link
                to={`/products/${product.id}`}
                className="font-medium hover:underline line-clamp-2"
              >
                {product.name}
              </Link>
              <div className="flex items-center gap-1 shrink-0">
                {/* External Link */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <a
                      href={product.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </a>
                  </TooltipTrigger>
                  <TooltipContent>Open product page</TooltipContent>
                </Tooltip>

                {/* Refresh */}
                {onRefresh && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => onRefresh(product.id)}
                        disabled={isRefreshing}
                      >
                        <RefreshCw
                          className={cn(
                            "h-4 w-4",
                            isRefreshing && "animate-spin"
                          )}
                        />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Refresh price</TooltipContent>
                  </Tooltip>
                )}

                {/* Toggle Status */}
                {onToggleStatus && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() =>
                          onToggleStatus(
                            product.id,
                            product.status === "paused" ? "active" : "paused"
                          )
                        }
                      >
                        {product.status === "paused" ? (
                          <Play className="h-4 w-4" />
                        ) : (
                          <Pause className="h-4 w-4" />
                        )}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      {product.status === "paused" ? "Resume tracking" : "Pause tracking"}
                    </TooltipContent>
                  </Tooltip>
                )}

                {/* Delete */}
                {onDelete && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:text-destructive"
                        onClick={() => onDelete(product.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Delete product</TooltipContent>
                  </Tooltip>
                )}
              </div>
            </div>

            {/* Store and Brand */}
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <span>{product.store_domain}</span>
              {product.brand && (
                <>
                  <span>·</span>
                  <span>{product.brand}</span>
                </>
              )}
            </div>

            {/* Price and Status */}
            <div className="flex items-center justify-between mt-3">
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold">
                  {formatPrice(product.current_price)}
                </span>
                {priceChange && priceChange.isDecrease && (
                  <Badge variant="success">
                    -{priceChange.value.toFixed(0)}%
                  </Badge>
                )}
                {product.original_price &&
                  product.original_price !== product.current_price && (
                    <span className="text-sm text-muted-foreground line-through">
                      {formatPrice(product.original_price)}
                    </span>
                  )}
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  variant={product.in_stock ? "success" : "destructive"}
                >
                  {product.in_stock ? "In Stock" : "Out of Stock"}
                </Badge>
                <Badge variant={statusBadge.variant}>{statusBadge.label}</Badge>
              </div>
            </div>

            {/* Last Checked */}
            {product.last_checked_at && (
              <p className="text-xs text-muted-foreground mt-2">
                Last checked {formatRelativeTime(product.last_checked_at)}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
