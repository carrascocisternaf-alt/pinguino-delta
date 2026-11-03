"""Prueba funcional de Pingüino Delta con los Excels de demostración.
- Sin internet (todo request externo se bloquea: valida que el HTML sea autónomo).
- Fecha fija 16-10-2026 (los vencimientos demo están calculados desde ese día).
- Verificación exacta de conteos y de la clasificación de Rotación.
Uso: pip install playwright && playwright install chromium && python3 tests/test_demo.py
"""
import asyncio, os, sys, datetime as dt
from playwright.async_api import async_playwright
BASE=os.path.dirname(os.path.abspath(__file__)); RAIZ=os.path.join(BASE,'..')
DEMO=os.path.join(RAIZ,'demo'); HTML='file://'+os.path.abspath(os.path.join(RAIZ,'index.html'))
def f(p): return next(os.path.join(DEMO,x) for x in sorted(os.listdir(DEMO)) if x.startswith(p))
fallas=[]
def ok(cond,msg): print(('✓ ' if cond else '✗ ')+msg); (None if cond else fallas.append(msg))

async def nueva(b):
    pg=await b.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('dialog',lambda d:(errs.append('DIALOGO: '+d.message[:200]),asyncio.ensure_future(d.accept())))
    async def route(rt):
        await (rt.continue_() if rt.request.url.startswith('file:') else rt.abort())
    await pg.route('**/*',route)
    await pg.clock.install(time=dt.datetime(2026,10,16,10,0))
    await pg.goto(HTML); await pg.wait_for_timeout(1500)
    return pg,errs

