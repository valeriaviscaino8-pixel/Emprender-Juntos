from datetime import datetime
from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Boolean, Column, Date, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Query, Request, Response
from typing import Optional

# 1. Configuración de FastAPI y Jinja2
app = FastAPI()
templates = Jinja2Templates(directory="templates")


# 2. CONFIGURACIÓN DE LA BASE DE DATOS (¡DEBE IR AQUÍ ARRIBA!)
SQLALCHEMY_DATABASE_URL = "sqlite:///./datos.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. Modelos (UsuarioDB y EmprendedorDB)
class UsuarioDB(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    rol = Column(String)

class EmprendedorDB(Base):
    __tablename__ = "emprendedores"
    id = Column(Integer, primary_key=True, index=True)
    cedula = Column(String, unique=True, index=True)
    nombre = Column(String)
    apellido = Column(String)
    telefono = Column(String)
    nombre_emprendimiento = Column(String)
    nacionalidad = Column(String)
    comuna = Column(String)
    rubro = Column(String)
    sector = Column(String)
    tiene_certificado = Column(Boolean, default=False)
    fecha_emision = Column(Date, nullable=True)

Base.metadata.create_all(bind=engine)
    
# 1. Muestra el formulario con los datos prellenados
@app.get("/editar/{emprendedor_id}", response_class=HTMLResponse)
def root(request: Request):
    username = request.cookies.get("user_session")
    if username:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse(request, "login.html", {"error": None})
def editar_page(request: Request, emprendedor_id: int):
    username = request.cookies.get("user_session")
    if not username:
        return RedirectResponse(url="/")
        
    db = SessionLocal()
    emprendedor = db.query(EmprendedorDB).filter(EmprendedorDB.id == emprendedor_id).first()
    db.close()

    if not emprendedor:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(request, "editar.html", {
        "user": username,
        "emp": emprendedor
    })

# 2. Recibe los cambios y los guarda en SQLite
@app.post("/editar/{emprendedor_id}")
def editar_post(
    emprendedor_id: int,
    cedula: str = Form(...),
    nombre: str = Form(...),
    apellido: str = Form(...),
    telefono: str = Form(...),
    nombre_emprendimiento: str = Form(...),
    nacionalidad: str = Form(...),
    sector: str = Form(...),
    comuna: str = Form(...),
    rubro: str = Form(...),
    tiene_certificado: bool = Form(False),
    fecha_emision: str = Form(None)
):
    db = SessionLocal()
    emprendedor = db.query(EmprendedorDB).filter(EmprendedorDB.id == emprendedor_id).first()
    
    if emprendedor:
        emprendedor.cedula = cedula
        emprendedor.nombre = nombre
        emprendedor.apellido = apellido
        emprendedor.telefono = telefono
        emprendedor.nombre_emprendimiento = nombre_emprendimiento
        emprendedor.nacionalidad = nacionalidad
        emprendedor.sector = sector
        emprendedor.rubro = rubro
        emprendedor.comuna = comuna
        emprendedor.tiene_certificado = tiene_certificado
        emprendedor.fecha_emision = datetime.strptime(fecha_emision, "%Y-%m-%d").date() if fecha_emision else None
        
        db.commit()
    db.close()
    
# 4. Función init_db (que ya puede usar SessionLocal porque ya fue creado arriba)
def init_db():
    db = SessionLocal()
    if not db.query(UsuarioDB).filter(UsuarioDB.username == "directora").first():
        db.add(UsuarioDB(username="directora", password="123", rol="admin"))
        db.add(UsuarioDB(username="operador1", password="123", rol="operador"))
        db.commit()
    db.close()

init_db()

#Funcion para mostrar la pagina de inicio de sesion, donde se puede ingresar el nombre de usuario y la contraseña.
# Función para mostrar la página de inicio de sesión (acepta un error opcional por URL)
@app.get("/", response_class=HTMLResponse)
def login_page(request: Request, error: str = None):
    return templates.TemplateResponse(request, "login.html", {"error": error})


# Función para procesar el inicio de sesión correctamente
@app.post("/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    # 1. Buscamos en la tabla UsuarioDB (aquí viven 'directora' y 'operador1')
    user = db.query(UsuarioDB).filter(UsuarioDB.username == username).first()
    db.close()

    # 2. Validamos si el usuario existe y si la contraseña coincide con la de la base de datos
    if not user or user.password != password:
        # Redirigimos al GET con el mensaje de error (evita que el error se quede fijo al recargar)
        return RedirectResponse(url="/?error=Usuario+o+contraseña+incorrectos", status_code=status.HTTP_303_SEE_OTHER)

    # Si es correcto, crea la cookie y redirige al dashboard de forma segura
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="user_session", value=username)
    return response

# Función para mostrar la página del dashboard (versión única y limpia)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    username = request.cookies.get("user_session")
    if not username:
        return RedirectResponse(url="/")
    
    db = SessionLocal()
    emprendedores = db.query(EmprendedorDB).all()
    db.close()

    lista_procesada = []
    for e in emprendedores:
        estado_cert = "Sin Certificado"
        clase_css = "text-gray-500"
        if e.tiene_certificado and e.fecha_emision:
            anos = (datetime.now().date() - e.fecha_emision).days / 365.25
            if anos > 3:
                estado_cert = "Vencido"
                clase_css = "text-black-600 font-bold"
            else:
                estado_cert = "Vigente"
                clase_css = "text-green-600 font-bold"
        
        lista_procesada.append({
            "id": e.id,
            "cedula": e.cedula,
            "nombre_completo": f"{e.nombre} {e.apellido}",
            "telefono": e.telefono,
            "emprendimiento": e.nombre_emprendimiento,
            "nacionalidad": e.nacionalidad,
            "sector": e.sector,
            "rubro": e.rubro,
            "comuna": e.comuna,
            "estado_cert": estado_cert,
            "clase_css": clase_css
        })

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": username, "emprendedores": lista_procesada
    })
