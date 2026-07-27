import { Box } from "lucide-react"

export function EmptyState({ title = "No data found", description = "Get started by creating a new resource." }: { title?: string, description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-white/5 mb-6">
        <Box className="h-10 w-10 text-muted-foreground" />
      </div>
      <h3 className="text-xl font-semibold tracking-tight">{title}</h3>
      <p className="text-sm text-muted-foreground mt-2 max-w-sm">{description}</p>
    </div>
  )
}
