import { Component, type ErrorInfo, type ReactNode } from "react"
import { ErrorState } from "./ErrorState"

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onReset?: () => void
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo)
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null })
    this.props.onReset?.()
  }

  public override render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="p-8">
          <ErrorState
            title="Component Error"
            message="A critical render error occurred while loading this view."
            errorDetails={this.state.error?.stack || this.state.error?.message}
            onRetry={this.handleReset}
          />
        </div>
      )
    }

    return this.props.children
  }
}
