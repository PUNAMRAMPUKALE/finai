# app/api/v1/deps.py
from app.domain.services.recommendation import recommend as _recommend

def get_recommend():
    """
    Dependency injection wrapper for the recommend() service.
    Later you can replace this with a class-based instance if needed.
    """
    return _recommend
