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

function sourceMeta(s: SourceCitation) {
  const m = s.metadata || {}
  return {
    doc: (m.source as string) || s.source || 'Document',
    heading: (m.heading as string) || '',
    chunk: m.chunk_index !== undefined ? `#${(m.chunk_index as number) + 1}` : '',
  }
}

export function SourceModal({ open, onOpenChange, sources }: SourceModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[70vh]">
        <DialogHeader>
          <DialogTitle>Sources</DialogTitle>
        </DialogHeader>
        <ScrollArea className="max-h-[55vh] pr-4">
          {sources.map((source, i) => {
            const meta = sourceMeta(source)
            return (
              <div
                key={i}
                className="mb-4 pb-4 border-b last:border-b-0 last:mb-0 last:pb-0"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold">
                    {meta.heading || 'Untitled Section'}
                  </span>
                  <span className="text-xs text-primary font-medium">
                    {(source.score * 100).toFixed(0)}% match
                  </span>
                </div>
                <div className="flex gap-2 text-xs text-muted-foreground mb-2">
                  <span>{meta.doc}</span>
                  {meta.chunk && <span>Chunk {meta.chunk}</span>}
                </div>
                <p className="text-sm bg-muted p-3 rounded-md leading-relaxed max-h-[120px] overflow-y-auto">
                  {source.content}
                </p>
              </div>
            )
          })}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
