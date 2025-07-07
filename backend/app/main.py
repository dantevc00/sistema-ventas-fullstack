import json
import io 
import csv
from pathlib import Path
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import StreamingResponse
from .schemas import ProductoInventario, Venta, VentaRegistrada, ProductoUpdate

app = FastAPI()
#-------------------- Autenticacion Hardcodeada de Users------------------------
security = HTTPBasic()

USUARIOS = {
    "admin": "1234",
    "user": "abcd"
}
def autenticar_usuario(credentials: HTTPBasicCredentials = Depends(security)):
    correct_password = USUARIOS.get(credentials.username)
    if not correct_password or credentials.password != correct_password:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return credentials.username

ARCHIVO_PRODUCTOS = "productos.json"
ARCHIVO_VENTAS = "ventas.json"

# ------------------ Manejo de Productos ------------------

def guardar_productos_en_archivo():
    with open(ARCHIVO_PRODUCTOS, "w", encoding="utf-8") as f:
        json.dump([p.model_dump(mode="json") for p in lista_productos], f, ensure_ascii=False, indent=4)

def cargar_productos_desde_archivo():
    archivo = Path(ARCHIVO_PRODUCTOS)
    if archivo.exists():
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
            return [ProductoInventario(**prod) for prod in datos]
    return []

try:
    lista_productos = cargar_productos_desde_archivo()
    if not lista_productos:
        raise FileNotFoundError("productos.json vacío o ilegible.")
except Exception as e:
    print(f"[ERROR] No se pudo cargar productos: {e}")
    lista_productos = []
    guardar_productos_en_archivo()

contador_productos = max([prod.id_producto for prod in lista_productos], default=0) + 1

# ------------------ Manejo de Ventas ------------------

def guardar_ventas_en_archivo():
    with open(ARCHIVO_VENTAS, "w", encoding="utf-8") as f:
        json.dump([v.model_dump(mode="json") for v in historial_ventas], f, ensure_ascii=False, indent=4)

def cargar_ventas_desde_archivo():
    archivo = Path(ARCHIVO_VENTAS)
    if archivo.exists():
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
            return [VentaRegistrada(**venta) for venta in datos]
    return []

try:
    historial_ventas = cargar_ventas_desde_archivo()
except Exception as e:
    print(f"[ERROR] No se pudo cargar ventas: {e}")
    historial_ventas = []
    guardar_ventas_en_archivo()

contador_ventas = max([venta.id_venta for venta in historial_ventas], default=0) + 1

# ------------------ Rutas FastAPI ------------------

@app.get("/")
def read_root():
    return {"mensaje": "Bienvenido al sistema de ventas"}

@app.get("/tienda/productos")
def obtener_productos_disponibles(
    nombre: Optional[str] = Query(None),
    min_precio: Optional[float] = Query(None, ge=0),
    max_precio: Optional[float] = Query(None, ge=0),
    min_stock: Optional[int] = Query(None, ge=0),
    max_stock: Optional[int] = Query(None, ge=0)
):

    if min_precio is not None and max_precio is not None:
        if min_precio > max_precio:
            raise HTTPException(status_code=400, detail="El precio mínimo no puede ser mayor al máximo.")

    if min_stock is not None and max_stock is not None:
        if min_stock > max_stock:
            raise HTTPException(status_code=400, detail="El stock mínimo no puede ser mayor al máximo.")

    productos_filtrados = lista_productos

    if nombre:
        productos_filtrados = [
            p for p in productos_filtrados
            if nombre.lower() in p.nombre.lower()
        ]

    if min_precio is not None:
        productos_filtrados = [
            p for p in productos_filtrados
            if p.precio_unitario >= min_precio
        ]

    if max_precio is not None:
        productos_filtrados = [
            p for p in productos_filtrados
            if p.precio_unitario <= max_precio
        ]

    if min_stock is not None:
        productos_filtrados = [
            p for p in productos_filtrados
            if p.cantidad_en_stock >= min_stock
        ]

    if max_stock is not None:
        productos_filtrados = [
            p for p in productos_filtrados
            if p.cantidad_en_stock <= max_stock
        ]

    return productos_filtrados


