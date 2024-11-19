from flask import Flask, request, jsonify
from google.cloud import vision
import os
from PIL import Image
import io
import base64
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import re
import base64
from datetime import datetime, timedelta
import requests
from werkzeug.utils import secure_filename
import gspread
import tinify  # TinyPNG module
from google.oauth2.service_account import Credentials
import schedule
import time
from datetime import datetime
import threading



app = Flask(__name__)
app.app_context().push()
CORS(app)
host = "/zambos-preparados"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

# Carpeta donde almacenar las imágenes
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Asegúrate de que la carpeta existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    
db = SQLAlchemy(app)
ma = Marshmallow(app)
base = db.Model.metadata.reflect(db.engine)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

tinify.key = "HSxvJcJyDw5zMMWJzC8s77XgrRzBFMVR"

class Usuarios(db.Model):
    __table__ = db.Model.metadata.tables["usuarios"]

    def __init__(
        self,
        nombre,
        apellido,
        identificacion,
        correo,
        telefono,
        genero,
        edad,
        departamento,
        token,
        ip_address,
        utms,        
        fecha_registro,
        tipo_usuario,
        estado,
    ):
        self.nombre = nombre
        self.apellido = apellido
        self.identificacion = identificacion
        self.correo = correo
        self.telefono = telefono
        self.genero = genero
        self.edad = edad
        self.departamento = departamento
        self.token = token
        self.utms = utms
        self.ip_address = ip_address
        self.fecha_registro = fecha_registro
        self.estado = estado
        self.tipo_usuario = tipo_usuario

    def tiene_votaciones_para_galeria(self, id_galeria):
        return (
            Votaciones.query.filter_by(
                id_usuario=self.id, id_galeria=id_galeria, estado=1
            ).first()
            is not None
        )


class Galeria(db.Model):
    __table__ = db.Model.metadata.tables["galeria"]

    def __init__(
        self,
        id_usuario,
        url,
        fecha_registro,
        fecha_eliminacion,
        estado,
        tipo,
    ):
        self.id_usuario = id_usuario
        self.url = url
        self.fecha_registro = fecha_registro
        self.fecha_eliminacion = fecha_eliminacion
        self.estado = estado,
        self.tipo = tipo,


class Votaciones(db.Model):
    __table__ = db.Model.metadata.tables["votaciones"]

    def __init__(
        self, id_galeria, id_usuario, fecha_registro, fecha_modificacion, estado
    ):
        self.id_galeria = id_galeria
        self.id_usuario = id_usuario
        self.fecha_registro = fecha_registro
        self.fecha_modificacion = fecha_modificacion
        self.estado = estado

    @classmethod
    def count_votaciones_for_galeria(cls, id_galeria):
        return cls.query.filter_by(id_galeria=id_galeria, estado=1).count()



class Departamentos(db.Model):
    __table__ = db.Model.metadata.tables["departamentos"]

    def __init__(self, nombre, id_pais, estado):
        self.nombre = nombre
        self.id_pais = id_pais
        self.estado = estado


class Galeria_Schema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "id_usuario",
            "url",
            "fecha_publicacion",
            "estado",
            "tipo"
        )


galeria_schema = Galeria_Schema()
galeria_schemas = Galeria_Schema(many=True)

class Departamentos_Schema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "nombre",
            "id_pais",
            "estado",
        )


depa_schema = Departamentos_Schema()
depa_schemas = Departamentos_Schema(many=True)


def verificar_estado_activacion(correo):
    return (
        True
        if Usuarios.query.filter(Usuarios.correo == correo).first().estado == 1
        else False
    )


@app.route(host + "/activar/<token>", methods=["GET"])
def activar_token_usuario(token):
    usuario = Usuarios.query.filter(Usuarios.token == token).first()
    if usuario:
        if verificar_estado_activacion(usuario.correo):
            return "Este usuario ya fue activado previamente", 404
        usuario.fecha_activacion = datetime.now() - timedelta(hours=6)
        usuario.estado = 1
        db.session.commit()
        return f"Usuario {usuario.correo} activado correctamente", 200
    return "El token Ingresado no es válido", 404


def generate_token(texto):
    string_bytes = texto.encode("ascii")
    base64_bytes = base64.b64encode(string_bytes)
    # sxa = base64.b64decode(base64_bytes).decode("ascii")
    return base64_bytes.decode("ascii")


def get_id_by_token(id_token):
    try:
        return base64.b64decode(id_token).decode("ascii")
    except:
        return -1

def validar_dato(dato, tipo):
    if tipo == "nombre":
        newdato = re.sub(r"[^A-Za-z-ÁáÉéÍíÓóÚúñÑ ]", "", dato).upper()
        newdato = re.sub(r'\s+', ' ', newdato).rstrip()
    if tipo == "identificacion":
        newdato = re.sub(r"[^A-Za-z-0-9]+", "", dato).upper()
    if tipo == "numerico":
        newdato = re.sub(r"     ", "", str(dato))
    return newdato