#Funcion para agregar un nuevo emprendedor a la base de datos, verificando que no exista otro con la misma cédula.
@app.post("/agregar")
def agregar(
    cedula: str = Form(...), nombre: str = Form(...), apellido: str = Form(...),
    telefono: str = Form(...), nombre_emprendimiento: str = Form(...) ,nacionalidad: str = Form(...) , 
    sector: str = Form(...), rubro: str = Form(...), comuna: str = Form(...),
    tiene_certificado: bool = Form(False), fecha_emision: str = Form(None)
):
    db = SessionLocal()
    if db.query(EmprendedorDB).filter(EmprendedorDB.cedula == cedula).first():
        db.close()
        return RedirectResponse(url="/dashboard?error=duplicado", status_code=status.HTTP_303_SEE_OTHER)
    
    fecha_obj = datetime.strptime(fecha_emision, "%Y-%m-%d").date() if fecha_emision else None
    nuevo = EmprendedorDB(
        cedula=cedula, nombre=nombre, apellido=apellido, telefono=telefono,
        nombre_emprendimiento=nombre_emprendimiento, nacionalidad=nacionalidad , 
        sector = sector , rubro= rubro ,tiene_certificado=tiene_certificado, comuna=comuna,
        fecha_emision=fecha_obj
    )
    db.add(nuevo)
    db.commit()
    db.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    
# Muestra la página dedicada al formulario de registro de nuevos emprendedores
@app.get("/registro", response_class=HTMLResponse)
def registro_page(request: Request):
    username = request.cookies.get("user_session")
    if not username:
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse(request, "registro.html", {
        "user": username
    })

# 1. Muestra el formulario con los datos prellenados
@app.get("/editar/{emprendedor_id}", response_class=HTMLResponse)
def editar_page(request: Request, emprendedor_id: int):
    username = request.cookies.get("user_session")
    if not username:
        return RedirectResponse(url="/")
        
    db = SessionLocal()
    emprendedor = db.query(EmprendedorDB).filter(EmprendedorDB.id == emprendedor_id).first()
    db.close()

    if not emprendedor:
        return RedirectResponse(url="/dashboard")

    return templates.TemplateResponse(request, "editar.html", {
        "user": username,
        "emp": emprendedor
    })



#Funcion para cerrar la sesion, eliminando la cookie de usuario y redirigiendo a la pagina de inicio de sesion.
@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="user_session")
    return response