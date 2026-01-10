import { Link } from "react-router-dom"
import { Bell, Trash2, Pause, Play } from "lucide-react"
import { formatPrice, formatDate } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { AlertWithProduct, AlertType } from "@/types/api"

interface AlertCardProps {
  alert: AlertWithProduct
  onDelete?: (id: number) => void
  onToggle?: (id: number, isActive: boolean) => void
}

const alertTypeLabels: Record<AlertType, string> = {
  target_price: "Target Price",
  percent_drop: "Percent Drop",
  any_change: "Any Change",
  back_in_stock: "Back in Stock",
}

export function AlertCard({ alert, onDelete, onToggle }: AlertCardProps) {
  return (
    <Card>
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
            <Badge variant={alert.is_active ? "success" : "secondary"}>
              {alert.is_active ? "Active" : "Paused"}
            </Badge>
            {onToggle && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onToggle(alert.id, alert.is_active)}
              >
                {alert.is_active ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="icon"
                className="text-destructive hover:text-destructive"
                onClick={() => onDelete(alert.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
