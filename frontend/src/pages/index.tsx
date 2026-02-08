import Link from 'next/link';
import ThemeToggle from '@/components/ThemeToggle';

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-text">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md bg-bg-secondary/80 border-b border-border">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bi-gradient rounded-full"></div>
              <h1 className="text-2xl font-bold bi-gradient-text">OpenRecords</h1>
            </div>
            <div className="flex items-center space-x-4">
              <ThemeToggle />
              <Link 
                href="/login" 
                className="text-text-muted hover:text-text transition-colors duration-200 font-medium"
              >
                Login
              </Link>
              <Link 
                href="/signup" 
                className="px-6 py-2 bi-gradient rounded-full font-semibold text-white hover:shadow-lg transition-all duration-200 hover:scale-105"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-bg-secondary/50 to-transparent"></div>
        <div className="container mx-auto px-6 relative z-10">
          <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-5xl md:text-7xl font-extrabold mb-6 leading-tight">
              <span className="bi-gradient-text">OpenRecords</span>
            </h1>
            <h2 className="text-2xl md:text-3xl text-text-muted mb-8 font-light">
              Your Private AI Knowledge Archive
            </h2>
            <p className="text-xl text-text-muted max-w-3xl mx-auto mb-12 leading-relaxed">
              OpenRecords is a local-first, privacy-focused AI notebook that helps you search, 
              understand, and retrieve information from your own documents — using the model of your choice.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link 
                href="/signup"
                className="px-8 py-4 bi-gradient rounded-full font-bold text-lg text-white hover:shadow-2xl transition-all duration-200 hover:scale-105 flex items-center gap-2"
              >
                Start Building Your Archive
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-bg-secondary">
        <div className="container mx-auto px-6">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                title: "📚 Document Intelligence",
                description: "Upload and query PDFs, Markdown, and text files using retrieval-augmented generation."
              },
              {
                title: "🤖 Model Freedom",
                description: "Use OpenRouter to choose from multiple AI models: Kimi, Claude, GPT, DeepSeek, and more."
              },
              {
                title: "⌨️ Keyboard-First Workflow",
                description: "Designed for power users. Search, upload, and navigate with shortcuts."
              },
              {
                title: "🗄️ Encrypted Vault",
                description: "All records are encrypted on disk. Even local leaks remain unreadable."
              },
              {
                title: "🚀 Fast Local Performance",
                description: "SQLite + smart caching = instant access to recent data."
              }
            ].map((feature, index) => (
              <div 
                key={index} 
                className="p-8 rounded-2xl surface-tertiary border border-border hover:border-border-strong transition-all duration-300 hover:shadow-lg"
              >
                <h3 className="text-xl font-bold mb-4 text-text">{feature.title}</h3>
                <p className="text-text-muted">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Philosophy Section */}
      <section className="py-20">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold mb-12 text-center">📌 Project Philosophy</h2>
            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  principle: "Privacy over convenience",
                  description: "Your data never leaves your machine. No compromises."
                },
                {
                  principle: "Control over lock-in",
                  description: "Switch models freely. Own your data. No vendor lock-in."
                },
                {
                  principle: "Tools over hype",
                  description: "Built for actual use, not buzzwords. This is an archive for thinking."
                }
              ].map((item, index) => (
                <div 
                  key={index} 
                  className="text-center p-6 rounded-xl border border-border hover:shadow-lg transition-all duration-300"
                >
                  <div className="text-4xl mb-4">{
                    index === 0 ? "🔐" : index === 1 ? "⚖️" : "🛠️"
                  }</div>
                  <h3 className="text-xl font-bold mb-3 text-text">{item.principle}</h3>
                  <p className="text-text-muted">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="py-20 relative overflow-hidden">
        <div className="absolute inset-0 bi-gradient opacity-10"></div>
        <div className="container mx-auto px-6 relative z-10">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-4xl font-bold mb-8">Ready to Build Your Knowledge Archive?</h2>
            <div className="flex flex-col sm:flex-row gap-6 justify-center items-center mb-12">
              <Link 
                href="/signup"
                className="px-8 py-4 bi-gradient rounded-full font-bold text-lg text-white hover:shadow-2xl transition-all duration-200 hover:scale-105"
              >
                Create an Account
              </Link>
              <Link 
                href="/login"
                className="px-8 py-4 border-2 border-border rounded-full font-bold text-lg text-text hover:border-border-strong transition-all duration-200"
              >
                Login to Your Archive
              </Link>
            </div>
            <p className="text-text-muted text-lg">
              No subscriptions. No paywalls. Your data stays yours.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border bg-bg-secondary">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-8 md:mb-0">
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-6 h-6 bi-gradient rounded-full"></div>
                <h2 className="text-xl font-bold bi-gradient-text">OpenRecords</h2>
              </div>
              <p className="text-text-muted">Knowledge, preserved.</p>
            </div>
            <div className="text-center md:text-right">
              <p className="text-text-muted mb-4">
                Open source • Community-driven • Self-hostable
              </p>
              <a 
                href="https://github.com/DebadityaMalakar" 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-text hover:text-purple-soft transition-colors duration-200"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                GitHub
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}