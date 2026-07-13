export function TypingIndicator() {
  return (
    <div className="flex gap-1.5 items-center px-4 py-3 bg-secondary rounded-2xl w-fit mb-6 animate-fade-in">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="w-2 h-2 rounded-full bg-muted-foreground"
          style={{
            animation: `typing-dot 1.4s infinite ease-in-out`,
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
    </div>
  )
}
