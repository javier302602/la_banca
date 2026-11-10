"""CU-20 — Ver el perfil de una persona. Usa la lectura compartida de datos públicos de las cuentas."""
from app.shared.db.perfiles import MongoPerfilesPublicosRepository as MongoVerPerfilRepository

__all__ = ["MongoVerPerfilRepository"]
