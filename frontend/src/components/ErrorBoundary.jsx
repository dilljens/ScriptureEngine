import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null } }
  static getDerivedStateFromError(error) { return { error } }
  render() {
    if (this.state.error) return (
      <div className="mx-4 mt-8 p-6 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
        <h2 className="text-sm font-semibold text-red-800 dark:text-red-300 mb-2">Something went wrong</h2>
        <pre className="text-xs text-red-700 dark:text-red-300 overflow-auto max-h-40">{this.state.error.stack}</pre>
        <button onClick={() => window.location.reload()} className="mt-3 text-sm text-red-700 underline hover:text-red-900 cursor-pointer">Reload page</button>
      </div>
    )
    return this.props.children
  }
}
