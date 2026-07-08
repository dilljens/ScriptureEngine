import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo })
    // Log to console for debugging
    console.error('React Error Boundary caught:', error)
    if (errorInfo?.componentStack) {
      console.error('Component stack:', errorInfo.componentStack)
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-white dark:bg-neutral-950 p-8">
          <div className="max-w-md text-center">
            <div className="text-4xl mb-4">⚠️</div>
            <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
              Something went wrong
            </h1>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-lg bg-indigo-500 text-white text-sm hover:bg-indigo-600 transition-colors"
            >
              Reload page
            </button>
            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <details className="mt-4 text-left">
                <summary className="text-xs text-neutral-400 cursor-pointer">Error details</summary>
                <pre className="mt-2 text-[10px] text-red-500 overflow-auto max-h-60 p-2 rounded bg-neutral-100 dark:bg-neutral-900">
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
