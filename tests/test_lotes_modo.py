"""Prueba del modo «como Lotes» de Delta compartido (sin cuenta Microsoft).
- La página es el cargador institucional con CONFIG {modo:'lotes'} servido en https://lotes.test/delta/.
- /api/delta y /api/inventario se simulan en memoria (como las funciones de Netlify de Pingüino Lotes).
Verifica: publicar los Excel con clave (y rechazo con clave errónea), que otro PC los vea sin cargar
nada, que tome los stocks de las tres bodegas desde Lotes, que comparta el mín/máx con clave y que
sin internet abra con la última copia.
"""
import asyncio, os, re, json, hashlib, datetime as dt, urllib.parse as up
from playwright.async_api import async_playwright
BASE=os.path.dirname(os.path.abspath(__file__)); RAIZ=os.path.join(BASE,'..'); DEMO=os.path.join(RAIZ,'demo')
HTML=open(os.path.join(RAIZ,'index.html'),'rb').read()
CARGADOR=open(os.path.join(RAIZ,'institucional','index.html'),encoding='utf-8').read()
def ruta(p): return os.path.join(DEMO,next(x for x in sorted(os.listdir(DEMO)) if x.startswith(p)))
CFG={"nombre":"DESAM Prueba","modo":"lotes","api":"/api/delta"}
PAGINA=re.sub(r'const CONFIG = \{[\s\S]*?\};','const CONFIG = '+json.dumps(CFG)+';',CARGADOR,count=1)
CLAVE='clave-buena'
fallas=[]
def ok(c,m): print(('✓ ' if c else '✗ ')+m); (None if c else fallas.append(m))

# Inventario de Lotes (formato de /api/inventario): items {n, lots:[[venc ISO, lote, stock, ...]]}
LOTES={
 'botiquin':{'meta':{'cargado':'2026-11-09T12:00:00Z','fechaReporte':'2026-11-09','archivo':'toma_botiquin.xlsx'},'items':[
   {'n':'PARACETAMOL 500 MG COMPRIMIDO','lots':[['2028-02-13','L1',1234,''],['2027-11-01','L2',3,'']]},
   {'n':'IBUPROFENO 400 MG COMPRIMIDO','lots':[['2027-05-31','I1',500,'']]}]},
 'central':{'meta':{'cargado':'2026-11-09T12:00:00Z','fechaReporte':'2026-11-08','archivo':'toma_central.xlsx'},'items':[
   {'n':'IBUPROFENO 400 MG COMPRIMIDO','lots':[['2028-01-31','BC1',300,'']]}]},
 'sapu':{'meta':{'cargado':'2026-11-09T12:00:00Z','fechaReporte':'2026-11-07','archivo':'toma_sapu.xlsx'},'items':[
   {'n':'INSULINA CRISTALINA 100 UI/ML SOLUCIÓN INYECTABLEF','lots':[['2028-06-30','BF1',1,'']]}]},
}
class Servidor:
    def __init__(s): s.idx={'archivos':{},'comp':None}; s.arch={}; s.comp=None; s.caido=False; s.posts=0
    async def handle(s,rt):
        u=up.urlparse(rt.request.url); q=up.parse_qs(u.query); m=rt.request.method
        if s.caido: return await rt.abort()
        J=lambda o,st=200: rt.fulfill(status=st,content_type='application/json',body=json.dumps(o))
        if u.path=='/api/inventario':
            b=(q.get('bodega') or ['botiquin'])[0]; return await J(LOTES[b])
        if u.path=='/api/delta':
            if m=='GET':
                k=(q.get('k') or [None])[0]
                if not k: return await J(s.idx)
                if k=='comp': return await (J(s.comp) if s.comp else J({'error':'no'},404))
                return await (J(s.arch[k]) if k in s.arch else J({'error':'no'},404))
            if m=='POST':
                if rt.request.headers.get('authorization','')!='Bearer '+CLAVE: return await J({'error':'Clave incorrecta.'},401)
                b=json.loads(rt.request.post_data); s.posts+=1; ahora=dt.datetime.utcnow().isoformat()+'Z'
                if b['k']=='comp':
                    et=hashlib.sha1(json.dumps(b['datos']).encode()).hexdigest()[:16]
                    s.comp={'ts':ahora,'por':b.get('por',''),'etag':et,'datos':b['datos']}; s.idx['comp']={'ts':ahora,'por':b.get('por',''),'etag':et}
                    return await J({'ok':True,'etag':et,'ts':ahora})
                meta={'nombre':b['nombre'],'subido':ahora,'por':b.get('por',''),'etag':hashlib.sha1(b['b64'].encode()).hexdigest()[:16]}
                s.arch[b['k']]=dict(meta,b64=b['b64']); s.idx['archivos'][b['k']]=meta
                return await J({'ok':True,'meta':meta})
        return False