def validar_creacion_usuario(identificacion, telefono, correo, departamento):
    # Verificar si la identificación ya está en uso
    user_by_identificacion = Usuarios.query.filter_by(
        identificacion=identificacion
    ).first()
    if user_by_identificacion:
        return (
            jsonify(
                {
                    "error": "El registro no pudo ser completado, esta identificación ya está en uso."
                }
            ),
            409,
        )

    # Verificar si el correo electrónico ya está en uso
    if Usuarios.query.filter_by(correo=correo).first():
        return (
            jsonify(
                {
                    "error": "El registro no pudo ser completado, este correo ya está en uso."
                }
            ),
            409,
        )

    user_by_telefono = Usuarios.query.filter_by(telefono=telefono).first()
    if user_by_telefono:
        return (
            jsonify(
                {
                    "error": "El registro no pudo ser completado, este telefono ya está en uso."
                }
            ),
            409,
        )

    telefono_regex = r"^\d{8}$"
    identificacion_regex = r"^[0-9]{13}$"


    # Validar teléfono y identificación según el país
    if not re.match(telefono_regex, str(telefono)):
        return jsonify({"error": f"El teléfono no pertenece al país"}), 409

    if not re.match(identificacion_regex, str(identificacion)):
        return (
            jsonify({"error": f"La identificación no pertenece al país"}),
            409,
        )

    return False  # El usuario no existe, pasa la validación



def calcular_edad(identificacion):
    try:
        # Extraer el año de nacimiento de la identificación
        anio_nacimiento = int(identificacion[4:8])

        # Obtener el año actual
        fecha_actual = datetime.now()
        anio_actual = fecha_actual.year

        # Calcular la edad
        edad = anio_actual - anio_nacimiento

        return edad
    except:
        return 0

@app.route(host + "/register", methods=["POST"])
def nuevo_usuario():
    try:
        nombre = str(validar_dato(request.json["nombre"], "nombre")).upper()
        apellido = str(validar_dato(request.json["apellido"], "nombre")).upper()
        identificacion = validar_dato(request.json["identificacion"], "identificacion")
        correo = str(request.json["correo"]).lower()
        telefono = int(validar_dato(request.json["telefono"], "numerico"))
        departamento = request.json["departamento"]
        utms = request.json["utms"]
        genero = request.json["genero"]
        edad = calcular_edad(identificacion)
        ip_address = request.json["ip"]
        fecha_registro = datetime.now() - timedelta(hours=6)
        estado = 1
        tipo_usuario = 1

        if not all(
            [
                nombre,
                apellido,
                identificacion,
                correo,
                telefono,
                departamento,
                genero,
                edad,
            ]
        ):
            return (
                jsonify(
                    {"error": "El registro no pudo ser completado campos incompletos "}
                ),
                400,
            )
            
        if edad < 18:
            return (
                    jsonify(
                        {"error": "El registro no pudo ser completado porque el usuario es menor de edad"}
                    ),
                    400,
                )

        validacion = validar_creacion_usuario(
            identificacion, telefono, correo, departamento
        )
        if not validacion:
            token = generate_token(correo)
            nuevo_usurio = Usuarios(
                nombre=nombre, apellido=apellido,identificacion=identificacion,correo=correo,telefono=telefono,genero=genero,edad=edad,departamento=departamento,token=token,ip_address=ip_address,utms=utms,fecha_registro=fecha_registro,tipo_usuario=tipo_usuario,estado=estado
            )
            db.session.add(nuevo_usurio)
            db.session.commit()
            return (
                jsonify(
                    {
                        "message": "Datos de usuario ingresados exitosamente",
                        "token": nuevo_usurio.token,
                    }
                ),
                201,
            )
        else:
            return validacion
    except KeyError as e:
        response = jsonify(
            {
                "error": "El registro no pudo ser completado, hace falta el campo: "
                + str(e)
            }
        )
        response.status_code = 400
        return response
    except Exception as ex:
        response = jsonify(
            {"error": "El registro no pudo ser completado, intenta nuevamente. Error: " + str(ex)}
        )
        response.status_code = 500
        return response



