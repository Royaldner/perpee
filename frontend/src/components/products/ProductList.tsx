import { ProductCard } from "./ProductCard"
import { Skeleton } from "@/components/ui/skeleton"
import type { ProductListItem, ProductStatus } from "@/types/api"

interface ProductListProps {
  products: ProductListItem[]
  isLoading?: boolean
  onRefresh?: (id: number) => void
  onDelete?: (id: number) => void
  onToggleStatus?: (id: number, status: ProductStatus) => void
  refreshingIds?: number[]
}

export function ProductList({
  products,
  isLoading = false,
  onRefresh,
  onDelete,
  onToggleStatus,
  refreshingIds = [],
}: ProductListProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-4 p-4 border rounded-xl">
            <Skeleton className="h-20 w-20 rounded-md" />
            <div className="flex-1 space-y-3">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <div className="flex justify-between">
                <Skeleton className="h-6 w-24" />
                <Skeleton className="h-6 w-32" />
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (products.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p>No products found.</p>
        <p className="text-sm mt-1">
          Add a product by clicking the "Add Product" button above.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {products.map((product) => (
        <ProductCard
          key={product.id}
          product={product}
          onRefresh={onRefresh}
          onDelete={onDelete}
          onToggleStatus={onToggleStatus}
          isRefreshing={refreshingIds.includes(product.id)}
        />
      ))}
    </div>
  )
}
