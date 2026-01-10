import { useState, type FormEvent } from "react"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useProducts } from "@/hooks/useProducts"
import { useCreateAlert } from "@/hooks/useAlerts"
import type { AlertType } from "@/types/api"

interface AlertFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
  productId?: number
}

const alertTypes: { value: AlertType; label: string; description: string }[] = [
  {
    value: "target_price",
    label: "Target Price",
    description: "Alert when price drops to or below a target",
  },
  {
    value: "percent_drop",
    label: "Percent Drop",
    description: "Alert when price drops by a certain percentage",
  },
  {
    value: "any_change",
    label: "Any Change",
    description: "Alert on any price change",
  },
  {
    value: "back_in_stock",
    label: "Back in Stock",
    description: "Alert when item is back in stock",
  },
]

export function AlertForm({
  open,
  onOpenChange,
  onSuccess,
  productId: initialProductId,
}: AlertFormProps) {
  const [productId, setProductId] = useState<number | undefined>(initialProductId)
  const [alertType, setAlertType] = useState<AlertType>("target_price")
  const [targetValue, setTargetValue] = useState("")
  const [minThreshold, setMinThreshold] = useState("1")

  const { data: productsData, isLoading: productsLoading } = useProducts()
  const createAlert = useCreateAlert()

  const requiresTargetValue = alertType === "target_price" || alertType === "percent_drop"

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!productId) return

    try {
      await createAlert.mutateAsync({
        product_id: productId,
        alert_type: alertType,
        target_value: requiresTargetValue ? parseFloat(targetValue) : undefined,
        min_change_threshold: parseFloat(minThreshold),
      })
      resetForm()
      onSuccess?.()
    } catch (error) {
      console.error("Failed to create alert:", error)
    }
  }

  const resetForm = () => {
    if (!initialProductId) {
      setProductId(undefined)
    }
    setAlertType("target_price")
    setTargetValue("")
    setMinThreshold("1")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create Alert</DialogTitle>
            <DialogDescription>
              Set up a price alert for a product. You'll be notified via email
              when the conditions are met.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {/* Product Selection */}
            {!initialProductId && (
              <div className="space-y-2">
                <Label htmlFor="product">Product</Label>
                <Select
                  value={productId?.toString() || ""}
                  onValueChange={(val) => setProductId(parseInt(val, 10))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a product" />
                  </SelectTrigger>
                  <SelectContent>
                    {productsLoading ? (
                      <SelectItem value="loading" disabled>
                        Loading...
                      </SelectItem>
                    ) : (
                      productsData?.items.map((product) => (
                        <SelectItem key={product.id} value={product.id.toString()}>
                          {product.name}
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Alert Type */}
            <div className="space-y-2">
              <Label htmlFor="alert-type">Alert Type</Label>
              <Select
                value={alertType}
                onValueChange={(val) => setAlertType(val as AlertType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {alertTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      <div className="flex flex-col">
                        <span>{type.label}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {alertTypes.find((t) => t.value === alertType)?.description}
              </p>
            </div>

            {/* Target Value */}
            {requiresTargetValue && (
              <div className="space-y-2">
                <Label htmlFor="target">
                  {alertType === "target_price" ? "Target Price ($)" : "Percent Drop (%)"}
                </Label>
                <Input
                  id="target"
                  type="number"
                  step={alertType === "target_price" ? "0.01" : "1"}
                  min="0"
                  placeholder={alertType === "target_price" ? "49.99" : "10"}
                  value={targetValue}
                  onChange={(e) => setTargetValue(e.target.value)}
                  required
                />
              </div>
            )}

            {/* Minimum Threshold */}
            <div className="space-y-2">
              <Label htmlFor="threshold">
                Minimum Change Threshold {alertType === "percent_drop" ? "(%)" : "($)"}
              </Label>
              <Input
                id="threshold"
                type="number"
                step="0.01"
                min="0"
                placeholder="1"
                value={minThreshold}
                onChange={(e) => setMinThreshold(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Ignore changes smaller than this amount
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={createAlert.isPending || !productId}
            >
              {createAlert.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Create Alert
            </Button>
          </DialogFooter>
          {createAlert.isError && (
            <p className="text-sm text-destructive mt-2">
              {createAlert.error instanceof Error
                ? createAlert.error.message
                : "Failed to create alert."}
            </p>
          )}
        </form>
      </DialogContent>
    </Dialog>
  )
}
