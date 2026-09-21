import { Component, type ErrorInfo, type ReactNode } from 'react'

/**
 * The last thing between a render error and a white page.
 *
 * An exception during render unmounts the whole tree: no message, no way back,
 * nothing. It happened twice in v1, both times because a run carried a shape the
 * panel had not been told to expect. Each was fixed where it was caused, and
 * neither is a guarantee — the data comes from runs written by a model, and its
 * shapes will keep drifting.
 *
 * So one screen failing costs one screen.
 */

interface Props {
  what: string
  children: ReactNode
  onEscape?: () => void
}

export class Boundary extends Component<Props, { error: Error | null }> {
  state = { error: null as Error | null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[${this.props.what}] failed to render`, error, info)
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children
    return (
      <section className="panel panel--bad">
        <h2>{this.props.what} could not be rendered</h2>
        <p className="muted">
          Nothing here writes anything, so the run&rsquo;s files are untouched and the
          other screens still work.
        </p>
        <pre className="code">
          {error.name}: {error.message}
        </pre>
        {this.props.onEscape && (
          <button type="button" onClick={this.props.onEscape}>
            Back to the library
          </button>
        )}
      </section>
    )
  }
}