@app.route(host + "/register_visita", methods=["POST"])
def nuevo_usuario_visitante():
    try:
        nombre = str(validar_dato(request.json["nombre"], "nombre")).upper()
        apellido = str(validar_dato(request.json["apellido"], "nombre")).upper()
        correo = str(request.json["correo"]).lower()
        utms = request.json["utms"]

        telefono = None
        departamento = None
        genero = None
        edad = None
        fecha_registro = datetime.now() - timedelta(hours=6)
        estado = 1
        identificacion = None
        ip_address = request.json["ip"]
        tipo_usuario = 2

        if not all(
            [
                nombre,
                apellido,
                correo,
            ]
        ):
            return (
                jsonify(
                    {"error": "El registro no pudo ser completado campos incompletos "}
                ),
                400,
            )

        if Usuarios.query.filter_by(correo=correo).first():
            return (
                jsonify(
                    {
                        "error": "El registro no pudo ser completado, este correo ya está en uso."
                    }
                ),
                409,
            )
            
        else:
            token = generate_token(correo)
            nuevo_usurio = Usuarios(
                nombre=nombre, apellido=apellido,identificacion=identificacion,correo=correo,telefono=telefono,genero=genero,edad=edad,id_departamento=departamento,token=token,ip_address=ip_address,utms=utms,fecha_registro=fecha_registro,tipo_usuario=tipo_usuario,estado=estado
            )
            db.session.add(nuevo_usurio)
            db.session.commit()
            return (
                jsonify(
                    {
                        "message": "Datos de usuario visitante ingresados exitosamente",
                        "token": nuevo_usurio.token,
                    }
                ),
                201,
            )

    except KeyError as e:
        response = jsonify(
            {
                "error": "El registro no pudo ser completado, hace falta el campo "
                + str(e)
            }
        )
        response.status_code = 400
        return response
    except Exception as ex:
        response = jsonify(
            {"error": "El registro no pudo ser completado, intenta nuevamente. Error: " + str(ex)}
        )
        response.status_code = 500
        return response


@app.route(host + "/login_visita", methods=["POST"])
def login_visita():
    if True:
        correo = request.json["correo"]
        if not correo:
            return jsonify({"error": "Campos incompletos "}), 400

        user = Usuarios.query.filter_by(correo=correo, estado=1, tipo_usuario=2
        ).first()
        if user:
            response = jsonify(
                {
                    "mensaje": "Login exitoso",
                    "datos": {
                        "id": user.id,
                        "nombre": user.nombre,
                        "apellido": user.apellido,
                        "correo": user.correo,
                        "token": user.token,
                        "estado": user.estado,
                        "tipo_usuario": user.tipo_usuario
                }
                }
            )
            return response, 200

        return jsonify({"message": "El usuario no fue encontrado"}), 404
    # except:
    #     return jsonify({"message": "Ocurrió un error durante el login, intentalo más tarde"}), 500



@app.route(host + "/departamentos", methods=["GET"])
def get_departamentos():
    pais_param = request.args.get("pais")
    depas = None

    if pais_param:
        depas = Departamentos.query.filter_by(id_pais=pais_param).all()
    else:
        depas = Departamentos.query.all()

    if depas:
        return depa_schemas.jsonify(depas), 200
    return "No hay resultados", 404


@app.route(host + "/login", methods=["POST"])
def login():
    if True:
        identificacion = request.json["identificacion"]
        correo = request.json["correo"]
        if not all([identificacion, correo]):
            return jsonify({"error": "Campos incompletos "}), 400
        if identificacion == None:
            return jsonify({"error": "Usuario no encontrado "}), 400 

        user = Usuarios.query.filter_by(
            identificacion=identificacion, correo=correo
        ).first()
        if user:
            response = jsonify(
                {
                    "mensaje": "Login exitoso",
                    "datos": {
                        "id": user.id,
                        "nombre": user.nombre,
                        "apellido": user.apellido,
                        "identificacion": user.identificacion,
                        "correo": user.correo,
                        "token": user.token,
                        "activado": verificar_estado_activacion(user.correo),
                        "estado": user.estado,
                        "telefono": user.telefono,
                        "genero": user.genero,
                        "edad": user.edad,
                        "departamento": user.departamento,
                        },
                }
            )
            return response, 200

        return jsonify({"message": "El usuario no fue encontrado"}), 404
    # except:
    #     return jsonify({"message": "Ocurrió un error durante el login, intentalo más tarde"}), 500



# Endpoint para verificar si un token esta activo y/o valido
@app.route(host + "/active/<token>", methods=["GET"])
def is_active(token):
    try:
        user = Usuarios.query.filter_by(token=token).first()
        if user:
            if user.estado == 2:
                return jsonify({"message": "El usuario esta desactivado"}), 409

            depa = Departamentos.query.filter_by(id=user.id_departamento).first()
            if not depa:
                return (
                    jsonify({"message": "El usuario no tiene un departamento valido"}),
                    404,
                )

            datos = {
                "mensaje": "Token valido",
                "datos": {
                    "id": user.id,
                    "nombre": user.nombre,
                    "apellido": user.apellido,
                    "identificacion": user.identificacion,
                    "correo": user.correo,
                    "token": user.token,
                    "activado": verificar_estado_activacion(user.correo),
                    "estado": user.estado,
                    "telefono": user.telefono,
                    "genero": user.genero,
                    "edad": user.edad,
                    "departamento": depa.id,
                    "departamento_name": depa.nombre                },
            }
            return datos
        return jsonify({"message": "Usuario no existe"}), 404

    except:
        return jsonify({"message": "Token no valido"}), 401




