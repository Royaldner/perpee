import { Link } from "react-router-dom"
import {
  Package,
  Bell,
  TrendingDown,
  AlertTriangle,
  ArrowRight,
} from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { healthApi } from "@/lib/api"
import { formatPrice, formatRelativeTime } from "@/lib/utils"
import { PageHeader } from "@/components/layout/PageHeader"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"

export function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => healthApi.getStats(),
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Overview of your price tracking activity"
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Products</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {stats?.products.total ?? 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  {stats?.products.active ?? 0} active,{" "}
                  {stats?.products.paused ?? 0} paused
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Alerts</CardTitle>
            <Bell className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {stats?.alerts.active ?? 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  {stats?.alerts.triggered_today ?? 0} triggered today
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Price Drops</CardTitle>
            <TrendingDown className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {stats?.recent_price_drops.length ?? 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  In the last 7 days
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Needs Attention</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {stats?.products.needs_attention ?? 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  Products with issues
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Price Drops */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Price Drops</CardTitle>
          <CardDescription>
            Products that recently dropped in price
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-12 w-12 rounded" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                  <Skeleton className="h-6 w-20" />
                </div>
              ))}
            </div>
          ) : stats?.recent_price_drops.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              No recent price drops. Keep tracking!
            </p>
          ) : (
            <div className="space-y-4">
              {stats?.recent_price_drops.slice(0, 5).map((drop) => (
                <Link
                  key={drop.product_id}
                  to={`/products/${drop.product_id}`}
                  className="flex items-center gap-4 p-2 -mx-2 rounded-lg hover:bg-muted transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{drop.product_name}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatPrice(drop.old_price)} {"->"} {formatPrice(drop.new_price)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="success">
                      -{drop.percent_change.toFixed(0)}%
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatRelativeTime(drop.changed_at)}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
          {(stats?.recent_price_drops.length ?? 0) > 5 && (
            <div className="mt-4 pt-4 border-t">
              <Link to="/products?sort=price_drop">
                <Button variant="ghost" className="w-full">
                  View All Price Drops
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Products by Store */}
      <Card>
        <CardHeader>
          <CardTitle>Products by Store</CardTitle>
          <CardDescription>
            Distribution of tracked products across stores
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="flex items-center gap-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 flex-1" />
                  <Skeleton className="h-4 w-8" />
                </div>
              ))}
            </div>
          ) : Object.keys(stats?.products.by_store ?? {}).length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              No products tracked yet. Start by adding a product URL!
            </p>
          ) : (
            <div className="space-y-3">
              {Object.entries(stats?.products.by_store ?? {})
                .sort(([, a], [, b]) => b - a)
                .slice(0, 8)
                .map(([store, count]) => {
                  const maxCount = Math.max(
                    ...Object.values(stats?.products.by_store ?? {})
                  )
                  const percentage = (count / maxCount) * 100

                  return (
                    <div key={store} className="flex items-center gap-3">
                      <span className="text-sm w-32 truncate">{store}</span>
                      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <span className="text-sm text-muted-foreground w-8 text-right">
                        {count}
                      </span>
                    </div>
                  )
                })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
