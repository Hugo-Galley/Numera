/** Pied de dialogue sur mobile : collé au bord bas, sans bande où le contenu défile dessous (audit visuel). */
import { render, screen } from "@testing-library/react"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle } from "@/components/ui/dialog"

describe("DialogFooter", () => {
  it("mobile : collant à -1,5 rem (compense le padding p-6), pas à bottom-0", () => {
    render(
      <Dialog open>
        <DialogContent>
          <DialogTitle>Titre</DialogTitle>
          <DialogDescription>Texte</DialogDescription>
          <DialogFooter><button>Enregistrer</button></DialogFooter>
        </DialogContent>
      </Dialog>,
    )
    const footer = screen.getByRole("button", { name: "Enregistrer" }).parentElement!
    expect(footer).toHaveClass("max-sm:sticky", "max-sm:-bottom-6", "max-sm:-mb-6")
    expect(footer).not.toHaveClass("max-sm:bottom-0")
  })
})