def is_shortened_url(url):
    original_url_pattern = re.compile(r'^https://www\.tiktok\.com/@[^/]+/video/\d+$')
    # Si la URL no coincide con el patrón de la URL original, se considera acortada
    return not original_url_pattern.match(url)

def expand_url(short_url):
    try:
        response = requests.get(short_url, allow_redirects=True)
        return response.url
    except requests.RequestException as e:
        print(f"Error al expandir la URL: {e}")
        return short_url

def extract_video_id(expanded_url):
    # Expresión regular para capturar el video_id de una URL expandida de TikTok
    match = re.search(r'https://www\.tiktok\.com/@[^/]+/video/(\d+)', expanded_url)
    if match:
        return match.group(1)
    return None


@app.route(host + "/new_image", methods=["POST"])
def detect_image():
    id_usuario = request.form.get("id_usuario")
    tipo = request.form.get("tipo")
    fecha_registro = datetime.now() - timedelta(hours=6)
    fecha_eliminacion = None

    if not all([id_usuario, tipo]):
        return (
            jsonify(
                {"error": "El registro no pudo ser completado, campos incompletos"}
            ),
            400,
        )

    current_user = Usuarios.query.filter(Usuarios.id == id_usuario).first()
    if not current_user or not verificar_estado_activacion(current_user.correo):
        return jsonify({"error": "Este usuario no existe o está deshabilitado"}), 401

    image_file = request.files.get("image")

    if not image_file:
        return jsonify({"error": "No se proporcionó un archivo de imagen"}), 400

    # Optimize image with Tinify
    try:
        cnt = image_file.read()
        source = tinify.from_buffer(cnt).to_buffer()
        image_content = source
        if image_content is None:
            return jsonify({"error": "Error al comprimir la imagen"}), 500
    except tinify.Error as e:
        return jsonify({"error": f"Error al comprimir la imagen: {str(e)}"}), 500

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_content)

    # Detección de etiquetas (Label Detection)
    labels_response = client.label_detection(image=image)
    labels = labels_response.label_annotations

    # Lista de etiquetas relacionadas con comida
    food_labels = ["food", "dish", "meal", "drink", "beverage", "fruit", "vegetable", "recipe", "ingredient"]

    actions = []
    detected_labels = []
    food_detected = False

    # Comprobar si alguna de las etiquetas está relacionada con comida
    for label in labels:
        label_description = label.description.lower()
        detected_labels.append(label_description)  # Guardar las etiquetas detectadas

        # Si alguna etiqueta se relaciona con comida, marcamos food_detected como True
        if any(food in label_description for food in food_labels):
            food_detected = True
        else:
            actions.append(f"Imagen contiene {label_description}")

    # Si se detecta comida, marcar estado 1, de lo contrario estado 0
    if food_detected:
        estado = 1
    else:
        actions.append("La imagen no contiene comida")
        estado = 0

    # Detección de contenido seguro (SafeSearch)
    safe_search_response = client.safe_search_detection(image=image)
    safe_search = safe_search_response.safe_search_annotation

    # Mapea los valores de clasificación a términos más descriptivos
    safe_search_labels = {
        vision.Likelihood.UNKNOWN: "Desconocido",
        vision.Likelihood.VERY_UNLIKELY: "Muy improbable",
        vision.Likelihood.UNLIKELY: "Improbable",
        vision.Likelihood.POSSIBLE: "Posible",
        vision.Likelihood.LIKELY: "Probable",
        vision.Likelihood.VERY_LIKELY: "Muy probable",
    }

    classification = {
        "adulto": safe_search_labels[safe_search.adult],
        "engañoso": safe_search_labels[safe_search.spoof],
        "médico": safe_search_labels[safe_search.medical],
        "violencia": safe_search_labels[safe_search.violence],
        "picante": safe_search_labels[safe_search.racy],
    }

    # Acciones basadas en contenido no deseado
    if classification["adulto"] in ["Posible", "Probable", "Muy probable"]:
        actions.append("Imagen contiene contenido adulto")

    if classification["picante"] in ["Posible", "Probable", "Muy probable"]:
        actions.append("Imagen contiene contenido picante")

    if classification["violencia"] in ["Posible", "Probable", "Muy probable"]:
        actions.append("Imagen contiene contenido violento")

    url = (
        str(id_usuario)
        + "_"
        + "_"
        + str(datetime.now().strftime("%Y%m%d_%H%M%S"))
        + ".jpg"
    )

    # Convertir la imagen a base64 sin guardarla en el servidor
    img = Image.open(io.BytesIO(image_content))
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)
    img_base64 = base64.b64encode(img_byte_array.read()).decode('utf-8')

    # Guardar en la base de datos
    nueva_galeria = Galeria(
        id_usuario=id_usuario, 
        url=url, 
        fecha_registro=fecha_registro, 
        estado=estado, 
        fecha_eliminacion=fecha_eliminacion, 
        tipo=tipo
    )
    db.session.add(nueva_galeria)
    db.session.commit()

    # Respuesta JSON con las etiquetas detectadas y las acciones
    return jsonify(
        {
            "image_base64": img_base64,
            'tipo': tipo,
            "actions": actions,
            "detected_labels": detected_labels,  # Etiquetas detectadas
            "url": url,
            "message": "Imagen procesada correctamente en base64",
        }
    )