async def pc(b,srv):
    ctx=await b.new_context(); pg=await ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('dialog',lambda d:(errs.append('DIALOGO '+d.message[:150]),asyncio.ensure_future(d.accept())))
    async def route(rt):
        u=rt.request.url
        if u.startswith('https://carrascocisternaf-alt.github.io/pinguino-delta/'):
            if srv.caido: return await rt.abort()
            return await rt.fulfill(status=200,content_type='text/html',headers={'Access-Control-Allow-Origin':'*'},body=HTML)
        if u.startswith('https://lotes.test/'):
            p=up.urlparse(u).path
            if p in ('/delta/','/delta/index.html'):  # sin internet la página la entrega el service worker de Lotes
                return await rt.fulfill(status=200,content_type='text/html',body=PAGINA)
            if p.startswith('/api/'):
                r=await srv.handle(rt)
                if r is not False: return
            return await rt.fulfill(status=404,body='')
        await rt.abort()
    await ctx.route('**/*',route)
    await pg.clock.install(time=dt.datetime(2026,11,10,10,0))
    return ctx,pg,errs

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); S=Servidor()
        # ── PC de Felipe: guarda la clave y carga sus Excel como siempre ──
        ctx,pg,errs=await pc(b,S)
        await pg.goto('https://lotes.test/delta/'); await pg.wait_for_timeout(4000)
        ok('aún no hay datos publicados' in await pg.inner_text('#nube-bar'),'Sin clave: vista de consulta, aún sin datos')
        await pg.click('text=🔑 Publicar desde este PC'); await pg.fill('#lx-clave','mala'); await pg.fill('#lx-por','Q.F. Prueba')
        await pg.click('#nube-bar .nb-pub button.nb-main'); await pg.wait_for_timeout(2500)
        ok('clave incorrecta' in await pg.inner_text('#nube-bar') and 'estado' not in S.arch,'Clave equivocada: no publica y avisa')
        if not await pg.is_visible('#lx-clave'): await pg.click('text=🔑 Publicar desde este PC')
        await pg.fill('#lx-clave',CLAVE)
        await pg.click('#nube-bar .nb-pub button.nb-main'); await pg.wait_for_timeout(2500)
        for fid,pre in [('fi-inv','01'),('fi-prog','05')]:
            await pg.set_input_files('#'+fid,ruta(pre)); await pg.wait_for_timeout(900)
        await pg.evaluate("switchMode('sapu');sapuSwitch('diario')")
        await pg.set_input_files('#sp-dia-fi',ruta('12_')); await pg.wait_for_timeout(900)
        await pg.evaluate("sapuSwitch('repo')")
        await pg.set_input_files('#sp-mm-fi',ruta('11_')); await pg.wait_for_timeout(900)
        await pg.set_input_files('#sp-sst-fi',ruta('13_')); await pg.wait_for_timeout(7000)
        n=await pg.evaluate("({inv:Object.keys(inv).length,cons:Object.keys(cons_map).length,prog:Object.keys(prog).length,dias:_sdCfg().diarioDias.length,mm:Object.keys(_repoCfg().mm||{}).length,sst:Object.keys(_repoCfg().sapuStock||{}).length,bar:document.getElementById('nube-bar').innerText})")
        ok('estado' in S.arch and 'publicado desde este PC' in n['bar'],f"Lo cargado se publica solo ({n['bar'][:120]!r})")
        ok(not errs,f'PC de Felipe sin errores ({errs})')
        # ── PC de una colega: solo abre el link ──
        ctx2,pg2,errs2=await pc(b,S)
        await pg2.goto('https://lotes.test/delta/'); await pg2.wait_for_timeout(9000)
        r=await pg2.evaluate("({inv:Object.keys(inv).length,cons:Object.keys(cons_map).length,prog:Object.keys(prog).length,dias:_sdCfg().diarioDias.length,mm:Object.keys(_repoCfg().mm||{}).length,sst:Object.keys(_repoCfg().sapuStock||{}).length,stinv:document.getElementById('st-inv').textContent,bar:document.getElementById('nube-bar').innerText})")
        ok(all(r[k]==n[k] for k in ['inv','cons','prog','dias','mm','sst']) and r['inv']>0,f"La colega ve exactamente lo mismo ({ {k:r[k] for k in ['inv','cons','prog','dias','mm','sst']} })")
        ok('datos publicados' in r['bar'] and 'Q.F. Prueba' in r['bar'],f"Barra de la colega: quién y cuándo publicó ({r['bar'][:140]!r})")
        # Felipe actualiza el inventario → la colega lo ve al «Actualizar»
        await pg.evaluate("inv={'PARACETAMOL 500 MG COMPRIMIDO':[{lote:'NUEVO',venc:'01/2029',stock:5}]};pdbGuardar('inv')"); await pg.wait_for_timeout(7000)
        await pg2.click('text=🔄 Actualizar'); await pg2.wait_for_timeout(7000)
        r=await pg2.evaluate("JSON.stringify(inv)")
        ok('NUEVO' in r,'Cambio posterior de Felipe llega a la colega')
        # Sin internet: reabre con la última copia
        S.caido=True
        await pg2.reload(); await pg2.wait_for_timeout(5000)
        r=await pg2.evaluate("({inv:JSON.stringify(inv),cons:Object.keys(cons_map).length,bar:document.getElementById('nube-bar').innerText})")
        ok('NUEVO' in r['inv'] and r['cons']==n['cons'] and 'sin conexión' in r['bar'],f"Sin internet abre con la última copia ({r['bar'][:150]!r})")
        ok(not errs2,f'PC de la colega sin errores ({errs2})')
        await b.close()
    print('\nRESULTADO:', 'TODO OK' if not fallas else f'{len(fallas)} FALLA(S)')
    if fallas: raise SystemExit(1)
asyncio.run(main())
