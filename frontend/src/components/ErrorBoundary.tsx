import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Global error boundary that catches render errors and displays a fallback
 * instead of crashing the entire app (which would show a blank page and
 * make it look like the app "navigated away").
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-background p-6">
          <div className="max-w-md rounded-xl border border-border bg-card p-6 shadow-lg">
            <h1 className="text-lg font-semibold text-foreground">
              Something went wrong
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              An unexpected error occurred while rendering this page.
              This is usually caused by a transient issue — try reloading.
            </p>
            {this.state.error && (
              <pre className="mt-3 max-h-32 overflow-auto rounded-md bg-muted p-2 text-xs text-muted-foreground">
                {this.state.error.message}
              </pre>
            )}
            <button
              type="button"
              onClick={() => this.setState({ hasError: false, error: null })}
              className="btn-primary mt-4 w-full"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
