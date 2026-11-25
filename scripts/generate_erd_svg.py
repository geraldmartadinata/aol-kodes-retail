from pathlib import Path
import subprocess

W, H = 1600, 1080
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
OUT.mkdir(parents=True, exist_ok=True)

entities = [
    {"name":"CUSTOMER", "x":70, "y":120, "w":610, "fields":[
        ("customer_id", "VARCHAR(10)", "PK"), ("customer_name", "VARCHAR(100)", ""),
        ("email", "VARCHAR(150)", "UQ"), ("phone_number", "VARCHAR(30)", ""),
        ("address", "VARCHAR(200)", ""), ("city", "VARCHAR(100)", ""),
        ("customer_type", "VARCHAR(20)", ""), ("country", "VARCHAR(60)", "")], "h": 38+8*40},
    {"name":"INVOICE", "x":920, "y":120, "w":610, "fields":[
        ("invoice_no", "VARCHAR(20)", "PK"), ("invoice_date", "TIMESTAMP", ""),
        ("customer_id", "VARCHAR(10)", "FK"), ("country", "VARCHAR(60)", ""),
        ("status", "VARCHAR(20)", ""), ("payment_method", "VARCHAR(20)", "")], "h": 38+6*40},
    {"name":"PRODUCT", "x":70, "y":650, "w":610, "fields":[
        ("stock_code", "VARCHAR(30)", "PK"), ("description", "VARCHAR(255)", ""),
        ("category", "VARCHAR(50)", ""), ("current_unit_price", "DECIMAL(10,2)", ""),
        ("stock_level", "INT", ""), ("reorder_level", "INT", ""),
        ("last_updated", "TIMESTAMP", "")], "h": 38+7*40},
    {"name":"INVOICE_LINE", "x":920, "y":650, "w":610, "fields":[
        ("invoice_no", "VARCHAR(20)", "FK"), ("stock_code", "VARCHAR(30)", "FK"),
        ("quantity", "INT", ""), ("unit_price_at_sale", "DECIMAL(10,2)", "")], "h": 38+4*40},
]
parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs><filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#0f172a" flood-opacity=".12"/></filter></defs>
<rect width="100%" height="100%" fill="#f1f5f9"/>
<rect width="100%" height="72" fill="#0f172a"/><text x="52" y="46" fill="white" font-family="Segoe UI,Arial" font-size="27" font-weight="700">KoDes Retail — Relational ERD</text>
<text x="52" y="102" fill="#475569" font-family="Segoe UI,Arial" font-size="17">Four entities • inventory attributes merged into PRODUCT • no primary key on INVOICE_LINE</text>
''']
# Relationship connectors in the clear gaps between entity cards.
parts += ['''
<!-- CUSTOMER to INVOICE: one customer may place zero or many invoices -->
<path d="M 680 280 L 920 280" stroke="#334155" stroke-width="2.5" fill="none"/>
<line x1="694" y1="270" x2="694" y2="290" stroke="#334155" stroke-width="2.5"/><line x1="701" y1="270" x2="701" y2="290" stroke="#334155" stroke-width="2.5"/>
<circle cx="899" cy="280" r="5" fill="#f1f5f9" stroke="#334155" stroke-width="2"/>
<path d="M 899 280 L 914 269 M 899 280 L 914 280 M 899 280 L 914 291" stroke="#334155" stroke-width="2.5" fill="none"/>
<rect x="755" y="263" width="90" height="32" rx="6" fill="white" stroke="#cbd5e1"/><text x="800" y="284" text-anchor="middle" fill="#334155" font-family="Segoe UI,Arial" font-size="14">places</text>

<!-- INVOICE to INVOICE_LINE: each detail belongs to one invoice; invoice has one or more details -->
<path d="M 1225 398 L 1225 650" stroke="#334155" stroke-width="2.5" fill="none"/>
<line x1="1215" y1="411" x2="1235" y2="411" stroke="#334155" stroke-width="2.5"/><line x1="1215" y1="418" x2="1235" y2="418" stroke="#334155" stroke-width="2.5"/>
<line x1="1215" y1="632" x2="1235" y2="632" stroke="#334155" stroke-width="2.5"/>
<path d="M 1213 650 L 1225 635 L 1237 650" stroke="#334155" stroke-width="2.5" fill="none"/>
<rect x="1172" y="500" width="106" height="32" rx="6" fill="white" stroke="#cbd5e1"/><text x="1225" y="521" text-anchor="middle" fill="#334155" font-family="Segoe UI,Arial" font-size="14">contains</text>

