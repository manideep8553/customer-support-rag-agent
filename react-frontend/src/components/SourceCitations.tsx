import { useState } from 'react'
import { type SourceCitation } from '@/api/client'
import { ChevronDown, ChevronUp, FileText, ExternalLink } from 'lucide-react'

interface SourceCitationsProps {
  sources: SourceCitation[]
}

function sourceMeta(s: SourceCitation) {
  const m = s.metadata || {}
  return {
    heading: (m.heading as string) || '',
    doc: (m.source as string) || s.source || 'Document',
    chunk: m.chunk_index !== undefined ? `#${(m.chunk_index as number) + 1}` : '',
  }
}

export function SourceCitations({ sources }: SourceCitationsProps) {
  const [expanded, setExpanded] = useState(false)
  const displaySources = expanded ? sources : sources.slice(0, 3)
  const hasMore = sources.length > 3

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-card">
      <div
        className="flex items-center gap-2 px-3 py-2 text-[11px] font-medium text-muted-foreground cursor-pointer hover:bg-muted/30 transition-colors select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <FileText className="h-3.5 w-3.5" />
        <span>{sources.length} source{sources.length !== 1 ? 's' : ''}</span>
        <div className="ml-auto flex items-center gap-1">
          <span className="text-[10px] text-muted-foreground/60">
            {sources.length > 0 && `${(Math.max(...sources.map(s => s.score)) * 100).toFixed(0)}% max relevance`}
          </span>
          {hasMore && (
            expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
          )}
        </div>
      </div>
      <div className="divide-y divide-border">
        {displaySources.map((source, i) => {
          const meta = sourceMeta(source)
          return (
            <div key={i} className="px-3 py-2 hover:bg-muted/20 transition-colors">
              <div className="flex items-start gap-2">
                <span className="w-4 h-4 rounded bg-primary/10 text-primary text-[9px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-foreground/80 truncate">
                      {meta.heading || 'Untitled Section'}
                    </span>
                    <span className="text-[10px] text-primary/70 font-medium flex-shrink-0">
                      {(source.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground/70 mt-0.5 truncate">{meta.doc}</p>
                  <p className="text-[11px] text-foreground/60 mt-1 line-clamp-2 leading-relaxed">
                    {source.content}
                  </p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
      {hasMore && !expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="w-full px-3 py-1.5 text-[11px] text-primary hover:text-primary/80 hover:bg-muted/30 transition-colors text-center font-medium"
        >
          Show all {sources.length} sources
        </button>
      )}
    </div>
  )
}
