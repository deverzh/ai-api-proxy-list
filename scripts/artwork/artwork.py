#!/usr/bin/env python3
"""Render this repository's editorial artwork. Runtime code does not depend on it."""
import argparse
import base64
import html
import json
import math
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / 'assets' / 'presentation'
W = 1440
INK, MUTED, PAPER, LINE = '#182B32', '#4D6267', '#F3F0E8', '#CAD1CC'
ACCENT = '#087F8C'
FONT = ''

def esc(s):
    return html.escape(str(s), quote=True)

def text(x, y, s, size=26, fill=INK, weight=400, anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{esc(s)}</text>'

def lines(x, y, values, size=26, fill=MUTED, gap=34, anchor='start', weight=400):
    return ''.join(text(x, y+i*gap, s, size, fill, weight, anchor) for i,s in enumerate(values))

def path(d, stroke=LINE, width=2, fill='none', extra=''):
    return f'<path d="{d}" stroke="{stroke}" stroke-width="{width}" fill="{fill}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'

def rect(x,y,w,h,fill='white',stroke='none',radius=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'

def circle(x,y,r,fill='white',stroke=LINE,width=2):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'

def poly(points, fill, stroke='none',width=2):
    pts=' '.join(f'{x},{y}' for x,y in points)
    return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round"/>'

def sheet(x,y,w=166,h=210,accent=ACCENT):
    p=rect(x+11,y+13,w,h,'#D8DED6',radius=4)+rect(x,y,w,h,'#FCFAF3',LINE,4)
    p+=rect(x+21,y+23,51,7,accent,radius=3)
    for i in range(5):
        p+=rect(x+21,y+54+i*24,w-43-(i%3)*17,5,'#AFBAB4',radius=2)
    return p

def icon(kind, scale=1):
    """Semantic linework and material forms, not generated screenshots."""
    p=''
    if kind in ('grid','window','focus'):
        p+=rect(-94,-77,216,171,'#DDE4DD',radius=8)
        p+=rect(-108,-91,216,171,'#FBFAF4',INK,8)
        p+=path('M-108 -61 H108',INK,1.8)
        for i in range(3):p+=circle(-88+i*13,-76,3,ACCENT,'none')
        if kind=='grid':
            for x in (-89,-25,39):
                for y in (-43,10):
                    p+=rect(x,y,51,41,'#E4EBE3',radius=3)
                    p+=circle(x+10,y+9,3,ACCENT,'none')
                    p+=rect(x+17,y+7,24,3,ACCENT,radius=2)
                    p+=rect(x+8,y+17,35,3,'#9CACAB',radius=1)
                    p+=rect(x+8,y+24,26,3,'#9CACAB',radius=1)
                    for dx in (9,23,37):p+=circle(x+dx,y+34,1.5,MUTED,'none')
        elif kind=='focus':
            p+=rect(-89,-40,112,97,'#E7EEE6',radius=3)+rect(36,-40,51,97,'#D4DFD7',radius=3)
            p+=circle(-32,6,31,'#FBFAF4',ACCENT,3)+path('M-45 7 L-35 18 L-17 -5',ACCENT,5)
        else:
            p+=rect(-88,-42,43,102,'#DBE4DD',radius=3)
            for i in range(4):p+=rect(-29,-34+i*24,115-i%2*28,6,ACCENT if i==0 else '#ACB9B3',radius=2)
    elif kind in ('trace','clock'):
        p+=circle(0,0,97,'#E2E9E0','none')+circle(0,0,78,'#FBFAF4',INK,2)
        for i in range(12):
            a=i*math.pi/6
            p+=path(f'M{math.sin(a)*64} {-math.cos(a)*64} L{math.sin(a)*70} {-math.cos(a)*70}',MUTED,2)
        p+=path('M0 -48 V0 L34 22',ACCENT,6)+circle(0,0,6,INK,'none')
        if kind=='trace':p+=path('M-119 107 H-75 L-62 71 L-46 117 L-31 94 H5 L19 111 L34 86 H117',ACCENT,4)
    elif kind in ('database','storage'):
        p+=rect(-84,-55,168,131,'#E1E9DF',INK)
        for y in (-55,10,76):p+=f'<ellipse cx="0" cy="{y}" rx="84" ry="27" fill="{PAPER if y==-55 else "none"}" stroke="{INK}" stroke-width="2"/>'
        p+=path('M-84 -55 V76 M84 -55 V76',INK,2)
        for y in (-16,48):p+=circle(54,y,5,ACCENT,'none')
    elif kind in ('book','library'):
        p+=poly([(-108,70),(2,99),(117,61),(5,35)],'#D5DED4')
        p+=path('M0 -64 Q-51 -97 -113 -65 V75 Q-53 45 0 79 Q57 44 114 72 V-65 Q54 -94 0 -64 Z',INK,2,'#FCFAF3')
        p+=path('M0 -64 V79',ACCENT,3)
        for y in (-36,-10,16,42):
            p+=path(f'M-89 {y} Q-50 {y-10} -22 {y+2} M23 {y+2} Q59 {y-10} 91 {y}',LINE,4)
        p+=path('M76 -72 V-10 L62 -21 L49 -13 V-78',ACCENT,1,ACCENT)
    elif kind in ('network','graph','fork'):
        points=[(-87,-50),(12,-95),(99,-27),(66,86),(-45,76),(0,0)]
        edges=[(0,1),(1,2),(2,3),(3,4),(4,0),(0,5),(2,5),(4,5)]
        if kind=='fork':edges=[(0,5),(5,1),(5,2),(5,3),(5,4)]
        for a,b in edges:p+=path(f'M{points[a][0]} {points[a][1]} L{points[b][0]} {points[b][1]}',ACCENT,4)
        for i,(x,y) in enumerate(points):
            p+=poly([(x-15,y),(x,y-9),(x+15,y),(x,y+10)], '#FBFAF4' if i%2 else ACCENT,INK,1.4)
            p+=path(f'M{x-15} {y} V{y+12} L{x} {y+22} L{x+15} {y+12} V{y}',INK,1.4,'#D5DFD5')
    elif kind=='scope':
        p+=circle(-20,-18,69,'#FCFAF4',INK,5)
        p+=path('M31 36 L103 109',INK,15)
        p+=rect(-53,-45,62,7,ACCENT,radius=3)
        p+=rect(-53,-20,76,5,LINE,radius=2)
        p+=rect(-53,2,50,5,LINE,radius=2)
    elif kind=='dna':
        for i in range(11):
            y=-110+i*22;x=math.sin(i*math.pi/5)*72
            p+=path(f'M{-x} {y} L{x} {y}',LINE,3)
        for side,col in [(-1,INK),(1,ACCENT)]:
            coords=[(side*math.sin(i*math.pi/25)*72,-110+i*4.4) for i in range(51)]
            p+=path('M'+' L'.join(f'{x} {y}' for x,y in coords),col,5)
    elif kind in ('molecule','science'):
        coords=[(-67,-39),(0,-78),(67,-39),(67,39),(0,78),(-67,39)]
        for i in range(6):
            a,b=coords[i],coords[(i+1)%6];p+=path(f'M{a[0]} {a[1]} L{b[0]} {b[1]}',INK,4)
        for x,y in coords:p+=circle(x,y,14,ACCENT if y<0 else '#FCFAF4',INK,2)
        p+=path('M-80 -46 L-111 -64 M80 45 L113 63',INK,3)+circle(-117,-69,9,'#FCFAF4',INK)+circle(118,68,9,ACCENT,INK)
    elif kind in ('layers','type'):
        for i in range(3):
            x,y=-109+i*21,-90+i*17
            p+=sheet(x,y,162,174,ACCENT)
        if kind=='type':
            p+=circle(63,56,47,ACCENT,'none')
            p+=path('M42 78 L63 32 L84 78 M49 63 H77','#FCFAF4',5)
    elif kind=='robot':
        p+=rect(-67,-100,134,79,'#FCFAF4',INK,15)+rect(-81,-4,162,114,'#E1E9DF',INK,12)
        p+=circle(-28,-63,12,ACCENT,INK)+circle(28,-63,12,ACCENT,INK)
        p+=path('M-21 -31 H21 M0 -100 V-117',INK,3)+circle(0,-121,5,ACCENT,INK)
        p+=path('M-80 14 L-111 42 V87 M80 14 L111 42 V87 M-38 109 V132 M38 109 V132',INK,11)
        p+=rect(-31,26,62,38,ACCENT,radius=5)
    elif kind=='cards':
        for x,y,angle in [(-65,-65,-18),(-20,-89,3),(26,-64,23)]:
            p+=f'<g transform="translate({x},{y}) rotate({angle})">'+rect(-37,-37,92,135,'#FCFAF4',INK,8)+poly([(8,-3),(24,20),(8,43),(-8,20)],ACCENT)+'</g>'
        p+=circle(-82,103,26,ACCENT,INK)+circle(-82,103,18,'none','#FCFAF4',2)
    else:
        p+=sheet(-80,-97,160,200,ACCENT)
        p+=path('M-45 71 L-15 40 L8 54 L43 5',ACCENT,5)
    return f'<g transform="scale({scale})">{p}</g>'

def svg(name,h,body,description):
    style=f"@font-face{{font-family:Editorial;src:url(data:font/ttf;base64,{FONT});font-weight:100 900}}text{{font-family:Editorial,Arial,sans-serif}}"
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="{h}" viewBox="0 0 1440 {h}" role="img"><title>{esc(name)}</title><desc>{esc(description)}</desc><defs><style>{style}</style></defs>'+rect(0,0,W,h,PAPER)+body+'</svg>'

def banner(c):
    p=path('M64 62 H1376',INK,2)
    if c['eyebrow'].lower()=='reference fork':
        p+=rect(64,78,285,46,INK,radius=4)+text(79,109,'REFERENCE FORK',26,'#FCFAF3',600)
    else:p+=text(64,105,c['eyebrow'].upper(),23,ACCENT,600)
    titles=c.get('title_lines') or textwrap.wrap(c['title'],14)
    assert len(titles)<=3
    size=min(126, max(64, 1050/max(map(len,titles))))
    if len(titles)==3:size=min(size,76)
    gap=max(102,size*1.35)
    p+=lines(64,251,titles,size,INK,gap,weight=600)
    sy=251+(len(titles)-1)*gap+64
    p+=lines(68,sy,c['subtitle'],27,MUTED,36)
    p+=text(64,591,c['status'],23,ACCENT,500)
    p+='<g transform="translate(1088 336)">'+icon(c['motif'],2.1)+'</g>'
    p+=path('M64 625 H1376',LINE,1)+text(64,655,c['footer'].split('/')[0].strip(),22,MUTED)
    return svg(c['title'],686,p,c['title']+'. '+ ' '.join(c['subtitle'])+'. '+c['status'])

def overview(c):
    p=text(64,93,c.get('overview_title','How it fits together'),45,INK,600)
    p+=text(67,138,c['overview_subtitle'],25,MUTED)
    p+=path('M236 309 H1205',ACCENT,2)
    for x in (478.5,959.5):p+=poly([(x-7,302),(x+7,309),(x-7,316)],ACCENT)
    for i,node in enumerate(c['nodes']):
        x=238+i*481
        p+=circle(x,304,139,PAPER,'none')
        p+=f'<g transform="translate({x} 295)">'+icon(node['icon'],0.85)+'</g>'
        p+=text(x,479,node['title'],29,INK,600,'middle')
        p+=lines(x,522,node['lines'],25,MUTED,33,'middle')
        p+=text(x,607,str(i+1).zfill(2),20,ACCENT,500,'middle')
    p+=path('M64 648 H1376',LINE,1)+text(64,688,c['caveat'],25,MUTED)
    return svg(c['title']+' overview',724,p,' '.join(n['title']+': '+' '.join(n['lines']) for n in c['nodes'])+'. '+c['caveat'])

def main():
    global ACCENT,FONT
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--render',action='store_true')
    ap.add_argument('--qa-dir',type=Path)
    args=ap.parse_args()
    c=json.loads((HERE/'artwork.json').read_text())
    OUT.mkdir(parents=True,exist_ok=True)
    ACCENT=c['accent'];FONT=base64.b64encode((HERE/'fonts'/'SpaceGrotesk.ttf').read_bytes()).decode()
    for name,body in [('banner',banner(c)),('overview',overview(c))]:
        (OUT/(name+'.svg')).write_text(body)
    if not args.render:return
    from playwright.sync_api import sync_playwright
    qa=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        try:
            for name,height in [('banner',686),('overview',724)]:
                page=browser.new_page(viewport={'width':W,'height':height},device_scale_factor=2)
                page.goto((OUT/(name+'.svg')).as_uri())
                page.evaluate('document.fonts.ready')
                bounds=page.evaluate("""() => [...document.querySelectorAll('text')].map(e=>{const r=e.getBoundingClientRect();return {text:e.textContent,x:r.x,y:r.y,w:r.width,h:r.height}})""")
                outside=[r for r in bounds if r['x']<24 or r['y']<16 or r['x']+r['w']>W-24 or r['y']+r['h']>height-12]
                overlap=[]
                for i,a in enumerate(bounds):
                    for b in bounds[i+1:]:
                        if min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x'])>2 and min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])>2:
                            overlap.append([a['text'],b['text']])
                if outside or overlap:raise RuntimeError({'asset':name,'outside':outside,'overlap':overlap})
                page.screenshot(path=str(OUT/(name+'.png')))
                qa.append({'asset':name,'text_bounds_checked':len(bounds),'outside':outside,'overlaps':overlap})
                page.close()
        finally:browser.close()
    if args.qa_dir:
        from PIL import Image
        args.qa_dir.mkdir(parents=True,exist_ok=True)
        for name in ['banner','overview']:
            with Image.open(OUT/(name+'.png')) as im:
                im.resize((840,round(im.height*840/im.width)),Image.Resampling.LANCZOS).save(args.qa_dir/(name+'-840.png'))
        (args.qa_dir/'geometry.json').write_text(json.dumps(qa,indent=2))
    print(json.dumps({'title':c['title'],'rendered':2,'geometry':qa}))

if __name__=='__main__':main()