<!-- PRODUCT to INVOICE_LINE: a product may appear on zero or many details -->
<path d="M 680 800 L 920 800" stroke="#334155" stroke-width="2.5" fill="none"/>
<line x1="694" y1="790" x2="694" y2="810" stroke="#334155" stroke-width="2.5"/><line x1="701" y1="790" x2="701" y2="810" stroke="#334155" stroke-width="2.5"/>
<circle cx="899" cy="800" r="5" fill="#f1f5f9" stroke="#334155" stroke-width="2"/>
<path d="M 899 800 L 914 789 M 899 800 L 914 800 M 899 800 L 914 811" stroke="#334155" stroke-width="2.5" fill="none"/>
<rect x="752" y="783" width="96" height="32" rx="6" fill="white" stroke="#cbd5e1"/><text x="800" y="804" text-anchor="middle" fill="#334155" font-family="Segoe UI,Arial" font-size="14">appears on</text>
''']
for e in entities:
    x,y,w,h=e['x'],e['y'],e['w'],e['h']
    parts.append(f'<g filter="url(#shadow)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="white" stroke="#cbd5e1" stroke-width="1.5"/><path d="M{x+9} {y} H{x+w-9} Q{x+w} {y} {x+w} {y+9} V{y+42} H{x} V{y+9} Q{x} {y} {x+9} {y}" fill="#1e293b"/><text x="{x+24}" y="{y+29}" fill="white" font-family="Segoe UI,Arial" font-size="17" font-weight="700">{e["name"]}</text></g>')
    for i,(name,typ,key) in enumerate(e['fields']):
        ry=y+42+i*40
        fill='#f8fafc' if i%2==0 else '#ffffff'
        parts.append(f'<rect x="{x+1}" y="{ry}" width="{w-2}" height="40" fill="{fill}"/>')
        if key:
            color='#fef3c7' if key=='PK' else ('#dcfce7' if key=='UQ' else '#e0f2fe')
            stroke='#f59e0b' if key=='PK' else ('#16a34a' if key=='UQ' else '#0284c7')
            ink='#92400e' if key=='PK' else ('#166534' if key=='UQ' else '#075985')
            parts.append(f'<rect x="{x+16}" y="{ry+9}" width="35" height="22" rx="4" fill="{color}" stroke="{stroke}"/><text x="{x+33.5}" y="{ry+24}" text-anchor="middle" fill="{ink}" font-family="Segoe UI,Arial" font-size="10" font-weight="700">{key}</text>')
        parts.append(f'<text x="{x+65 if key else x+22}" y="{ry+26}" fill="#1e293b" font-family="Consolas,monospace" font-size="15">{name}</text><text x="{x+w-20}" y="{ry+26}" text-anchor="end" fill="#64748b" font-family="Consolas,monospace" font-size="14">{typ}</text>')
        if i<len(e['fields'])-1: parts.append(f'<line x1="{x+1}" y1="{ry+40}" x2="{x+w-1}" y2="{ry+40}" stroke="#e2e8f0"/>')
parts.append('''
<text x="70" y="1030" fill="#475569" font-family="Segoe UI,Arial" font-size="14">PK = primary key • FK = foreign key • UQ = unique constraint</text>
<text x="920" y="1030" fill="#475569" font-family="Segoe UI,Arial" font-size="14">Foreign keys preserve references; invoice_line has no row-level key by design.</text>
</svg>''')
svg=''.join(parts)
svg_path=OUT/'erd.svg'
svg_path.write_text(svg, encoding='utf-8')
print(f'Wrote {svg_path}')
edge_candidates=[Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'),Path(r'C:\Program Files\Microsoft\Edge\Application\msedge.exe')]
edge=next((p for p in edge_candidates if p.exists()),None)
if edge:
    png=OUT/'erd.png'
    subprocess.run([str(edge),'--headless=new','--disable-gpu',f'--screenshot={png}',f'--window-size={W},{H}',svg_path.as_uri()],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    print(f'Wrote {png}')
else:
    print('Edge unavailable; SVG written, PNG not regenerated.')
