/** Investissements : nom complet d'une entreprise au survol de sa graduation tronquée. */
import { render, screen } from "@testing-library/react"
import { CompanyTick } from "@/pages/Investments/TopCompanies"

describe("Investissements : top entreprises", () => {
  it("donne le nom complet en infobulle", () => {
    const name = "TSMC (Taiwan Semiconductor Manufacturing)"
    render(<svg><CompanyTick x={140} y={20} name={name} ticker="2330.TW" isMobile={false} /></svg>)
    expect(screen.getByText(name, { selector: "span" })).toHaveAttribute("title", name)
    expect(document.querySelector("g > title")?.textContent).toBe(name)
  })
})
