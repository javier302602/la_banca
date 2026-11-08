"""CU-15 — Configurar los parámetros del sistema. Controlador MVC.

Sin endpoint público (RF-CFG-08): la configuración se gestiona por variables de entorno.
El router existe vacío para mantener la forma del slice.
"""
from fastapi import APIRouter

router = APIRouter(tags=["M06 Configuración"])
