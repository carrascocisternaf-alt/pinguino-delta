// Pingüino Delta compartido · guarda lo que publica el QF para que los colegas lo vean.
// La app es / (cargador que trae la versión publicada de Pingüino Delta).
// GET  /api/delta            -> índice: qué Excel hay publicados (nombre, fecha, etag) y la config compartida
// GET  /api/delta?k=consumos -> Excel único de consumos y programaciones (base64)
// GET  /api/delta?k=sapu     -> Excel de consumo diario SAPU (base64)
// GET  /api/delta?k=comp     -> configuración compartida (mín/máx SAPU, exclusivos, equivalencias, apertura)
// POST /api/delta            -> publica {k, nombre, b64} o {k:"comp", datos}  (requiere la clave DELTA_CLAVE)
// Los stocks NO se guardan aquí: Delta los lee de /api/inventario (las tres bodegas de Lotes).
import { getStore } from "@netlify/blobs";
import { createHash, timingSafeEqual } from "node:crypto";

// La clave NO va en el código (este repositorio es público): se define en Netlify →
// Site configuration → Environment variables → DELTA_CLAVE.
const CLAVE = process.env.DELTA_CLAVE || "";

const MAX_B64 = 4.5 * 1024 * 1024; // ~3,3 MB de Excel
const MAX_COMP = 2 * 1024 * 1024;
const ARCHIVOS = ["consumos", "sapu", "estado"];

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });

function claveOk(req) {
  const dada = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "").trim();
  if (!dada) return false;
  const esperada = CLAVE;
  if (!esperada) return false;
  const a = createHash("sha256").update(esperada).digest();
  const b = createHash("sha256").update(dada).digest();
  return timingSafeEqual(a, b);
}
const S = (v, n) => (typeof v === "string" ? v.slice(0, n) : "");
const etagDe = (s) => createHash("sha1").update(s).digest("hex").slice(0, 16);

export default async (req) => {
  const store = getStore({ name: "pinguino-delta", consistency: "strong" });
  const url = new URL(req.url);

  if (req.method === "GET") {
    const k = url.searchParams.get("k");
    if (!k) {
      const idx = (await store.get("indice", { type: "json" })) || { archivos: {}, comp: null };
      return json(idx);
    }
    if (ARCHIVOS.includes(k)) {
      const a = await store.get("arch_" + k, { type: "json" });
      return a ? json(a) : json({ error: "Aún no se ha publicado ese archivo." }, 404);
    }
    if (k === "comp") {
      const c = await store.get("comp", { type: "json" });
      return c ? json(c) : json({ error: "Sin configuración compartida." }, 404);
    }
    return json({ error: "Archivo no reconocido." }, 400);
  }

  if (req.method === "POST") {
    if (!CLAVE) return json({ error: "Falta definir DELTA_CLAVE en Netlify (Environment variables)." }, 500);
    if (!claveOk(req)) return json({ error: "Clave incorrecta." }, 401);
    const text = await req.text();
    if (text.length > MAX_B64 + 4096) return json({ error: "El archivo es demasiado grande (máx. ~3 MB)." }, 413);
    let body;
    try { body = JSON.parse(text); } catch (e) { return json({ error: "Formato inválido." }, 400); }
    const idx = (await store.get("indice", { type: "json" })) || { archivos: {}, comp: null };
    const ahora = new Date().toISOString();
    if (ARCHIVOS.includes(body.k)) {
      const b64 = S(body.b64, MAX_B64 + 1);
      if (!b64 || b64.length > MAX_B64 || !/^[A-Za-z0-9+/=]+$/.test(b64)) return json({ error: "Archivo inválido." }, 400);
      const meta = { nombre: S(body.nombre, 200) || body.k + ".xlsx", subido: ahora, por: S(body.por, 80), etag: etagDe(b64), tam: Math.round(b64.length * 0.75) };
      await store.setJSON("arch_" + body.k, { ...meta, b64 });
      idx.archivos[body.k] = meta;
      await store.setJSON("indice", idx);
      return json({ ok: true, meta });
    }
    if (body.k === "comp") {
      const datos = body.datos;
      if (!datos || typeof datos !== "object") return json({ error: "Datos inválidos." }, 400);
      const txt = JSON.stringify(datos);
      if (txt.length > MAX_COMP) return json({ error: "Configuración demasiado grande." }, 413);
      const comp = { ts: ahora, por: S(body.por, 80), etag: etagDe(txt), datos };
      await store.setJSON("comp", comp);
      idx.comp = { ts: ahora, por: comp.por, etag: comp.etag };
      await store.setJSON("indice", idx);
      return json({ ok: true, etag: comp.etag, ts: ahora });
    }
    return json({ error: "Archivo no reconocido." }, 400);
  }

  return json({ error: "Método no permitido." }, 405);
};

export const config = { path: "/api/delta" };
