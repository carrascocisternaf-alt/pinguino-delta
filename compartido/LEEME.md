# Pingüino Delta compartido (link propio para los colegas)

Sitio aparte de Lotes. Tú cargas tus Excel en Delta desde este link (con la clave guardada en tu PC) y se publican solos; los colegas abren el link y ven lo mismo, sin cargar nada. Sin internet, abre con la última copia. La página es la versión publicada de Delta, así que se actualiza sola.

## Crear el sitio en Netlify (una vez, ~5 minutos)

1. Netlify → **Add new site → Import an existing project → GitHub** → elige `pinguino-delta`.
2. En la configuración del sitio:
   - **Base directory:** `compartido`
   - **Publish directory:** `compartido/public` (Netlify lo completa solo desde `netlify.toml`)
   - **Build command:** dejar vacío.
3. **Environment variables → Add a variable:** `DELTA_CLAVE` = la clave que usarás para publicar (no se guarda en GitHub).
4. **Deploy**. Luego **Site configuration → Change site name** → p. ej. `delta-desam-limache`.

Link para los colegas: `https://delta-desam-limache.netlify.app/`

## Uso

- En tu PC: barra azul → **🔑 Publicar desde este PC** → clave, tu nombre, «Publicar automáticamente» → Guardar. Desde ahí, todo lo que cargues en Delta en ese link se publica solo.
- Colegas: solo abren el link (botón 🔄 Actualizar para traer lo último).

`public/index.html` (cargador con la configuración) · `netlify/functions/delta.mjs` (guarda lo publicado en Netlify Blobs; lectura abierta, escritura con `DELTA_CLAVE`).
