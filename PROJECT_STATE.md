# Estado del proyecto IA GIRL

- Identidad visual maestra: `assets/lia-cute-v4.png`.
- Cuenta conectada: `laura_726362` (`29460271443573159`), tipo Business.
- El token permanece solamente en `.env`.
- Restricción visual: mantener la misma cara, ojos azules, pecas y cabello rubio;
  usar poses variadas y evitar que mire siempre al objetivo.
- Cola de publicaciones: `publication_queue.json`.
- Comando de publicación: `python .\publish_queue.py`.
- Autorización persistente del usuario: cuando diga **“publica”**, revisar las
  entradas pendientes y publicarlas directamente, sin pedir otra confirmación.
- Si el usuario encarga contenido nuevo para Instagram, generarlo, revisarlo y
  publicarlo directamente al terminar, salvo que indique expresamente que solo
  quiere una vista previa.
- Automatizaciones activas desde el 20-10-2026:
  - `Laura: contenido diario`, a las 20:30, genera, revisa y publica un Reel y
    una historia; usa `content_plan.json` y `daily_manager.py`.
  - `Laura: comunidad y métricas`, a las 12:30, revisa comentarios y actualiza
    `analytics/`.
- El token se renueva automáticamente cada siete días con `token_manager.py`.
- El sistema puede publicar fotos, Reels, historias de imagen e historias de vídeo.
- Plan editorial inicial de 30 días guardado en `content_plan.json`; al agotarse,
  la automatización debe ampliarlo usando las métricas observadas.
- El 20-10-2026 se publicaron diez fotos adicionales: Coliseo, Fontana di
  Trevi, Plaza de España de Roma, Panteón, Plaza de San Pedro, Sagrada Família,
  Park Güell, Barceloneta, Barrio Gótico y Arco de Triunfo de Barcelona.
- Mantener variedad de encuadres: primeros planos, planos generales, perfil,
  espalda y sujeto lejano; evitar repetir siempre la mirada a cámara.
- Presentar siempre a Laura como creadora virtual/IA en biografía, contenido o
  etiquetas. No afirmar encuentros ni experiencias físicas reales.
- Las automatizaciones de Codex son locales y no corren con el ordenador
  apagado. Se preparó la alternativa gratuita de GitHub Actions en
  `.github/workflows/`, junto con `cloud_publish.py` y `cloud_schedule.json`.
  Todavía requiere pre-generar los medios y conectar un repositorio una vez.
- El 20-10-2026 se publicó el primer Reel automático de París y su historia:
  https://www.instagram.com/reel/DeuxzYZE_Cq/