@app.route(host + "/galeria_admin", methods=["GET"])
def get_total_Galeria_admin():
    galery = Galeria.query.order_by(
        Galeria.fecha_registro.desc()
    ).filter(Galeria.estado != 1).all()  # Obtiene todos los elementos de Galeria

    if galery:
        galeria_data = []

        for g in galery:
            current_user = Usuarios.query.filter_by(id=g.id_usuario).first()
            galeria_data.append(
                {
                    "nombre_usuario": current_user.nombre,
                    "apellido_usuario": current_user.apellido,
                    "id": g.id,
                    "id_usuario": g.id_usuario,
                    "url": g.url,
                    "tipo": g.tipo,
                    "fecha_registro": g.fecha_registro,
                    "estado": g.estado,
                }
            )

        result = {
            "data": galeria_data,
        }
        return jsonify(result), 200

    return jsonify(message="No hay resultados"), 404

 
@app.route(host + "/galeria", methods=["POST"])
def get_total_Galeria():
    if True:
        data = request.get_json()

        # Leer parámetros del cuerpo JSON con valores predeterminados
        page = data.get("page", 1)
        per_page = data.get("per_page", 6)
        token = data.get("token", "")
        fecha_inicio = data.get("fecha_inicio", None)  # Nuevo filtro de fecha
        fecha_fin = data.get("fecha_fin", None)  # Nuevo filtro de fecha

        # Filtros iniciales: estado y aprobación_filtro
        base_query = Galeria.query.filter(
            Galeria.estado == 1
        ).order_by(Galeria.fecha_registro.desc())


        if fecha_inicio is not None and fecha_fin is not None:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1)
            
            # Filtrar por rango de fechas si se proporcionan ambas fechas
            base_query = base_query.filter(
                Galeria.fecha_registro.between(fecha_inicio_dt, fecha_fin_dt)
            )

        galery = base_query.paginate(page=page, per_page=per_page)

        if galery.items:
            galeria_data = []
            for g in galery.items:
                current_user = Usuarios.query.get(g.id_usuario)
                votaciones_galeria = Votaciones.count_votaciones_for_galeria(g.id)
                tiene_votaciones = False
                if token != "":
                    usuario_token = Usuarios.query.filter_by(token=token).first()
                    tiene_votaciones = usuario_token.tiene_votaciones_para_galeria(g.id)

                galeria_data.append(
                    {
                        "nombre_usuario": current_user.nombre,
                        "apellido_usuario": current_user.apellido,
                        "id": g.id,
                        "id_usuario": g.id_usuario,
                        "url": g.url,
                        "votaciones": votaciones_galeria,
                        "fecha_publicacion": g.fecha_registro,
                        "usuario_voto_logeado": tiene_votaciones,
                        "tipo": g.tipo,
                    }
                )

            result = {
                "data": galeria_data,
                "total_items": galery.total,
                "per_page": len(galeria_data),
                "page": galery.page,
            }

            if not galeria_data:
                return jsonify(message="No hay resultados"), 404

            return jsonify(result), 200

        return jsonify(message="No hay resultados"), 404

    # except Exception as e:
    #     return jsonify(message="No hay resultados"), 500


@app.route(host + "/votar", methods=["POST"])
def votar():
    data = request.get_json()
    token = data.get("token")
    id_galeria = data.get("id_galeria")
    estado = data.get("estado")

    if not all([token, id_galeria, estado in (0, 1)]):
        return jsonify({"message": "Datos de entrada incompletos o incorrectos."}), 400

    usuario_token = Usuarios.query.filter_by(token=token).first()
    galeria_foto = Galeria.query.filter_by(id=id_galeria).first()

    if not usuario_token or not galeria_foto:
        return jsonify({"message": "Datos de usuario o galería incorrectos."}), 404

    existing_vote = Votaciones.query.filter_by(
        id_usuario=usuario_token.id, id_galeria=id_galeria
    ).first()

    if estado == 1:
        if existing_vote:
            if existing_vote.estado == 1:
                return (
                    jsonify({"message": "El usuario ya ha votado por esta galería."}),
                    409,
                )
            existing_vote.estado = 1
            existing_vote.fecha_modificacion = datetime.now() - timedelta(hours=6)
        else:
            nueva_votacion = Votaciones(
                id_galeria=id_galeria,
                id_usuario=usuario_token.id,
                fecha_registro=datetime.now() - timedelta(hours=6),
                estado=1,
                fecha_modificacion=None,
            )
            db.session.add(nueva_votacion)

    elif estado == 0:
        if existing_vote:
            existing_vote.estado = 0
            existing_vote.fecha_modificacion = datetime.now() - timedelta(hours=6)

            db.session.commit()

            return jsonify({"message": "Se ha quitado la votación de esta foto."})

        else:
            return (
                jsonify({"message": "El usuario no ha votado por esta galería."}),
                404,
            )

    db.session.commit()

    return jsonify({"message": "Votación registrada correctamente."})



