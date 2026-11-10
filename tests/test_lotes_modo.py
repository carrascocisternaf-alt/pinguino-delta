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
CFG={"nombre":"DESAM Prueba","modo":"lotes","api":"/api/delta","inventario":"/api/inventario"}
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
        ctx,pg,errs=await pc(b,S)
        await pg.goto('https://lotes.test/delta/'); await pg.wait_for_timeout(4000)
        r=await pg.evaluate("({bar:document.getElementById('nube-bar').innerText,inv:Object.keys(inv).length,bod:Object.keys(_repoCfg().bodega||{}).length,sapu:_repoCfg().sapuStock,fecha:_repoCfg().sapuStockFecha})")
        ok('aún no publicado' in r['bar'] and 'Botiquín 09/11/2026' in r['bar'],f"Barra: sin Excel publicados y stocks de Lotes ({r['bar'][:200]!r})")
        ok(r['inv']==2 and r['bod']==1 and r['sapu'] and 'INSULINA CRISTALINA 100 UI/ML SOLUCIÓN INYECTABLE' in r['sapu'] and r['fecha']=='2026-11-07',
           f"Stocks de las tres bodegas desde Lotes, con homologación («F») y fecha de la toma ({r['inv']} botiquín, {r['bod']} central, fecha {r['fecha']})")
        # Publicar con clave equivocada → rechazo
        await pg.click('text=⬆ Publicar Excel'); await pg.fill('#lx-clave','mala')
        await pg.set_input_files('.nb-pub label.nb-file >> nth=0 >> input',ruta('05_')); await pg.wait_for_timeout(2500)
        ok('Clave incorrecta' in await pg.inner_text('#lx-st') and S.posts==0,'Clave equivocada: no se publica')
        await pg.fill('#lx-clave',CLAVE); await pg.fill('#lx-por','Q.F. Prueba')
        await pg.set_input_files('.nb-pub label.nb-file >> nth=0 >> input',ruta('05_')); await pg.wait_for_timeout(3000)
        await pg.set_input_files('.nb-pub label.nb-file >> nth=1 >> input',ruta('12_')); await pg.wait_for_timeout(3000)
        ok('consumos' in S.arch and 'sapu' in S.arch and 'Publicado' in await pg.inner_text('#lx-st'),f"Publica los dos Excel con la clave ({list(S.arch)})")
        # Un Excel que Delta no entiende no se publica
        n0=S.posts; await pg.set_input_files('.nb-pub label.nb-file >> nth=0 >> input',ruta('07_')); await pg.wait_for_timeout(2500)
        ok(S.posts==n0 and 'No se publicó' in await pg.inner_text('#lx-st'),'Excel con formato equivocado: avisa y no lo publica')
        # Mín/máx compartido (con la clave guardada en este PC)
        await pg.evaluate("switchMode('sapu');sapuSwitch('repo')")
        await pg.set_input_files('#sp-mm-fi',ruta('11_')); await pg.wait_for_timeout(4500)
        ok(S.comp and len(S.comp['datos']['repo']['mm'])>0 and 'bodega' not in S.comp['datos']['repo'],f"Mín/máx se comparte (sin stocks, que vienen de Lotes) ({len(S.comp['datos']['repo']['mm']) if S.comp else 0} artículos)")
        ok(not errs,f'PC 1 sin errores ({errs})')
        # ── PC 2: colega, sin clave, no carga nada ──
        ctx2,pg2,errs2=await pc(b,S)
        await pg2.goto('https://lotes.test/delta/'); await pg2.wait_for_timeout(6000)
        r=await pg2.evaluate("({cons:Object.keys(cons_map).length,prog:Object.keys(prog).length,dias:_sdCfg().diarioDias.length,inv:Object.keys(inv).length,mm:Object.keys(_repoCfg().mm||{}).length,bar:document.getElementById('nube-bar').innerText})")
        ok(r['cons']==40 and r['prog']>0 and r['dias']==15 and r['inv']==2 and r['mm']>0,f"Colega ve consumos, programación, diario SAPU, stocks y mín/máx sin cargar nada ({ {k:v for k,v in r.items() if k!='bar'} })")
        ok('publicado' in r['bar'] and 'Q.F. Prueba' in r['bar'],f"Barra del colega muestra quién y cuándo publicó ({r['bar'][:160]!r})")
        # ── Sin internet: reabre con la última copia ──
        S.caido=True
        await pg2.reload(); await pg2.wait_for_timeout(5000)
        r=await pg2.evaluate("({cons:Object.keys(cons_map).length,dias:_sdCfg().diarioDias.length,inv:Object.keys(inv).length,bar:document.getElementById('nube-bar').innerText})")
        ok(r['cons']==40 and r['dias']==15 and r['inv']==2 and 'sin conexión' in r['bar'],f"Sin internet abre con la última copia ({r['cons']}, {r['dias']} días, {r['inv']} art.)")
        ok(not errs2,f'PC 2 sin errores ({errs2})')
        await b.close()
    print('\nRESULTADO:', 'TODO OK' if not fallas else f'{len(fallas)} FALLA(S)')
    if fallas: raise SystemExit(1)
asyncio.run(main())
