import { useState } from "react"
import { useSearchParams, Link } from "react-router-dom"
import { Bell, Plus, Trash2, Pause, Play } from "lucide-react"
import { formatPrice, formatDate } from "@/lib/utils"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertForm } from "@/components/alerts/AlertForm"
import {
  useAlerts,
  useDeleteAlert,
  useUpdateAlert,
} from "@/hooks/useAlerts"
import type { AlertType } from "@/types/api"

const alertTypeLabels: Record<AlertType, string> = {
  target_price: "Target Price",
  percent_drop: "Percent Drop",
  any_change: "Any Change",
  back_in_stock: "Back in Stock",
}

export function Alerts() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [showForm, setShowForm] = useState(false)

  const isActive = searchParams.get("is_active")
  const productId = searchParams.get("product_id")
    ? parseInt(searchParams.get("product_id")!, 10)
    : undefined

  const { data: alertsData, isLoading, refetch } = useAlerts({
    is_active: isActive === "true" ? true : isActive === "false" ? false : undefined,
    product_id: productId,
  })

  const deleteAlert = useDeleteAlert()
  const updateAlert = useUpdateAlert()

  const handleDelete = async (id: number) => {
    if (window.confirm("Are you sure you want to delete this alert?")) {
      await deleteAlert.mutateAsync(id)
    }
  }

  const handleToggle = async (id: number, isActive: boolean) => {
    await updateAlert.mutateAsync({ id, data: { is_active: !isActive } })
  }

  const handleActiveFilter = (value: string) => {
    const newParams = new URLSearchParams(searchParams)
    if (value === "all") {
      newParams.delete("is_active")
    } else {
      newParams.set("is_active", value)
    }
    setSearchParams(newParams)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Alerts"
        description="Manage your price alerts"
        actions={
          <Button onClick={() => setShowForm(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Alert
          </Button>
        }
      />

      {/* Filters */}
      <div className="flex gap-4">
        <Select
          value={isActive ?? "all"}
          onValueChange={handleActiveFilter}
        >
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Alerts</SelectItem>
            <SelectItem value="true">Active</SelectItem>
            <SelectItem value="false">Paused</SelectItem>
          </SelectContent>
        </Select>

        {productId && (
          <Badge
            variant="secondary"
            className="cursor-pointer"
            onClick={() => {
              const newParams = new URLSearchParams(searchParams)
              newParams.delete("product_id")
              setSearchParams(newParams)
            }}
          >
            Filtered by Product #{productId} ×
          </Badge>
        )}
      </div>

      {/* Alert Form Dialog */}
      <AlertForm
        open={showForm}
        onOpenChange={setShowForm}
        onSuccess={() => {
          setShowForm(false)
          refetch()
        }}
      />

      {/* Alerts List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-5 w-48" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                  <Skeleton className="h-8 w-20" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : alertsData?.items.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Bell className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p>No alerts found.</p>
          <p className="text-sm mt-1">Create an alert to get notified of price changes.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {alertsData?.items.map((alert) => (
            <Card key={alert.id}>
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Bell className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/products/${alert.product_id}`}
                        className="font-medium hover:underline truncate"
                      >
                        {alert.product_name}
                      </Link>
                      <Badge variant="outline">
                        {alertTypeLabels[alert.alert_type]}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {alert.store_domain}
                      {alert.target_value && (
                        <> · Target: {formatPrice(alert.target_value)}</>
                      )}
                      {alert.current_price && (
                        <> · Current: {formatPrice(alert.current_price)}</>
                      )}
                    </p>
                    {alert.triggered_at && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Last triggered: {formatDate(alert.triggered_at)}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge
                      variant={alert.is_active ? "success" : "secondary"}
                    >
                      {alert.is_active ? "Active" : "Paused"}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleToggle(alert.id, alert.is_active)}
                    >
                      {alert.is_active ? (
                        <Pause className="h-4 w-4" />
                      ) : (
                        <Play className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:text-destructive"
                      onClick={() => handleDelete(alert.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