@app.route(host + "/galeria_usuario/<int:user_id>", methods=["GET"])
def get_galeria_usuario(user_id):
    try:
        galerias = (
            Galeria.query.filter(Galeria.id_usuario == user_id, Galeria.estado != 2)
            .order_by(Galeria.fecha_registro.desc())
            .all()
        )

        if galerias:
            galeria_data = []

            for galeria in galerias:
                current_user = Usuarios.query.filter_by(id=galeria.id_usuario).first()
                votaciones_galeria = Votaciones.count_votaciones_for_galeria(galeria.id)
                tiene_votaciones = current_user.tiene_votaciones_para_galeria(
                    galeria.id
                )

                galeria_data.append(
                    {
                        "id": galeria.id,
                        "id_usuario": galeria.id_usuario,
                        "url": galeria.url,
                        "fecha_registro": galeria.fecha_registro,
                        "estado": galeria.estado,
                        "votaciones": votaciones_galeria,
                        "usuario_voto_logeado": tiene_votaciones,
                        "tipo": galeria.tipo,
                    }
                )

            result = {"data": galeria_data}
            return jsonify(result), 200
        else:
            return (
                jsonify(
                    message="No se encontraron Galerías con estado diferente de 1 para este usuario."
                ),
                404,
            )

    except Exception as e:
        return jsonify(message="Error en la solicitud"), 500



@app.route(host + "/galeria_usuario_publica", methods=["POST"])
def get_galeria_usuario_publica():
    try:
        id_token = request.json["id_token"]
        usuario_id = request.json["usuario_id"]
        if not usuario_id:
            return (
                jsonify(
                    message="No se proporciono usuario"
                ),
                409,
            )
            
        if not usuario_id == -1:
            current_user_vista = Usuarios.query.filter_by(id=usuario_id).first()

        user_id = get_id_by_token(id_token)
        
        current_user = Usuarios.query.filter_by(id=user_id).first()
        if not current_user:
            return (
                jsonify(
                    message="No se encontró este usuario."
                ),
                404,
            )
            
        galerias = (
            Galeria.query.filter(Galeria.id_usuario == current_user.id, Galeria.estado == 1)
            .order_by(Galeria.fecha_registro.desc())
            .all()
        )

        if galerias:
            galeria_data = []
            user_data = []

            for galeria in galerias:
                votaciones_galeria = Votaciones.count_votaciones_for_galeria(galeria.id)
                if current_user_vista:
                    tiene_votaciones = current_user_vista.tiene_votaciones_para_galeria(
                        galeria.id
                    )
                else:
                    tiene_votaciones = False


                galeria_data.append(
                    {
                        "id": galeria.id,
                        "id_usuario": galeria.id_usuario,
                        "url": galeria.url,
                        "fecha_registro": galeria.fecha_registro,
                        "estado": galeria.estado,
                        "votaciones": votaciones_galeria,
                        "usuario_voto_logeado": tiene_votaciones,
                        "tipo": galeria.tipo,
                    }
                )


            user_data.append(
                    {"nombre": current_user.nombre,
                    "apellido": current_user.apellido,                    
                     }
                )
            result = {"data": galeria_data, "usuario": user_data}
            return jsonify(result), 200
        else:
            return (
                jsonify(
                    message="No se encontraron Galerías con estado diferente de 1 para este usuario."
                ),
                404,
            )

    except Exception as e:
        return jsonify(message="Error en la solicitud"), 500

