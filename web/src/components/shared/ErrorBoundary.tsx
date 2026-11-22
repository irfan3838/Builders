// Contain render errors: one malformed card must not take the whole workspace down with it.
import { Component, ErrorInfo, ReactNode } from "react";

type Props = { children: ReactNode; fallback: (error: Error, reset: () => void) => ReactNode; resetKey?: unknown; label?: string };
type State = { error: Error | null };

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[Purser] ${this.props.label ?? "render"} failed`, error, info.componentStack);
  }

  componentDidUpdate(prev: Props) {
    // New data for the same slot (e.g. a revised card) gets a fresh attempt.
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  reset = () => this.setState({ error: null });

  render() {
    return this.state.error ? this.props.fallback(this.state.error, this.reset) : this.props.children;
  }
}
