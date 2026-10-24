import { Component, type ErrorInfo, type ReactNode } from "react"
import { AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"

interface Props {
  children: ReactNode
  /** Affichage compact (dans la zone de contenu, le menu reste utilisable) ou page entière. */
  fullPage?: boolean
}

interface State {
  error: Error | null
}

/** Filet de sécurité : une exception de rendu affiche un message au lieu d'une page blanche. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Erreur de rendu :", error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className={`flex flex-col items-center justify-center gap-4 p-8 text-center ${this.props.fullPage ? "min-h-dvh" : "h-[60vh]"}`}>
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Cette page a rencontré une erreur</h2>
          <p className="mt-1 text-sm text-slate-500">Vos données ne sont pas affectées. Réessayez ou rechargez la page.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => this.setState({ error: null })}>Réessayer</Button>
          <Button onClick={() => window.location.reload()}>Recharger</Button>
        </div>
      </div>
    )
  }
}
