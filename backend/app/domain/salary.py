"""Salaire et temps de travail : calculs purs (règle métier 6)."""


def month_key(year: int, month: int) -> str:
    """Libellé d'un mois de paie : « 2026-09 »."""
    return f"{year}-{month:02d}"


def salary_amount(net_salary: float, telework_days: int, ticket_employee_share: float) -> float:
    """Salaire versé = net − jours de télétravail × part salariale du ticket restaurant."""
    return net_salary - telework_days * ticket_employee_share


def salary_note(net_salary: float, nb_tickets: int, ticket_employee_share: float, real_salary: float) -> str:
    return (
        f"Net: {net_salary:.2f}€ - TR({nb_tickets}×{ticket_employee_share:.2f}€): "
        f"{real_salary:.2f}€"
    )


def hourly_rate(net_salary: float | None, work_days_per_year: int, work_hours_per_day: float) -> float | None:
    """Taux horaire net : le salaire net de 12 mois rémunère les seules heures réellement travaillées."""
    hours_per_year = work_days_per_year * work_hours_per_day
    if not net_salary or net_salary <= 0 or hours_per_year <= 0:
        return None
    return round(net_salary * 12 / hours_per_year, 2)
