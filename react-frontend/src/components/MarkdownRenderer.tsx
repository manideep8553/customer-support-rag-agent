import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'

interface MarkdownRendererProps {
  content: string
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const processed = useMemo(() => {
    return content
      .replace(/^### (.+)$/gm, '**$1**')
      .replace(/^## (.+)$/gm, '**$1**')
      .replace(/^# (.+)$/gm, '**$1**')
  }, [content])

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>,
        li: ({ children }) => <li>{children}</li>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        em: ({ children }) => <em>{children}</em>,
        code: ({ children, className }) => {
          const isInline = !className
          if (isInline) {
            return (
              <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground/80">
                {children}
              </code>
            )
          }
          return (
            <div className="relative group my-2">
              <div className="flex items-center justify-between px-3 py-1.5 text-[10px] font-mono bg-muted/80 rounded-t-lg border border-border text-muted-foreground">
                <span>{(className || '').replace('language-', '') || 'code'}</span>
              </div>
              <pre className="bg-muted/50 border border-t-0 border-border rounded-b-lg overflow-x-auto">
                <code className={`${className || ''} text-sm leading-relaxed block p-3`}>
                  {children}
                </code>
              </pre>
            </div>
          )
        },
        a: ({ children, href }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-2 hover:text-primary/80">
            {children}
          </a>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-3 border-primary/30 pl-3 italic text-muted-foreground my-2">
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="min-w-full text-sm border-collapse border border-border">{children}</table>
          </div>
        ),
        th: ({ children }) => <th className="border border-border bg-muted px-3 py-1.5 text-left font-semibold">{children}</th>,
        td: ({ children }) => <td className="border border-border px-3 py-1.5">{children}</td>,
        hr: () => <hr className="my-4 border-border" />,
      }}
    >
      {processed}
    </ReactMarkdown>
  )
}
