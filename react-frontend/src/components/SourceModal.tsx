import { type SourceCitation } from '@/api/client'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'

interface SourceModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sources: SourceCitation[]
}

export function SourceModal({ open, onOpenChange, sources }: SourceModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[70vh]">
        <DialogHeader>
          <DialogTitle>Sources</DialogTitle>
        </DialogHeader>
        <ScrollArea className="max-h-[55vh] pr-4">
          {sources.map((source, i) => (
            <div
              key={i}
              className="mb-4 pb-4 border-b last:border-b-0 last:mb-0 last:pb-0"
            >
              <div className="flex justify-between text-xs text-muted-foreground mb-2">
                <span>Source {i + 1}</span>
                <span>Relevance: {(source.score * 100).toFixed(0)}%</span>
              </div>
              <p className="text-sm bg-muted p-3 rounded-md leading-relaxed max-h-[120px] overflow-y-auto">
                {source.content}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Document: {source.source}
              </p>
            </div>
          ))}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
