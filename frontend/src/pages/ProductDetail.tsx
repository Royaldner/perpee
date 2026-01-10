import { useState } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import {
  ArrowLeft,
  ExternalLink,
  RefreshCw,
  Trash2,
  Bell,
} from "lucide-react"
import { formatPrice, formatRelativeTime, formatDate, calculatePriceChange } from "@/lib/utils"
import { PriceChart } from "@/components/products/PriceChart"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import {
  useProduct,
  useProductHistory,
  useRefreshProduct,
  useDeleteProduct,
} from "@/hooks/useProducts"
import { useAlerts } from "@/hooks/useAlerts"

export function ProductDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const productId = parseInt(id || "0", 10)

  const [isRefreshing, setIsRefreshing] = useState(false)

  const { data: product, isLoading: productLoading } = useProduct(productId)
  const { data: history, isLoading: historyLoading } = useProductHistory(
    productId,
    30
  )
  const { data: alertsData } = useAlerts({ product_id: productId })
  const refreshProduct = useRefreshProduct()
  const deleteProduct = useDeleteProduct()

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await refreshProduct.mutateAsync(productId)
    } finally {
      setIsRefreshing(false)
    }
  }

  const handleDelete = async () => {
    if (window.confirm("Are you sure you want to delete this product?")) {
      await deleteProduct.mutateAsync(productId)
      navigate("/products")
    }
  }

  if (productLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-64" />
            <Skeleton className="h-4 w-48" />
          </div>
        </div>
        <Skeleton className="h-[300px] w-full" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[200px]" />
        </div>
      </div>
    )
  }

  if (!product) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Product not found.</p>
        <Link to="/products">
          <Button variant="link" className="mt-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Products
          </Button>
        </Link>
      </div>
    )
  }

  const priceChange = calculatePriceChange(
    product.original_price,
    product.current_price
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link to="/products">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight line-clamp-2">
                {product.name}
              </h1>
              <p className="text-muted-foreground mt-1">
                {product.store_domain}
                {product.brand && ` · ${product.brand}`}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <a
                href={product.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="outline" size="sm">
                  <ExternalLink className="mr-2 h-4 w-4" />
                  View on Store
                </Button>
              </a>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={isRefreshing}
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`}
                />
                Refresh
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={handleDelete}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Price Overview */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Current Price</p>
              <div className="flex items-center gap-3">
                <span className="text-3xl font-bold">
                  {formatPrice(product.current_price)}
                </span>
                {priceChange && priceChange.isDecrease && (
                  <Badge variant="success" className="text-sm">
                    -{priceChange.value.toFixed(0)}% off
                  </Badge>
                )}
              </div>
              {product.original_price &&
                product.original_price !== product.current_price && (
                  <p className="text-sm text-muted-foreground mt-1">
                    <span className="line-through">
                      {formatPrice(product.original_price)}
                    </span>{" "}
                    MSRP
                  </p>
                )}
            </div>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <Badge variant={product.in_stock ? "success" : "destructive"}>
                  {product.in_stock ? "In Stock" : "Out of Stock"}
                </Badge>
              </div>
              <Separator orientation="vertical" className="h-8" />
              <div className="text-center">
                <p className="text-xs text-muted-foreground">Last Checked</p>
                <p className="text-sm font-medium">
                  {formatRelativeTime(product.last_checked_at)}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Price History Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Price History (Last 30 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <Skeleton className="h-[300px]" />
          ) : (
            <PriceChart
              history={history?.history ?? []}
              currentPrice={product.current_price}
            />
          )}
        </CardContent>
      </Card>

      {/* Product Details & Alerts */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Product Details */}
        <Card>
          <CardHeader>
            <CardTitle>Product Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Status</p>
                <Badge
                  variant={
                    product.status === "active"
                      ? "success"
                      : product.status === "error"
                        ? "destructive"
                        : "secondary"
                  }
                >
                  {product.status}
                </Badge>
              </div>
              <div>
                <p className="text-muted-foreground">Currency</p>
                <p className="font-medium">{product.currency}</p>
              </div>
              {product.upc && (
                <div>
                  <p className="text-muted-foreground">UPC</p>
                  <p className="font-medium">{product.upc}</p>
                </div>
              )}
              <div>
                <p className="text-muted-foreground">Added</p>
                <p className="font-medium">{formatDate(product.created_at)}</p>
              </div>
            </div>
            {product.image_url && (
              <div className="pt-4 border-t">
                <img
                  src={product.image_url}
                  alt={product.name}
                  className="max-w-[200px] max-h-[200px] object-contain mx-auto rounded-lg"
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Alerts */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Alerts
            </CardTitle>
            <Link to={`/alerts?product_id=${productId}`}>
              <Button variant="outline" size="sm">
                Manage Alerts
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {alertsData?.items.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No alerts set up for this product.
              </p>
            ) : (
              <div className="space-y-3">
                {alertsData?.items.map((alert) => (
                  <div
                    key={alert.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted"
                  >
                    <div>
                      <p className="text-sm font-medium capitalize">
                        {alert.alert_type.replace("_", " ")}
                      </p>
                      {alert.target_value && (
                        <p className="text-xs text-muted-foreground">
                          Target: {formatPrice(alert.target_value)}
                        </p>
                      )}
                    </div>
                    <Badge variant={alert.is_active ? "success" : "secondary"}>
                      {alert.is_active ? "Active" : "Paused"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
