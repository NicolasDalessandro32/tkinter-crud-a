from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CampoDef:
    nombre: str                       
    etiqueta: str                     
    tipo: str = "texto"
    obligatorio: bool = True
    unico: bool = False                            
    opciones: Optional[List[str]] = None        
    entidad_relacionada: Optional[str] = None        
    ancho: int = 28                  
    def __post_init__(self):
        tipos_validos = {
            "texto", "numero", "email", "password", "select", "fecha", "relacion"
        }
        if self.tipo not in tipos_validos:
            raise ValueError(
                f"Tipo de campo inválido: '{self.tipo}'. "
                f"Debe ser uno de {tipos_validos}"
            )
        if self.tipo == "select" and not self.opciones:
            raise ValueError(
                f"El campo '{self.nombre}' es de tipo 'select' pero no tiene 'opciones'."
            )
        if self.tipo == "relacion" and not self.entidad_relacionada:
            raise ValueError(
                f"El campo '{self.nombre}' es de tipo 'relacion' pero no indica "
                f"'entidad_relacionada'."
            )

    # Serialización: permite guardar la DEFINICIÓN de un campo en JSON (dentro de la tabla de metadatos de basedatos.py).
  
    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "etiqueta": self.etiqueta,
            "tipo": self.tipo,
            "obligatorio": self.obligatorio,
            "unico": self.unico,
            "opciones": self.opciones,
            "entidad_relacionada": self.entidad_relacionada,
            "ancho": self.ancho,
        }

    @staticmethod
    def from_dict(d: dict) -> "CampoDef":
        return CampoDef(
            nombre=d["nombre"],
            etiqueta=d["etiqueta"],
            tipo=d.get("tipo", "texto"),
            obligatorio=d.get("obligatorio", True),
            unico=d.get("unico", False),
            opciones=d.get("opciones"),
            entidad_relacionada=d.get("entidad_relacionada"),
            ancho=d.get("ancho", 28),
        )
