# 🐍 Python - Rest API Zambos preparados

Esta es una documentación para la API REST de Zambos preparados en Python, que se ejecuta dentro de un contenedor Docker.

## 💻 Instalación

Para ejecutar este proyecto, sigue los siguientes pasos:

### Clonar el Repositorio

Clona el repositorio de GitHub en tu máquina local:

```bash
git clone [https://github.com/oscarwol/zambos_preparados_2024](https://github.com/oscarwol/zambos_preparados_2024)
cd zambos_preparados_2024
```

### Configurar la Base de Datos

Este proyecto utiliza SQLAlchemy como un ORM para Flask. Al ejecutar el proyecto, todos los modelos se migrarán automáticamente a la base de datos configurada. No es necesario crear la base de datos manualmente.

Para configurar la base de datos, abre el archivo `Docker-compose.yml` y configura la URL de la base de datos siguiendo el formato:

```yaml
"DATABASE_URL=mysql+pymysql://usuario:contraseña@servidor:puerto/base_de_datos"
```

Asegúrate de seguir la nomenclatura de datos proporcionada a continuación:

- Usuario: sql3506490
- Contraseña: tb9TZcCU7W
- Servidor: sql3.freemysqlhosting.net
- Base de datos: sql3506490

## 🚀 Iniciar el Proyecto

Una vez que hayas clonado el repositorio y configurado la base de datos en el archivo `Docker-compose.yml`, puedes iniciar el proyecto ejecutando el siguiente comando:

```bash
docker-compose up --build
```
Esto iniciará la aplicación en un contenedor Docker y estará disponible para su uso.

## ⚙️ Uso:
https://apiswolgroup.com/zambos-preparados (Para Prod)

localhost:5199 (Local)



| HTTP Type | Path | Used For |
| --- | --- | --- |
| `POST` | /login | Endpoint para autenticar y logear al usuario, una autenticación exitosa retornara los datos del usuario y un token|
| `POST` | /login_visita | Endpoint para autenticar y logear al usuario de visita|
| `POST` | /register | Nos permite registrar un nuevo usuario en el sistema, retorna un token |
| `POST` | /register_visita | Endpoint para registrar al usuario de visita|
| `GET` | /departamento | Retorna el listado total de los departamentos registrados|
| `POST` | /new_galeria | Sube una nueva foto al sistema, la guarda en la base de datos  |
| `POST` | /galeria | Obtiene los elementos con aprobacion, en estado activo y retorna su conteo de votaciones, además si el usuario logeado ya votó por esta foto o no.|
| `GET` | /galeria_usuario/<int:user_id> | Obtiene las fotos en estado activo de un usuario en especifico|
| `POST` | /votar | Permite sumar o restar una votación a una id_Galeria específica, cada usuario puede votar una única vez y la suma o resta dependerá del estado que se envie|


#### Endpoint Login [/login]
```http
POST /zambos-preparados/login/
```

Ejemplos de datos a enviar:
```
{
  "identificacion": "29999999999",
  "correo": "omorales@wol.group"
}
```
---


### Endpoint Register: [/register]
```http
POST /zambos-preparados/register/
```

Ejemplos de datos a enviar:
```
{
    "nombre": "Juan",
    "apellido": "Pérez",
    "identificacion": "2269696300109",
    "correo": "juan.perez@example.com",
    "telefono": "55551234",
    "genero": "Masculino",
    "departamento": 1,
    "ip": "192.168.1.1",
    "utms": "utm_source=google&utm_medium=cpc"
}

```
---

#### Endpoint new_galeria [/zambos-preparados/new_galeria] (Subir foto a Galeria)
```http
POST /zambos-preparados/new_galeria/
```

Ejemplos de datos a enviar (Debe ser un POST):
```
{
    "id_usuario": 30475,
    "plataforma": "Instagram",
    "codigo": "C48ybrQv5QH/",
    "url": "https://www.instagram.com/reel/C48ybrQv5QH/",
    "tipo": "reel"
}
```
```

---

#### Endpoint Galeria [/zambos-preparados/galeria] (Galeria)
```http
POST /zambos-preparados/galeria/
```
Filtros opcionales que se pueden utilizar en este endpoint:
- "page" (opcional, si no se incluye muestra por default la página 1)
- "per_page" (opcional, si no se incluye muestra por default 9 elementos por cada página)
- "fecha_inicio" y "fecha_fin" (opcional, si no se incluye muestra todas las fechas)
- "token" (obligatorio, debe ir vacio "" si el usuario no está logeado y con el token del usuario si ya inició sesión )


Sin filtros y de manera general, el request puede ser enviado de esta forma:
```
{
    "page": 1,
    "token": ""
}
```

Si el usuario esta logeado debe enviarse de esta forma:
```
{
    "page": 1,
    "token": "b21vcmFsZXNAb2RkLmRpZ2l0YWw="
}
```
Los filtros son opcionales, asi que pueden añadirse y funcionarán de manera independiente
```
{
    "page": 1,
    "per_page": 10,
    "fecha_inicio": "2023-10-10",
    "fecha_fin": "2023-10-12",
    "token": "b21vcmFsZXNAb2RkLmRpZ2l0YWw="
}
```

Este endpoint también permite ver resultados específicos por cada página
```
{
    "page": 1,
    "per_page": 2,
    "token": "b21vcmFsZXNAb2RkLmRpZ2l0YWw="
}
```
---

#### Endpoint de Votación [/zambos-preparados/votar] 
```http
POST /zambos-preparados/votar/
```
Significados del valor de 'estado'
- 0: Quitar votación (deshabilitar) votación
- 1: Agregar o (habilitar) votación.
Ejemplos de datos a enviar:
```
{
    "id_galeria": 5412,
    "token": "b21vcmFsZXNAb2RkLmRpZ2l0YWw=",
    "estado: 1
}
```
---