async def st(pg,i): return await pg.eval_on_selector('#'+i,'e=>e.textContent')

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        # ── Escenario A: archivos separados ──
        pg,errs=await nueva(b)
        ok(await pg.evaluate("typeof XLSX")=='object','SheetJS embebido disponible sin internet')
        ok(await pg.eval_on_selector('[data-an=log]','e=>getComputedStyle(e).display')=='none','Pestaña LOG oculta')
        for fid,pre,sid,txt in [('fi-inv','01','st-inv','✓ 40 artículos'),('fi-cons','02','st-cons','✓ 40 artículos'),
            ('fi-prog','03','st-prog','3 artículo(s) con doble programación'),('fi-disp','04','st-disp','años: 2024, 2025, 2026'),
            ('cal-fi','06','cal-st','✓ 223 despachos'),('costo-fi','07','costo-st','✓ 40 artículos'),
            ('difinv-fi','08','difinv-st','✓ 14 artículo(s)'),('gasto-fi','09','gasto-st','✓ 840 registros')]:
            await pg.set_input_files('#'+fid,f(pre)); await pg.wait_for_timeout(700)
            t=await st(pg,sid); ok(txt in t,f'{pre} → {t[:90]}')
        ok(await pg.evaluate("Object.keys(ARTS_DINAMICOS).length")==0,'0 artículos no reconocidos (homologación 100%)')
        await pg.evaluate("calcularRotacion('arsenal')")
        c=await pg.evaluate("(()=>{const R=window._rotResultados_arsenal;const L=R.map?R:R.res;const c={};L.forEach(x=>c[x.estado]=(c[x.estado]||0)+1);return c})()")
        ok(c=={'ok':24,'critico':5,'sobrestock':6,'vence-pronto':5},f'Rotación: {c}')
        ok(not errs,f'Sin errores JS ni alertas: {errs}')
        # ── Escenario B: archivo único ──
        pg,errs=await nueva(b)
        await pg.set_input_files('#fi-prog',f('05')); await pg.wait_for_timeout(900)
        t=await st(pg,'st-prog'); ok('80 filas de consumo / 86 de programación' in t,'05 archivo único → '+t[-90:])
        ok('✓ 40 artículos' in await st(pg,'st-cons'),'05 → consumo promedio derivado')
        ok(not errs,f'Sin errores JS ni alertas: {errs}')
        # ── Escenario C: botón "Cargar datos de prueba" (datos embebidos) ──
        pg,errs=await nueva(b)
        await pg.click('#demo-bar button'); await pg.wait_for_timeout(5500)
        ok('12 archivos de prueba cargados' in await st(pg,'demo-st'),'Botón → '+(await st(pg,'demo-st'))[:60])
        for sid,txt in [('st-inv','✓ 40 artículos'),('st-prog','doble programación'),('st-disp','años: 2024, 2025, 2026'),('cal-st','✓ 223 despachos'),('difinv-st','✓ 14 artículo(s)'),('gasto-st','✓ 840 registros')]:
            ok(txt in await st(pg,sid),f'Botón → {sid}')
        await pg.evaluate("calcularRotacion('arsenal')")
        c=await pg.evaluate("(()=>{const R=window._rotResultados_arsenal;const L=R.map?R:R.res;const c={};L.forEach(x=>c[x.estado]=(c[x.estado]||0)+1);return c})()")
        ok(c=={'ok':24,'critico':5,'sobrestock':6,'vence-pronto':5},f'Botón → Rotación: {c}')
        # ── Escenario F: Reposición SAPU ──
        await pg.evaluate("switchMode('sapu');sapuSwitch('repo');repoParam('frec','semanal');repoParam('vista','mes');repoParam('mes','2026-11')")
        await pg.wait_for_timeout(500)
        r=await pg.evaluate("""(()=>{const F=_repoUltimo.filas;const by=n=>F.find(a=>a.art.startsWith(n));
          const excl=F.filter(a=>a.P.excl);
          return{n:F.length,
            exclSoloBodega:excl.every(a=>a.picks.every(p=>p.origen==='Bodega central')),
            fefoLido:(by('LIDOCAINA').picks[0]||{}).lote,
            paraB:(repoParam('mes','2026-10'),_repoUltimo.filas.find(a=>a.art.startsWith('PARACETAMOL 500')).picks[0]||{}).origen,
            salbFalt:by('SALBUTAMOL').falt>0}})()""")
        ok(r['n']==16 and r['exclSoloBodega'],f'Reposición SAPU: 16 artículos y exclusivos solo desde bodega central ({r})')
        ok(r['fefoLido']=='BC-LI01' and r['paraB']=='Bodega central',f"Reposición SAPU: FEFO (lidocaína {r['fefoLido']}) y bodega antes que farmacia (paracetamol: {r['paraB']})")
        ok(r['salbFalt'],'Reposición SAPU: respeta la reserva de farmacia (salbutamol con faltante)')
        r=await pg.evaluate("""(()=>{repoParam('mes','2026-11');const a='ATROPINA 1 MG/ML SOLUCIÓN INYECTABLE AMPOLLA';prog[a]={origen:'CENABAST',años:{2026:{diciembre:50}},origenPorAño:{2026:'CENABAST'},desglose:{}};repoParam('mes','2026-12');
          return _repoUltimo.filas.find(x=>x.art===a).lleg.map(l=>l.q+'|'+l.destino)})()""")
        ok(r==['50|Bodega central'],f'Reposición SAPU: lo programado de un exclusivo llega a bodega central ({r})')
        r=await pg.evaluate("""(()=>{sapuSwitch('repo');repoParam('vista','semana');repoParam('frec','semanal');const F=_repoUltimo.filas;const by=n=>F.find(a=>a.art.startsWith(n));
          return{fuente:by('PARACETAMOL 500').P.fStock,stock:by('PARACETAMOL 500').P.stockSapu,col:_repoCfg().sapuStockArchivo.includes('Stock Sist.')}})()""")
        ok(r['fuente'].startswith('AVIS') and r['stock']==240 and r['col'],f'Stock SAPU (AVIS): usa «Stock Sist.» por lote, no «Stock Total» ({r})')
        r=await pg.evaluate("""(()=>{sapuSwitch('repo');const tot=document.querySelectorAll('#repo-tabla tbody tr[data-art]').length;repoBuscar('paracetamol');
          const vis=[...document.querySelectorAll('#repo-tabla tbody tr[data-art]')].filter(t=>t.style.display!=='none').map(t=>t.dataset.art);
          repoParam('vista','semana');const sigue=[...document.querySelectorAll('#repo-tabla tbody tr[data-art]')].filter(t=>t.style.display!=='none').length;repoBuscar('');
          return{tot,vis,sigue,q:document.getElementById('repo-buscar').value}})()""")
        ok(r['tot']>1 and r['vis'] and all('PARACETAMOL' in v for v in r['vis']) and r['sigue']==len(r['vis']),f'Reposición SAPU: buscador filtra y se mantiene al recalcular ({r})')
        r=await pg.evaluate("""(()=>{sapuSwitch('repo');repoParam('vista','semana');const vis=()=>[...document.querySelectorAll('#repo-tabla tbody tr[data-art]')].filter(t=>t.style.display!=='none');
          const F=_repoUltimo.filas;repoFiltrar('falt');const nf=vis().length;const okf=vis().every(t=>F.find(a=>normArt(a.art)===t.dataset.art).falt>0);
          repoFiltrar('rep');const nr=vis().length;repoParam('vista','semana');const sigue=vis().length;repoFiltrar('rep');const todos=vis().length;
          const th=[...document.querySelectorAll('#repo-tabla th')].map(t=>t.textContent).find(t=>t.startsWith('Stock SAPU'));
          return{nf,okf,kf:F.filter(a=>a.falt>0).length,nr,kr:F.filter(a=>a.env>0).length,sigue,todos,n:F.length,th}})()""")
        ok(r['nf']==r['kf'] and r['okf'] and r['nr']==r['kr'] and r['sigue']==r['nr'] and r['todos']==r['n'] and r['th']=='Stock SAPUactual',f'Reposición SAPU: clic en tarjetas filtra (faltante / a reponer), se mantiene al recalcular y «Stock SAPU actual» ({r})')
        # ── Escenario G: consumo real del SAPU (mensual en archivo único y diario) ──
        r=await pg.evaluate("""(()=>{const c=_sapuCfg();return{dias:c.diarioDias.length,real:_sapuConsReal('PARACETAMOL 500 MG COMPRIMIDO'),fuente:(sapuSwitch('repo'),_repoUltimo.filas.find(a=>a.art==='PARACETAMOL 500 MG COMPRIMIDO').P.cons.f)}})()""")
        ok(r['dias']==15 and r['real']['tipo']=='diario' and r['fuente'].startswith('Real diario'),f"Consumo real SAPU: 15 días informados y Reposición usa el real diario ({r['fuente']})")
        pg2,errs2=await nueva(b)
        await pg2.set_input_files('#fi-prog',f('05')); await pg2.wait_for_timeout(900)
        r=await pg2.evaluate("[cons_mensual['PARACETAMOL 500 MG COMPRIMIDO'][2026]['julio'],(_sapuCfg().consMensualSapu['PARACETAMOL 500 MG COMPRIMIDO']||{})[2026],!!cons_mensual['ATROPINA 1 MG/ML SOLUCIÓN INYECTABLE AMPOLLA']]")
        ok(r[0]==19874 and r[1] and r[1].get('julio')==399 and r[2] is False,f'Archivo único: «Consumo SAPU 2026» no se suma al botiquín ({r})')
        ok(not errs2,f'Archivo único con SAPU sin errores ({errs2})')
        errs=[e for e in errs if not e.startswith('DIALOGO: Se cargarán los datos FICTICIOS')]
        ok(not errs,f'Botón → sin errores JS ni alertas: {errs}')
        # ── Escenario D: buscador de la Ayuda ──
        pg,errs=await nueva(b)
        await pg.evaluate("switchMode('ayuda')")
        r=await pg.evaluate("({fuera:document.querySelectorAll('.arch-card:not(#view-ayuda .arch-card)').length,dentro:document.querySelectorAll('#view-ayuda .arch-grid > .arch-card').length,ids:[...document.querySelectorAll('[id]')].map(e=>e.id).filter((x,i,a)=>a.indexOf(x)!==i)})")
        ok(r['fuera']==0 and r['dentro']==13 and not r['ids'],f'Ayuda: las 13 fichas de archivos están solo en la Ayuda y no hay ids duplicados ({r})')
        r=await pg.evaluate("(ayudaBuscar('respaldo'),document.querySelector('#ay-res .ay-t')?.textContent)")
        ok(r=='Exportar e importar respaldo',f'Buscador → «respaldo»: {r}')
        r=await pg.evaluate("(ayudaBuscar('monte carlo'),[...document.querySelectorAll('#ay-res .ay-t')].map(e=>e.textContent))")
        ok(r==['Probabilidad de quiebre'],f'Buscador → «monte carlo»: {r}')
        n=await pg.evaluate("(()=>{let f=0;AYUDA_CATALOGO.filter(e=>e.go).forEach(e=>{try{ayudaIr(e.go)}catch(x){f++}});return f})()")
        ok(n==0 and not errs,f'Buscador → todos los «Ir →» sin errores ({errs})')
        # ── Escenario H: invariantes de Reposición SAPU con datos aleatorios ──
        pg3,errs3=await nueva(b)
        r=await pg3.evaluate("window.__FUZZ_N=120;"+open(os.path.join(BASE,'fuzz_reposicion.js'),encoding='utf-8').read())
        ok(r['casos']==120 and not r['fallas'],f"Reposición SAPU: 120 escenarios aleatorios sin violar invariantes (despacho = picking, unidades enteras, sin stocks negativos, reserva de farmacia, destino de lo programado) {r['fallas'][:3]}")
        ok(not errs3,f'Invariantes sin errores JS ({errs3})')
        # ── Escenario E: IA local (homologación, calidad, política, grupos) ──
        pg,errs=await nueva(b)
        h=await pg.evaluate("homEvaluar()")
        ok(h['nuevo']>h['anterior'] and h['errDosisN']<=h['errDosisJ'],f"Homologación: {h['nuevo']:.0%} vs {h['anterior']:.0%} anterior; errores de dosis {h['errDosisN']} vs {h['errDosisJ']}")
        r=await pg.evaluate("(r=>[r.art,r.det.bloqueo])(homSugerir('LOSARTAN 100 MG CM'))")
        ok(r[1] is True,f'Homologación: no sugiere dosis distinta ({r})')
        await pg.click('#demo-bar button'); await pg.wait_for_timeout(5500)
        n=await pg.evaluate("calidadRevisar().length")
        ok(n==0,f'Calidad: 0 avisos con datos demo correctos ({n})')
        await pg.evaluate("cons_mensual['LOSARTAN (POTASICO) 50 MG COMPRIMIDO'][2026]['marzo']*=10")
        r=await pg.evaluate("calidadRevisar().map(x=>x.sev+'|'+x.art)")
        ok(r==['alta|LOSARTAN (POTASICO) 50 MG COMPRIMIDO'],f'Calidad: detecta un cero de más sembrado ({r})')
        await pg.evaluate("cons_mensual['LOSARTAN (POTASICO) 50 MG COMPRIMIDO'][2026]['marzo']/=10")
        await pg.evaluate("switchMode('analisis');anSwitch('politica')"); await pg.click('#an-politica .btn-calc')
        await pg.wait_for_function("typeof politicaRes!=='undefined'&&politicaRes",timeout=60000)
        r=await pg.evaluate("({n:politicaRes.res.length,mejor:politicaRes.res.every(x=>x.rec.c<=x.actual.c+1e-9||!x.rec.cumple||x.actual.pq>({V:0.05,E:0.10}[x.ven]||1))})")
        ok(r['n']==40 and r['mejor'],f'Política: 40 artículos y la recomendada nunca es peor que la actual ({r})')
        await pg.evaluate("anSwitch('gruposcomp')"); await pg.click('#an-gruposcomp .btn-calc'); await pg.wait_for_timeout(1200)
        r=await pg.evaluate("({k:gruposRes.k,n:gruposRes.asig.length,unicos:new Set(gruposRes.grupos.map(g=>g.nombre)).size===gruposRes.grupos.length})")
        ok(3<=r['k']<=6 and r['n']==40 and r['unicos'],f'Grupos: {r}')
        errs=[e for e in errs if not e.startswith('DIALOGO: Se cargarán los datos FICTICIOS')]
        ok(not errs,f'IA local sin errores JS ({errs})')
        # ── Escenario I: Excel tal como los entrega AVIS (filas extra arriba) y consumo diario «Día N (día semana)» ──
        pg,errs=await nueva(b)
        SUBIR="""(id,aoa,nombre)=>{const ws=XLSX.utils.aoa_to_sheet(aoa),wb=XLSX.utils.book_new();XLSX.utils.book_append_sheet(wb,ws,'Export');
          const buf=XLSX.write(wb,{type:'array',bookType:'xlsx'});const dt=new DataTransfer();dt.items.add(new File([buf],nombre));
          const el=document.getElementById(id);el.files=dt.files;el.dispatchEvent(new Event('change',{bubbles:true}));}"""
        toma=[[],['TOMA DE INVENTARIO'],[],['Fecha',':','10/10/2026'],['Funcionario',':','(1-9) PERSONA DE PRUEBA'],[' '],[],[],
              ['Grupo','Familia','Código','Nombre Artículo','Ubicación','Vencimiento','Lote','Stock Sist.','Último Precio\nIngresado','Stock Valorizado'],
              ['MED','MED','1','PARACETAMOL 500 MG COMPRIMIDO','UNICO','13/02/2028','L1','1.234,00','0.00','0.00'],
              ['MED','MED','1','PARACETAMOL 500 MG COMPRIMIDO','UNICO','01/11/2027','L2','3.00','0.00','0.00']]
        await pg.evaluate(f"({SUBIR})('fi-inv',{toma!r},'toma.xlsx')".replace('None','null')); await pg.wait_for_timeout(700)
        r=await pg.evaluate("JSON.stringify(inv['PARACETAMOL 500 MG COMPRIMIDO'])")
        ok(r=='[{"lote":"L1","venc":"02/2028","stock":1234},{"lote":"L2","venc":"11/2027","stock":3}]',f'AVIS con 8 filas de título: Mi arsenal lee el inventario y los números en texto ({r})')
        await pg.evaluate("switchMode('sapu')"); await pg.wait_for_timeout(400)
        await pg.evaluate(f"({SUBIR})('sp-sst-fi',{toma!r},'toma.xlsx')".replace('None','null')); await pg.wait_for_timeout(700)
        r=await pg.evaluate("_repoCfg().sapuStockFecha")
        ok(r=='2026-10-10',f'Stock SAPU: toma la fecha del reporte AVIS ({r})')
        dia=[['ARTICULO','CONSUMO DIA 1 (LUNES) ','CONSUMO DIA 2 (MARTES)','CONSUMO DIA 3 (MIERCOLES)','CONSUMO DIA 4 (JUEVES)','CONSUMO DIA 5 (VIERNES)'],
             ['PARACETAMOL 500 MG COMPRIMIDO',4,0,2,6,None],['IBUPROFENO 400 MG COMPRIMIDO',1,1,0,0,None]]
        await pg.evaluate(f"({SUBIR})('sp-dia-fi',{dia!r},'consumo.xlsx')".replace('None','null')); await pg.wait_for_timeout(700)
        r=await pg.evaluate("(()=>{const c=_sdCfg();return{ini:c.diarioRel&&c.diarioRel.inicio,dias:c.diarioDias,p:c.diario['PARACETAMOL 500 MG COMPRIMIDO']}})()")
        ok(r['ini']=='2026-10-12' and r['dias']==['2026-10-12','2026-10-13','2026-10-14','2026-10-15'] and r['p']['2026-10-15']==6,
           f'Consumo diario «Día N (día)»: Día 1 = lunes 12/10, columna vacía no cuenta ({r})')
        r=await pg.evaluate("(()=>{sapuCambiarInicioRel('2026-10-05');const c=_sdCfg();return{dias:c.diarioDias,p:c.diario['PARACETAMOL 500 MG COMPRIMIDO']}})()")
        ok(r['dias']==['2026-10-05','2026-10-06','2026-10-07','2026-10-08'] and r['p']=={'2026-10-05':4,'2026-10-06':0,'2026-10-07':2,'2026-10-08':6},f'Consumo diario: cambiar «Día 1» re-fecha sin duplicar ({r})')
        ok(not errs,f'Escenario AVIS / diario relativo sin errores ({errs})')
        await b.close()
    print('\nRESULTADO:', 'TODO OK' if not fallas else f'{len(fallas)} FALLA(S)')
    sys.exit(1 if fallas else 0)
asyncio.run(main())
