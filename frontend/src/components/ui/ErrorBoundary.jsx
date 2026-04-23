import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    const { fallback, label = "component" } = this.props;
    if (fallback) return fallback;

    return (
      <div className="flex flex-col items-center justify-center gap-4 h-full w-full p-8 text-center">
        <div className="w-12 h-12 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
          <AlertTriangle size={22} className="text-red-400" />
        </div>
        <div>
          <p className="text-slate-300 font-semibold text-sm mb-1">
            {`The ${label} crashed`}
          </p>
          <p className="text-slate-600 text-xs max-w-xs">
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
        </div>
        <button
          onClick={() => {
            this.setState({ hasError: false, error: null });
            window.location.reload();
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-slate-400 hover:text-slate-200 text-xs transition-colors"
        >
          <RefreshCw size={12} />
          Reload page
        </button>
      </div>
    );
  }
}

export default ErrorBoundary;