@app.get("/ventas/historial")
def obtener_historial_ventas(
    cliente: Optional[str] = Query(None),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None)
):
    ventas_filtradas = historial_ventas

    if cliente:
        ventas_filtradas = [
            v for v in ventas_filtradas
            if v.nombre_cliente.lower() == cliente.lower()
        ]


    if desde:
        try:
            fecha_desde = datetime.strptime(desde, "%Y-%m-%d")
            ventas_filtradas = [
                v for v in ventas_filtradas if v.fecha_venta >= fecha_desde
            ]
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha 'desde' inválido. Use YYYY-MM-DD")

    if hasta:
        try:
            fecha_hasta = datetime.strptime(hasta, "%Y-%m-%d")
            ventas_filtradas = [
                v for v in ventas_filtradas if v.fecha_venta <= fecha_hasta
            ]
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha 'hasta' inválido. Use YYYY-MM-DD")

    return ventas_filtradas

@app.get("/ventas/exportar_csv")
def exportar_historial_csv(usuario: str = Depends(autenticar_usuario)):
    if not historial_ventas:
        raise HTTPException(status_code=404, detail="No hay ventas registradas")

    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "ID Venta", "ID Producto", "Nombre Cliente", "Cantidad", "Fecha Venta"
    ])
    
    for venta in historial_ventas:
        writer.writerow([
            venta.id_venta,
            venta.id_producto,
            venta.nombre_cliente,
            venta.cantidad,
            venta.fecha_venta.strftime("%Y-%m-%d %H:%M:%S")
        ])
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=historial_ventas.csv"}
    )

@app.get("/ventas/{id_venta}")
def obtener_venta_por_id(id_venta: int):
    for venta in historial_ventas:
        if venta.id_venta == id_venta:
            return venta
    raise HTTPException(status_code=404, detail="Venta no encontrada")

@app.post("/tienda/productos/agregar")
def agregar_producto(producto_data: dict,usuario: str = Depends(autenticar_usuario)):
    global contador_productos

    for prod in lista_productos:
        if prod.nombre.lower() == producto_data["nombre"].lower():
            raise HTTPException(status_code=400, detail="Producto ya registrado")

    nuevo_producto = ProductoInventario.from_request(producto_data, contador_productos)

    lista_productos.append(nuevo_producto)
    guardar_productos_en_archivo()
    contador_productos += 1

    return {"mensaje": "Producto registrado exitosamente", "producto": nuevo_producto}

@app.put("/tienda/productos/editar/{id_producto}")
def editar_producto(id_producto: int, datos: ProductoUpdate,usuario: str = Depends(autenticar_usuario)):
    for producto in lista_productos:
        if producto.id_producto == id_producto:
            # Actualizamos solo los campos que se pasaron
            if datos.nombre is not None:
                producto.nombre = datos.nombre
            if datos.precio_unitario is not None:
                producto.precio_unitario = datos.precio_unitario
            if datos.cantidad_en_stock is not None:
                producto.cantidad_en_stock = datos.cantidad_en_stock

            guardar_productos_en_archivo()
            return {"mensaje": "Producto editado exitosamente", "producto": producto}

    raise HTTPException(status_code=404, detail="Producto no encontrado")

@app.delete("/tienda/productos/eliminar/{id_producto}")
def eliminar_Producto(id_producto: int, usuario: str = Depends(autenticar_usuario)):
    ventas_asociadas = any(venta.id_producto == id_producto for venta in historial_ventas)
    if ventas_asociadas:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar el producto con ID {id_producto} porque tiene ventas registradas."
        )
    for i, producto in enumerate(lista_productos):
        if producto.id_producto == id_producto:
            lista_productos.pop(i)
            guardar_productos_en_archivo()
            return {"mensaje": f"Producto con ID {id_producto} eliminado exitosamente."}

    raise HTTPException(status_code=404, detail="Producto no encontrado")

@app.post("/ventas/registrar")
def registrar_venta(venta: Venta,usuario: str = Depends(autenticar_usuario)):
    global contador_ventas
    for producto in lista_productos:
        if producto.id_producto == venta.id_producto:
            if venta.cantidad <= producto.cantidad_en_stock:
                producto.cantidad_en_stock -= venta.cantidad
                guardar_productos_en_archivo()
                venta_registrada = VentaRegistrada(
                    id_venta=contador_ventas,
                    **venta.dict(),
                    fecha_venta=datetime.now()
                )
                historial_ventas.append(venta_registrada)
                guardar_ventas_en_archivo()
                contador_ventas += 1
                return {"mensaje": "Venta registrada exitosamente", "datos": venta_registrada}
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente para {producto.nombre} (disponible: {producto.cantidad_en_stock}, solicitado: {venta.cantidad})"
                )
    raise HTTPException(status_code=404, detail="Producto no encontrado")

