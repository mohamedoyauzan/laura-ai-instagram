# IA GIRL — gestión autónoma de Laura

La cuenta de Instagram se autoriza con `instagram_oauth.py`. Las credenciales
se guardan únicamente en `.env`, que está excluido de Git.

## Comprobar la conexión

```powershell
python .\instagram_publish.py verify
```

## Operación diaria

El proyecto contiene un calendario inicial de 30 días en `content_plan.json`.
Cada lote genera un Reel vertical y una historia con la misma escena. La identidad
visual se toma siempre de `assets/lia-cute-v4.png`.

```powershell
python .\daily_manager.py next
python .\daily_manager.py prepare --image ".\ruta\a\la-imagen.png"
python .\daily_manager.py publish
```

`daily_manager.py` registra el estado antes de publicar. Si una ejecución se
interrumpe, el siguiente intento reanuda el lote preparado y evita duplicados.

## Métricas y comunidad

```powershell
python .\instagram_insights.py --limit 25
python .\instagram_comments.py scan --media-limit 12
python .\instagram_comments.py reply ID_COMENTARIO --message "Respuesta"
```

Las métricas se conservan en `analytics/latest.json` y
`analytics/history.jsonl`. El token se renueva automáticamente cada siete días
mediante `token_manager.py`.

## Perfiles separados

Las credenciales de cada cuenta permanecen en archivos ignorados por Git. Para
trabajar con Jordi se selecciona su perfil antes de ejecutar cualquier comando:

```powershell
$env:INSTAGRAM_ENV_FILE='.env.jordi'
python .\instagram_publish.py verify
```

Las diez fotos de lanzamiento de Jordi se preparan y encolan de forma repetible:

```powershell
python .\prepare_jordi_launch.py
python .\queue_jordi_launch.py
python .\publish_queue.py --batch-id jordi-launch-2026-10-22
```

La cola registra cada publicación al completarse para que un reintento no cree
duplicados.

## Publicación manual de una foto

Instagram necesita descargar la imagen desde una URL HTTPS pública:

```powershell
python .\instagram_publish.py photo `
  --image-url "https://ejemplo.com/foto.jpg" `
  --caption "Texto de la publicación"
```

## Publicar una historia

```powershell
python .\instagram_publish.py story `
  --image-url "https://ejemplo.com/historia.jpg"
```

## Publicar un Reel

```powershell
python .\instagram_publish.py reel `
  --video-url "https://ejemplo.com/reel.mp4" `
  --caption "Texto del Reel"
```

Ejecutar estos comandos crea una publicación real.

## Publicar la cola preparada

`publish_queue.py` abre un túnel HTTPS temporal mediante `localhost.run`,
publica todas las entradas pendientes de `publication_queue.json` y cierra el
túnel al terminar.

```powershell
python .\publish_queue.py --dry-run
python .\publish_queue.py
```

## Automatizaciones activas

- `Laura: contenido diario`: un Reel y una historia cada día a las 20:30.
- `Laura: comunidad y métricas`: comentarios y estadísticas a las 12:30.

Son automatizaciones locales sin coste de alojamiento. El ordenador y Codex
deben poder ejecutar la tarea; si están apagados, la ejecución tendrá que esperar
hasta que el entorno vuelva a estar disponible.

## Calendario autónomo de Jordi

Jordi usa una agenda independiente y cuatro horarios diarios en zona
`Europe/Madrid`: foto a las 10:00, Reel a las 12:00 e historias a las 13:00 y
15:00. El workflow de GitHub se despierta cada 15 minutos y el publicador decide
si hay una pieza vencida; nunca publica más de una pieza por ejecución.

```powershell
python .\prepare_jordi_automation.py
python .\jordi_automation.py status
python .\jordi_automation.py due --dry-run --now "2026-10-27T10:05:00+01:00"
```

Cada fuente debe superar una revisión visual registrada y un filtro técnico de
resolución, exposición, contraste, nitidez y recorte. Los derivados se validan
otra vez antes de publicarse. Las ejecuciones retrasadas más de tres horas se
marcan como caducadas para evitar ráfagas de publicaciones.

El workflow `.github/workflows/jordi-daily.yml` necesita dos secretos separados:
`JORDI_INSTAGRAM_ACCESS_TOKEN` y `JORDI_INSTAGRAM_USER_ID`. Nunca reutiliza los
secretos de Laura y verifica que la cuenta conectada sea exactamente
`jordi_fitt` antes de crear contenido.

La API de publicación de Instagram no permite seleccionar automáticamente
audio del catálogo de Reels. Los vídeos preparados usan pistas con licencia
incluidas en `assets/music/`; una tendencia del catálogo solo puede añadirse
manualmente desde la app de Instagram.

## Ejecución con el ordenador apagado

La carpeta `.github/workflows/` contiene una alternativa para GitHub Actions:

- `instagram-daily.yml` publica desde los servidores de GitHub a las 20:37.
- `instagram-metrics.yml` guarda las estadísticas a las 12:43.
- `cloud_publish.py` reanuda lotes parciales y evita volver a publicar un lote
  marcado como completado.
- `cloud_schedule.json` contiene las 29 fechas restantes del primer mes.

Para activarla se necesita un repositorio público con los medios de
`posts/cloud/` y dos GitHub Actions Secrets: `INSTAGRAM_ACCESS_TOKEN` e
`INSTAGRAM_USER_ID`. Las credenciales nunca deben añadirse al repositorio. El
repositorio público permite que Instagram descargue los medios; GitHub Actions
es gratuito para repositorios públicos con runners estándar. Esta modalidad
publica con el PC apagado, pero primero hay que pre-generar los 29 lotes y subir
el proyecto una vez.