@app.route(host + "/completar_register", methods=["POST"])
def completar_register_visita():
    try:

        nombre = str(validar_dato(request.json["nombre"], "nombre")).upper()
        apellido = str(validar_dato(request.json["apellido"], "nombre")).upper()
        identificacion = validar_dato(request.json["identificacion"], "identificacion")
        correo = str(request.json["correo"]).lower()
        telefono = int(validar_dato(request.json["telefono"], "numerico"))
        departamento = request.json["departamento"]
        genero = request.json["genero"]
        edad = calcular_edad(identificacion)
        ip_address = request.json["ip"]
        estado = 1
        tipo_usuario = 1
        

        if not all(
            [
                nombre,
                apellido,
                identificacion,
                correo,
                telefono,
                departamento,
                genero,
                edad,
            ]
        ):
            return (
                jsonify(
                    {"error": "El registro no pudo ser completado campos incompletos "}
                ),
                400,
            )
        if edad < 18:
            return (
                    jsonify(
                        {"error": "El registro no pudo ser completado porque el usuario es menor de edad"}
                    ),
                    400,
                )
            
        current_user = Usuarios.query.filter_by(correo=correo, estado=1, tipo_usuario=2
        ).first()
        if not current_user:
            return (
                jsonify(
                    {"error": "El registro no pudo ser completado, el usuario no es usuario visitante "}
                ),
                400,
            )


        validacion = validar_creacion_usuario(
            identificacion, telefono, "-1", departamento
        )
        if not validacion:
            current_user.nombre = nombre
            current_user.apellido = apellido
            current_user.telefono = telefono
            current_user.identificacion = identificacion
            current_user.id_departamento = departamento
            current_user.genero = genero
            current_user.edad = edad
            current_user.ip_address = ip_address
            current_user.estado = estado
            current_user.tipo_usuario = tipo_usuario
            db.session.commit()
            return (
                jsonify(
                    {
                        "message": "Datos de usuario actualizados exitosamente",
                        "token": current_user.token,
                    }
                ),
                201,
            )
        else:
            return validacion
    except KeyError as e:
        response = jsonify(
            {
                "error": "El registro no pudo ser completado, hace falta el campo "
                + str(e)
            }
        )
        response.status_code = 400
        return response
    except Exception as ex:
        response = jsonify(
            {"error": "El registro no pudo ser completado, intenta nuevamente. Error: " + str(ex)}
        )
        response.status_code = 500
        return response



@app.route(host + "/aprobar", methods=["POST"])
def aprobaciones():
    admin_token = "YWRtaW5AbW9zY2EuY29vbA=="
    data = request.get_json()
    id_galeria = data.get("id_galeria")
    aprobacion = data.get("aprobacion")
    token = data.get("token")
    # Validación de entrada
    if id_galeria is None or aprobacion is None:
        return jsonify({"message": "Datos de entrada incompletos."}), 400

    galeria_foto = Galeria.query.filter_by(id=id_galeria).first()
    if not galeria_foto:
        return jsonify({"message": "Datos de galeria incorrectos."}), 404
    if aprobacion == 0:
        if token != admin_token:
            return jsonify({"message": "Error de token"}), 400

        galeria_foto.estado = 0
        msg = f"Foto de galeria {galeria_foto.id} deshabilitada correctamente"
    elif aprobacion == 2:
        usuario_token = Usuarios.query.filter_by(token=token).first()
        if (usuario_token and galeria_foto.id_usuario == usuario_token.id) or token == admin_token :
            galeria_foto.estado = 2
            galeria_foto.fecha_eliminacion = datetime.now() - timedelta(hours=6)
            msg = f"Foto de galeria {galeria_foto.id} eliminada correctamente"
        else:
            return jsonify({"message": "Esta foto no pertenece a este usuario"}), 400

    else:
        if token != admin_token:
            return jsonify({"message": "Error de token"}), 400

        galeria_foto.estado = 1
        msg = f"Foto de galeria {galeria_foto.id} habilitada correctamente"

    db.session.commit()

    return jsonify({"message": msg}), 200


@app.route(host + "/registrar-reel", methods=["POST"])
def registrar_reel():
    data = request.get_json()
    nombre = data.get("nombre")
    apellido = data.get("apellido")
    instagram_link = data.get("instagram_link")

    if not all([nombre, apellido, instagram_link]):
        return jsonify({"message": "Datos de entrada incompletos."}), 400
    

    # Create a new user
    nuevo_usuario = Usuarios(
        nombre=nombre.upper(),
        apellido=apellido.upper(),
        identificacion=None,
        correo=None,
        telefono=None,
        genero=None,
        edad=None,
        departamento=None,
        token=None,
        ip_address=None,
        utms=None,
        fecha_registro=datetime.now() - timedelta(hours=6),
        tipo_usuario=4,
        estado=1,
    )
    db.session.add(nuevo_usuario)
    db.session.commit()

    # Add the Instagram link to the Galeria table
    nueva_galeria = Galeria(
        id_usuario=nuevo_usuario.id,
        url=instagram_link,
        fecha_registro=datetime.now() - timedelta(hours=6),
        fecha_eliminacion=None,
        estado=1,
        tipo="Instagram",
    )
    db.session.add(nueva_galeria)
    db.session.commit()

    return jsonify({"message": "Reel registrado correctamente.", "user_id": nuevo_usuario.id, "galeria_id": nueva_galeria.id}), 201


