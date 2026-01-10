import { useState, type FormEvent } from "react"
import { Plus, Loader2 } from "lucide-react"
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
  DialogTrigger,
} from "@/components/ui/dialog"
import { useCreateProduct } from "@/hooks/useProducts"

interface AddProductFormProps {
  onSuccess?: () => void
}

export function AddProductForm({ onSuccess }: AddProductFormProps) {
  const [open, setOpen] = useState(false)
  const [url, setUrl] = useState("")
  const createProduct = useCreateProduct()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    try {
      await createProduct.mutateAsync({ url: url.trim() })
      setUrl("")
      setOpen(false)
      onSuccess?.()
    } catch (error) {
      // Error is handled by the mutation
      console.error("Failed to add product:", error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Add Product
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add Product</DialogTitle>
            <DialogDescription>
              Enter the URL of a product you want to track. We'll automatically
              extract the price and product details.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="url">Product URL</Label>
              <Input
                id="url"
                type="url"
                placeholder="https://www.amazon.ca/dp/..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                Supported stores: Amazon, Walmart, Best Buy, Costco, and more.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createProduct.isPending || !url.trim()}>
              {createProduct.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Add Product
            </Button>
          </DialogFooter>
          {createProduct.isError && (
            <p className="text-sm text-destructive mt-2">
              {createProduct.error instanceof Error
                ? createProduct.error.message
                : "Failed to add product. Please check the URL and try again."}
            </p>
          )}
        </form>
      </DialogContent>
    </Dialog>
  )
}
