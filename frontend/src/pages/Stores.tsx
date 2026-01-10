import { useQuery } from "@tanstack/react-query"
import { Store, CheckCircle, XCircle, AlertCircle } from "lucide-react"
import { formatRelativeTime } from "@/lib/utils"
import { storesApi } from "@/lib/api"
import { PageHeader } from "@/components/layout/PageHeader"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export function Stores() {
  const { data: stores, isLoading: storesLoading } = useQuery({
    queryKey: ["stores"],
    queryFn: () => storesApi.list(),
  })

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["stores-health"],
    queryFn: () => storesApi.getHealth(),
  })

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stores-stats"],
    queryFn: () => storesApi.getStats(),
  })

  const isLoading = storesLoading || healthLoading || statsLoading

  // Create a map of store health by domain
  const healthMap = new Map(
    health?.map((h) => [h.domain, h]) ?? []
  )

  const getHealthIcon = (status: string | undefined) => {
    switch (status) {
      case "healthy":
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case "degraded":
        return <AlertCircle className="h-4 w-4 text-yellow-500" />
      case "unhealthy":
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return null
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Stores"
        description="Supported Canadian retailers"
      />

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Stores</CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{stats?.total ?? 0}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Active</CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{stats?.active ?? 0}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Whitelisted</CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{stats?.whitelisted ?? 0}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Avg Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">
                {stats?.avg_success_rate?.toFixed(0) ?? 0}%
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Info Card */}
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">
            Perpee supports 16+ Canadian retailers including Amazon, Walmart, Best Buy,
            and more. <strong>Whitelisted</strong> stores have pre-configured selectors
            for fast, free extraction. Other stores use LLM-based extraction which may
            use tokens.
          </p>
        </CardContent>
      </Card>

      {/* Stores Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <Skeleton className="h-12 w-12 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-4 w-48" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : stores?.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Store className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p>No stores configured.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {stores?.map((store) => {
            const storeHealth = healthMap.get(store.domain)

            return (
              <Card key={store.domain}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted text-muted-foreground font-semibold text-lg">
                      {store.name.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium truncate">{store.name}</h3>
                        {storeHealth && (
                          <Tooltip>
                            <TooltipTrigger>
                              {getHealthIcon(storeHealth.health_status)}
                            </TooltipTrigger>
                            <TooltipContent>
                              {storeHealth.health_status === "healthy" && "Store is healthy"}
                              {storeHealth.health_status === "degraded" && "Store is experiencing issues"}
                              {storeHealth.health_status === "unhealthy" && "Store is currently unavailable"}
                            </TooltipContent>
                          </Tooltip>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground truncate">
                        {store.domain}
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <Badge
                          variant={store.is_whitelisted ? "success" : "outline"}
                        >
                          {store.is_whitelisted ? "Whitelisted" : "LLM"}
                        </Badge>
                        <Badge
                          variant={store.is_active ? "secondary" : "destructive"}
                        >
                          {store.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </div>
                      {storeHealth && (
                        <div className="mt-2 text-xs text-muted-foreground">
                          <span>
                            {storeHealth.product_count} products tracked
                          </span>
                          {storeHealth.success_rate != null && (
                            <span className="ml-2">
                              · {storeHealth.success_rate.toFixed(0)}% success
                            </span>
                          )}
                          {storeHealth.last_success_at && (
                            <span className="ml-2">
                              · Last: {formatRelativeTime(storeHealth.last_success_at)}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
