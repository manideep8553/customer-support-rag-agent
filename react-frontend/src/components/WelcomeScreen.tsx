import { MessageCircle } from 'lucide-react'

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
    <div className="max-w-xl mx-auto mt-20 text-center">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 mb-6">
        <MessageCircle className="h-8 w-8 text-primary" />
      </div>
      <h2 className="text-2xl font-semibold tracking-tight mb-2">
        How can I help you today?
      </h2>
      <p className="text-muted-foreground text-sm leading-relaxed mb-8 max-w-md mx-auto">
        I'm GigaBot, your AI support agent. I can answer questions about GigaCorp
        products, policies, billing, and more.
      </p>
      <div className="flex flex-wrap gap-2 justify-center">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => onSuggestionClick(suggestion)}
            className="px-4 py-2 text-sm rounded-full border bg-card text-muted-foreground hover:border-primary hover:text-primary hover:bg-primary/5 transition-all"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
}
