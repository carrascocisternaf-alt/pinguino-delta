# Pingüino Delta · versión institucional (Microsoft 365)

Un link propio de la institución: cada colega entra con su cuenta Microsoft institucional y Delta:

- lee **directo de SharePoint/OneDrive** el Excel único de consumos y programaciones y el de consumo diario SAPU (solo los descarga de nuevo si cambiaron);
- guarda los **stocks cargados a mano** (botiquín, bodega central, SAPU, mín/máx, exclusivos SAPU, equivalencias) en un archivo `Pinguino_Delta_compartido.json` en OneDrive, para que **todos los PC con el link vean lo mismo**;
- **sin internet** abre con la última copia guardada en ese navegador;
- se puede **instalar** como app (opcional: en Chrome/Edge, ícono «Instalar» en la barra de direcciones).

Los datos no pasan por servidores de terceros: el navegador habla directo con Microsoft. Sin una cuenta de la institución con permiso sobre los archivos, el link muestra Delta vacío (como la versión abierta).

El `index.html` de esta carpeta es un **cargador**: trae la versión publicada de Delta (GitHub Pages), así que **se actualiza sola**, guarda una copia para abrir sin internet y le entrega la configuración de tu institución (bloque `CONFIG` al inicio del archivo). `sw.js`, `manifest.webmanifest` e `icono.svg` son opcionales: permiten abrir el link sin internet aunque se cierre el navegador e instalarlo como app.

---

## 1 · Para informática: registrar la aplicación en Entra ID (una vez, ~10 min)

1. Entra a <https://entra.microsoft.com> → **Identidad → Aplicaciones → Registros de aplicaciones → Nuevo registro**.
2. Nombre: `Pingüino Delta`. Tipos de cuenta: **Solo las cuentas de este directorio organizativo** (un solo inquilino).
3. URI de redirección: plataforma **Aplicación de página única (SPA)**, URL: `https://NOMBRE-DEL-SITIO.netlify.app/` (la que entregue el paso 2, con la barra final).
4. **Permisos de API → Agregar un permiso → Microsoft Graph → Permisos delegados**: `User.Read`, `Files.ReadWrite.All`, `offline_access`. Luego **Conceder consentimiento de administrador**.
   - `Files.ReadWrite.All` es delegado: la app solo puede abrir lo que el propio usuario ya puede abrir en SharePoint/OneDrive. La escritura se usa únicamente para el archivo de stocks compartidos.
5. Copia el **Id. de aplicación (cliente)** y entrégalo a quien administra Delta.

No se crea ningún secreto ni certificado (las apps de página única no lo usan).

## 2 · Publicar el sitio (Netlify, gratis)

1. Abre `index.html` con el Bloc de notas y, en el bloque `CONFIG`, pega el `clientId` del paso 1 (entre comillas) y revisa los vínculos. Guarda.
2. En Netlify → **Sites → Add new site → Deploy manually** arrastra la carpeta (o «browse to upload»). Basta con que suba `index.html`; si suben también `sw.js`, `manifest.webmanifest` e `icono.svg`, mejor.
3. En **Site configuration → Change site name** elige el nombre (p. ej. `delta-desam-limache`). Esa URL es la que va en el paso 1.3.
4. Para cambiar la configuración más adelante: edita `index.html` y en **Deploys** arrastra la carpeta de nuevo.

## 3 · SharePoint / OneDrive

- Comparte los dos Excel con **«Personas de tu organización»** (no «Cualquier persona»): así solo colegas con cuenta institucional pueden leerlos.
- Stocks compartidos: crea una carpeta (p. ej. `Delta - stocks`), compártela **con permiso de edición** con los colegas que cargan stocks (y de lectura con el resto), y pega su vínculo en `"carpeta"`. Si `"carpeta"` queda vacío, se usa la carpeta donde está el Excel de consumos.
- Quien solo tenga permiso de lectura ve todo, pero sus cargas de stock no se suben (la barra lo indica).

## Bloque CONFIG (en index.html)

| Campo | Qué es |
|---|---|
| `nombre` | Nombre que aparece en la barra y en la pestaña |
| `tenant` | Dominio de la institución (`desamlimache.cl`) o el Id. de inquilino |
| `dominio` | Dominio para sugerir la cuenta al iniciar sesión |
| `clientId` | Id. de aplicación del paso 1 |
| `consumos` | Vínculo al Excel único (columna *Origen*: «Consumo 2026», «CENABAST 2026», «Consumo SAPU 2026»…) |
| `sapu` | Vínculo al Excel de consumo diario SAPU (opcional) |
| `carpeta` | Vínculo a la carpeta de stocks compartidos (opcional) |

## Notas

- La sesión dura hasta ~24 h sin uso; después se vuelve a presionar «Entrar».
- Cuando varios cargan stock a la vez, queda la última carga (se muestra quién y cuándo).
- La copia local de Delta y el link abierto de GitHub siguen funcionando igual: sin configuración no se conectan a nada.
