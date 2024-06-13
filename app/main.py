from flask import Flask, request, jsonify
import os
import io
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import re
import base64
from datetime import datetime, timedelta

app = Flask(__name__)
app.app_context().push()
CORS(app)
host = "/zambos-preparados"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")


db = SQLAlchemy(app)
ma = Marshmallow(app)
base = db.Model.metadata.reflect(db.engine)


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
        id_departamento,
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
        self.id_departamento = id_departamento
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
        plataforma,
        codigo,
        url,
        fecha_registro,
        fecha_eliminacion,
        estado,
        tipo,
    ):
        self.id_usuario = id_usuario
        self.url = url
        self.plataforma = plataforma  
        self.codigo = codigo
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
            "plataforma",
            "codigo,"
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
        usuario.fecha_activacion = datetime.now()
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
    if tipo == "identificacion":
        newdato = re.sub(r"[^A-Za-z-0-9]+", "", dato).upper()
    if tipo == "numerico":
        newdato = re.sub(r"     ", "", str(dato))
    return newdato


def validar_creacion_usuario(identificacion, telefono, correo, departamento):
    departamento_obj = Departamentos.query.filter_by(id=departamento).first()

    if not departamento_obj:
        return (
            jsonify(
                {
                    "error": "El registro no pudo ser completado, Este departamento no existe"
                }
            ),
            409,
        )

    pais_id = departamento_obj.id_pais

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
        return jsonify({"error": f"El teléfono no pertenece al país {pais_id}"}), 409

    if not re.match(identificacion_regex, str(identificacion)):
        return (
            jsonify({"error": f"La identificación no pertenece al país {pais_id}"}),
            409,
        )

    return False  # El usuario no existe, pasa la validación


def calcular_edad(identificacion):
    try:
        fecha_actual = datetime.now()
        anio_actual = fecha_actual.year
        # Tomar los dos últimos dígitos del año de nacimiento
        anio_nacimiento = int(identificacion[7:9])

        # Asumir que el año de nacimiento es del siglo pasado si es mayor a la edad actual
        if anio_nacimiento > anio_actual % 100:
            anio_nacimiento += 1900
        else:
            anio_nacimiento += 2000

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
        fecha_registro = datetime.now()
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

        validacion = validar_creacion_usuario(
            identificacion, telefono, correo, departamento
        )
        if not validacion:
            token = generate_token(correo)
            nuevo_usurio = Usuarios(
                nombre=nombre, apellido=apellido,identificacion=identificacion,correo=correo,telefono=telefono,genero=genero,edad=edad,id_departamento=departamento,token=token,ip_address=ip_address,utms=utms,fecha_registro=fecha_registro,tipo_usuario=tipo_usuario,estado=estado
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
        fecha_registro = datetime.now()
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
            depa = Departamentos.query.filter_by(id=user.id_departamento).first()
            if not depa:
                return (
                    jsonify({"message": "El usuario no tiene un departamento valido"}),
                    404,
                )

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
                        "departamento": depa.id,
                        "departamento_name": depa.nombre
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





@app.route(host + "/new_galeria", methods=["POST"])
def new_total_Galeria():
    try:
        data = request.get_json()

        id_usuario = request.json["id_usuario"]
        plataforma = request.json["plataforma"]
        codigo = request.json["codigo"]
        url = request.json["url"]
        tipo = request.json["tipo"]
        fecha_registro = datetime.now()
        estado = 1
        fecha_eliminacion = None

        if not all(
            [
                id_usuario,
                plataforma,
                codigo,
                url,
                tipo,
            ]
        ):
            return (
                jsonify(
                    {"error": "El registro no pudo ser completado campos incompletos "}
                ),
                400,
            )
        nueva_galeria = Galeria(id_usuario=id_usuario,plataforma=plataforma,codigo=codigo,url=url,fecha_registro=fecha_registro, estado=estado, fecha_eliminacion=fecha_eliminacion, tipo=tipo)
        db.session.add(nueva_galeria)
        db.session.commit()
        return (
            jsonify(
                {
                    "message": "Datos ingresados exitosamente"
                }
            ),
            201,
        ) 
            
    except Exception as e:
        return jsonify(message="Error en la solicitud"), 500







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
                    "plataforma": g.plataforma,
                    "codigo": g.codigo,
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
    try:
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
            # Filtrar por rango de fechas si se proporcionan ambas fechas
            base_query = base_query.filter(
                Galeria.fecha_publicacion.between(fecha_inicio, fecha_fin)
            )

        galery = base_query.paginate(page=page, per_page=per_page)

        if galery.items:
            galeria_data = []
            print(galery.items)

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
                        "plataforma": g.plataforma,
                        "codigo": g.codigo
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

    except Exception as e:
        return jsonify(message="No hay resultados"), 404


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
            existing_vote.fecha_modificacion = datetime.now()
        else:
            nueva_votacion = Votaciones(
                id_galeria=id_galeria,
                id_usuario=usuario_token.id,
                fecha_registro=datetime.now(),
                estado=1,
                fecha_modificacion=None,
            )
            db.session.add(nueva_votacion)

    elif estado == 0:
        if existing_vote:
            existing_vote.estado = 0
            existing_vote.fecha_modificacion = datetime.now()

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
                        "plataforma": galeria.plataforma,
                        "codigo": galeria.codigo

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




@app.route(host + "/galeria_usuario_publica/<id_token>", methods=["GET"])
def get_galeria_usuario_publica(id_token):
    try:
        user_id = get_id_by_token(id_token)
        print(user_id)
        current_user = Usuarios.query.filter_by(correo=user_id).first()
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

            for galeria in galerias:
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
                        "plataforma": galeria.plataforma,
                        "codigo": galeria.codigo
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5199)
