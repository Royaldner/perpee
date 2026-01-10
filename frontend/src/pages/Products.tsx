import { useState, useCallback } from "react"
import { useSearchParams } from "react-router-dom"
import { Search, Filter } from "lucide-react"
import { PageHeader } from "@/components/layout/PageHeader"
import { AddProductForm, ProductList } from "@/components/products"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  useProducts,
  useRefreshProduct,
  useDeleteProduct,
  useUpdateProduct,
} from "@/hooks/useProducts"
import type { ProductStatus } from "@/types/api"

export function Products() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [search, setSearch] = useState("")
  const [refreshingIds, setRefreshingIds] = useState<number[]>([])

  const store = searchParams.get("store") || undefined
  const status = (searchParams.get("status") as ProductStatus) || undefined

  const { data: productsData, isLoading, refetch } = useProducts({ store, status })
  const refreshProduct = useRefreshProduct()
  const deleteProduct = useDeleteProduct()
  const updateProduct = useUpdateProduct()

  const handleRefresh = useCallback(
    async (id: number) => {
      setRefreshingIds((prev) => [...prev, id])
      try {
        await refreshProduct.mutateAsync(id)
      } finally {
        setRefreshingIds((prev) => prev.filter((i) => i !== id))
      }
    },
    [refreshProduct]
  )

  const handleDelete = useCallback(
    async (id: number) => {
      if (window.confirm("Are you sure you want to delete this product?")) {
        await deleteProduct.mutateAsync(id)
      }
    },
    [deleteProduct]
  )

  const handleToggleStatus = useCallback(
    async (id: number, newStatus: ProductStatus) => {
      await updateProduct.mutateAsync({ id, data: { status: newStatus } })
    },
    [updateProduct]
  )

  const handleStatusFilter = (value: string) => {
    const newParams = new URLSearchParams(searchParams)
    if (value === "all") {
      newParams.delete("status")
    } else {
      newParams.set("status", value)
    }
    setSearchParams(newParams)
  }

  const handleStoreFilter = (value: string) => {
    const newParams = new URLSearchParams(searchParams)
    if (value === "all") {
      newParams.delete("store")
    } else {
      newParams.set("store", value)
    }
    setSearchParams(newParams)
  }

  // Filter products by search
  const filteredProducts =
    productsData?.items.filter(
      (p) =>
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.store_domain.toLowerCase().includes(search.toLowerCase()) ||
        p.brand?.toLowerCase().includes(search.toLowerCase())
    ) ?? []

  // Get unique stores for filter
  const stores = [...new Set(productsData?.items.map((p) => p.store_domain) ?? [])]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Products"
        description="Manage your tracked products"
        actions={<AddProductForm onSuccess={() => refetch()} />}
      />

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search products..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          <Select
            value={status || "all"}
            onValueChange={handleStatusFilter}
          >
            <SelectTrigger className="w-[140px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="paused">Paused</SelectItem>
              <SelectItem value="error">Error</SelectItem>
              <SelectItem value="needs_attention">Needs Attention</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={store || "all"}
            onValueChange={handleStoreFilter}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Store" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Stores</SelectItem>
              {stores.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Products */}
      <ProductList
        products={filteredProducts}
        isLoading={isLoading}
        onRefresh={handleRefresh}
        onDelete={handleDelete}
        onToggleStatus={handleToggleStatus}
        refreshingIds={refreshingIds}
      />

      {/* Pagination info */}
      {productsData && productsData.meta.total > 0 && (
        <p className="text-sm text-muted-foreground text-center">
          Showing {filteredProducts.length} of {productsData.meta.total} products
        </p>
      )}
    </div>
  )
}
