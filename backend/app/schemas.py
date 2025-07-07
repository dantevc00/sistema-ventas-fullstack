from pydantic import BaseModel
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional



class ProductoInventario(BaseModel):
    id_producto: int
    nombre: str = Field(..., min_length=1)
    precio_unitario: float = Field(..., gt=0)
    cantidad_en_stock: int = Field(..., ge=0)

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v):
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío o solo con espacios")
        return v

    @classmethod
    def from_request(cls, data: dict, id_producto: int):
        """
        Creo un nuevo producto con el ID asignado internamente.
        `data` debe contener nombre, precio_unitario y cantidad_en_stock.
        """
        return cls(
            id_producto=id_producto,
            nombre=data["nombre"],
            precio_unitario=data["precio_unitario"],
            cantidad_en_stock=data["cantidad_en_stock"]
        )

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1)
    precio_unitario: Optional[float] = Field(None, gt=0)
    cantidad_en_stock: Optional[int] = Field(None, ge=0)

    @field_validator("nombre")
    @classmethod
    def no_vacio(cls, v):
        if v is not None and not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v

class Venta(BaseModel):
    id_producto: int = Field(..., ge=1, description="ID del producto debe ser mayor o igual a 1")
    cantidad: int = Field(..., gt=0, description="La cantidad debe ser mayor a 0")
    nombre_cliente: str = Field(..., min_length=1, description="El nombre del cliente no puede estar vacío")

    @field_validator("nombre_cliente")
    @classmethod
    def validar_cliente_no_vacio(cls, valor):
        if not valor.strip():
            raise ValueError("El nombre del cliente no puede ser solo espacios")
        return valor

class VentaRegistrada(Venta):
    id_venta: int
    fecha_venta: datetime