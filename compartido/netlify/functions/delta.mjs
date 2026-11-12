// Pingüino Delta compartido · guarda lo que publica el QF para que los colegas lo vean.
// La app es / (cargador que trae la versión publicada de Pingüino Delta).
// GET  /api/delta            -> índice: qué Excel hay publicados (nombre, fecha, etag) y la config compartida
// GET  /api/delta?k=consumos -> Excel único de consumos y programaciones (base64)
// GET  /api/delta?k=sapu     -> Excel de consumo diario SAPU (base64)
// GET  /api/delta?k=oc       -> órdenes de compra (todas)
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

// Órdenes de compra: varias personas editan a la vez. Cada cambio llega como una
// OPERACIÓN y el servidor la aplica con SU hora (no la de cada PC):
//   {op:"oc", oc}            crea o edita cabecera y artículos (no toca estados ya marcados)
//   {op:"linea", id, linea}  marca una línea (OK / sin recepción / quiebre / recibido / obs)
//   {op:"cab", id, campos}   cierre, reapertura o eliminación
function ocAplicarOp(ocs, op, ahora) {
  if (op.op === "linea") {
    const o = ocs[op.id]; if (!o || !op.linea || typeof op.linea.id !== "string") return null;
    const L = (o.lineas || []).slice(); const i = L.findIndex((l) => l.id === op.linea.id);
    const nl = { ...op.linea, ts: ahora }; if (i >= 0) L[i] = nl; else L.push(nl);
    ocs[op.id] = { ...o, lineas: L }; return ocs[op.id];
  }
  if (op.op === "cab") {
    const o = ocs[op.id]; if (!o || !op.campos || typeof op.campos !== "object") return null;
    const c = {}; ["estado", "cierre", "borrada", "updPor"].forEach((k) => { if (k in op.campos) c[k] = op.campos[k]; });
    ocs[op.id] = { ...o, ...c, upd: ahora }; return ocs[op.id];
  }
  if (op.op === "oc") {
    const n = op.oc; if (!n || typeof n.id !== "string" || !Array.isArray(n.lineas)) return null;
    const o = ocs[n.id];
    if (!o) { ocs[n.id] = { ...n, upd: ahora, creado: ahora, lineas: n.lineas.map((l) => ({ ...l, ts: ahora })) }; return ocs[n.id]; }
    const prevL = {}; (o.lineas || []).forEach((l) => { prevL[l.id] = l; });
    const lineas = n.lineas.map((l) => {
      const p = prevL[l.id];
      if (!p) return { estado: "pend", recib: null, obs: "", ...l, ts: ahora };
      const cambia = p.art !== l.art || +p.cant !== +l.cant || !!p.borrada !== !!l.borrada;
      return { ...p, art: l.art, cant: +l.cant, borrada: !!l.borrada, ...(cambia ? { ts: ahora, por: l.por || p.por } : {}) };
    });
    (o.lineas || []).forEach((l) => { if (!n.lineas.some((x) => x.id === l.id)) lineas.push(l); });
    ocs[n.id] = { ...o, numero: n.numero, proveedor: n.proveedor, fecha: n.fecha, obs: n.obs, updPor: n.updPor, upd: ahora, lineas };
    return ocs[n.id];
  }
  return null;
}
const MAX_OC = 300 * 1024;

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
    if (k === "oc") {
      const o = (await store.get("ocs", { type: "json" })) || { ocs: {} };
      return json(o);
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
    if (body.k === "oc") {
      if (text.length > MAX_OC) return json({ error: "OC demasiado grande." }, 413);
      const idOk = (v) => typeof v === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(v);
      const oid = body.op === "oc" ? body.oc && body.oc.id : body.id;
      const lineasOk = body.op === "oc" ? Array.isArray(body.oc && body.oc.lineas) && body.oc.lineas.every((l) => l && idOk(l.id))
        : body.op === "linea" ? !!(body.linea && idOk(body.linea.id)) : true;
      if (!["oc", "linea", "cab"].includes(body.op) || !idOk(oid) || !lineasOk) return json({ error: "OC inválida." }, 400);
      const todo = (await store.get("ocs", { type: "json" })) || { ocs: {} };
      const oc = ocAplicarOp(todo.ocs, body, ahora);
      if (!oc) return json({ error: "OC inválida o inexistente." }, body.op === "oc" ? 400 : 404);
      todo.upd = ahora;
      await store.setJSON("ocs", todo);
      return json({ ok: true, oc });
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
