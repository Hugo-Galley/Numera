"""Réponses élémentaires partagées par plusieurs routes d'écriture."""
from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: str  # « success » ou « ok » selon la route


class OkResponse(BaseModel):
    ok: bool


class HealthStatus(BaseModel):
    status: str
    demo: bool  # public : la page de connexion affiche alors les identifiants de démonstration