def spreadsheet_v2():
    with app.app_context(): 
        try:
            # Autenticación de Google Sheets
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file("key-spreadsheet.json", scopes=scopes)
            client = gspread.authorize(creds)

            # Acceso al Google Spreadsheet
            sheet_id = "1PygHsgkbDbQlW211MwhJ9j82GQ75Geh-vCrweTFn82U"
            workbook = client.open_by_key(sheet_id)
            sheet = workbook.get_worksheet(0)

            # Leer la cabecera desde la primera fila para usarla como claves
            header = sheet.row_values(1)
            
            # Obtener el último usuario de tipo 3 (Whatsapp) registrado en la base de datos
            ultimo_usuario = Usuarios.query.filter_by(tipo_usuario=3).order_by(Usuarios.fecha_registro.desc()).first()

            # Leer todas las filas de datos desde la segunda fila (saltando la cabecera)
            data = sheet.get_all_values()[1:]

            # Convertir las filas en un diccionario con base en la cabecera
            data_as_dict = [dict(zip(header, row)) for row in data]

            # Si no hay registros previos, incluir todos los registros
            if not ultimo_usuario:
                nuevos_registros = data_as_dict
            else:
                # Convertir fecha_registro a cadena en formato completo de fecha y hora para comparación
                last_user_date = ultimo_usuario.fecha_registro.strftime("%Y-%m-%d %H:%M:%S")
                last_user_email = ultimo_usuario.correo.strip()

                # Recorrer el spreadsheet desde el final hasta el inicio
                nuevos_registros = []
                for item in reversed(data_as_dict):
                    # Normalizar fecha y correo
                    fecha = item.get("Fecha de creación", "").strip()
                    correo = item.get("Email", "").strip()

                    # Normalizar las fechas para que tengan el mismo formato de 24 horas con ceros a la izquierda
                    normalized_fecha = normalize_date(fecha)
                    normalized_last_user_date = normalize_date(last_user_date)

                    # Si encontramos el último registro, dejamos de añadir elementos
                    if normalized_fecha == normalized_last_user_date and correo == last_user_email:
                        break
                    
                    # Agregar a nuevos_registros solo si no se encontró el último registro aún
                    nuevos_registros.insert(0, item)  # Añadir al inicio para mantener el orden

            # Preparar los datos para insertar en la base de datos
            data_db = [
                {
                    "nombre": item.get("Nombre del concursante", ""),
                    "apellido": " ",
                    "identificacion": item.get("Número de identificación", ""),
                    "correo": item.get("Email", ""),
                    "telefono": item.get("Número de teléfono del concursante", ""),
                    "genero": item.get("Género", ""),
                    "edad": item.get("Edad", ""),
                    "departamento": item.get("Departamento", ""),
                    "token": None,
                    "ip_address": None,
                    "utms": None,
                    "fecha_registro": item.get("Fecha de creación", ""),
                    "tipo_usuario": 3,
                    "estado": 1,
                    "img_url": item.get("URL de imagen adjunta", ""),
                }
                for item in nuevos_registros
            ]

            # Validar si el array data_db está vacío
            if not data_db:
                return jsonify({"message": "No hay nuevos registros para insertar."}), 200

            # Registrar los datos en la base de datos
            for item in data_db:
                nuevo_usurio = Usuarios(
                    nombre=item["nombre"],
                    apellido=item["apellido"],
                    identificacion=item["identificacion"],
                    correo=item["correo"],
                    telefono=item["telefono"],
                    genero=item["genero"],
                    edad=item["edad"],
                    departamento=item["departamento"],
                    token=item["token"],
                    ip_address=item["ip_address"],
                    utms=item["utms"],
                    fecha_registro=item["fecha_registro"],
                    tipo_usuario=item["tipo_usuario"],
                    estado=item["estado"],
                )
                db.session.add(nuevo_usurio)
                db.session.commit()

                # Guardar la imagen en la galería
                nueva_galeria = Galeria(
                    id_usuario=nuevo_usurio.id,
                    url=item["img_url"],
                    fecha_registro=datetime.now() - timedelta(hours=6),
                    fecha_eliminacion=None,
                    estado=1,
                    tipo="Whatsapp",
                )
                db.session.add(nueva_galeria)
                db.session.commit()

            return jsonify(data_db), 200

        except Exception as e:
            return jsonify({"message": str(e)}), 500

# Función para normalizar las fechas en formato "YYYY-MM-DD HH:MM:SS"
def normalize_date(date_str):
    try:
        # Intentamos convertir la fecha en un formato estandarizado
        normalized_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return normalized_date.strftime("%Y-%m-%d %H:%M:%S")  # Asegurarnos que tiene el formato esperado
    except ValueError:
        # Si la fecha no tiene el formato correcto, devolverla tal como está
        return date_str
    
schedule.every(1).hours.do(spreadsheet_v2)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)



if __name__ == "__main__":
    # Iniciar un hilo para ejecutar las tareas programadas
    schedule_thread = threading.Thread(target=run_schedule)
    schedule_thread.start()

    # Iniciar el servidor Flask
    app.run(host="0.0.0.0", debug=True, port=5199, use_reloader=False)



