const SUGGESTIONS = [
  'What is your return policy?',
  'How much does GigaAnalytics cost?',
  'What support tiers do you offer?',
  'How do I reset my password?',
  'Do you ship internationally?',
  'What is the warranty on servers?',
]

interface WelcomeScreenProps {
  onSuggestionClick: (text: string) => void
}

export function WelcomeScreen({ onSuggestionClick }: WelcomeScreenProps) {
  return (
    <div className="w-full max-w-[var(--chat-width)] mx-auto px-4 md:px-8 py-12">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 mb-4">
          <span className="text-xl font-bold text-primary">G</span>
        </div>
        <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-foreground/90 mb-2">
          How can I help you today?
        </h1>
        <p className="text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
          I'm GigaBot, your AI support agent. I can answer questions about GigaCorp
          products, policies, billing, and more.
        </p>
      </div>
      <div className="flex flex-wrap gap-2 justify-center max-w-lg mx-auto">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => onSuggestionClick(suggestion)}
            className="px-3.5 py-2 text-xs md:text-sm rounded-lg border border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-primary hover:bg-primary/5 transition-all"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
}
