"""
HSS Node Explorer & Connection Designer — Unified App
Upload RISA 3D exports once. All modules share the same data.
Run:  streamlit run hss_node_app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from collections import defaultdict
import io, re, math, datetime, os
import zipfile
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image as RLImage, KeepInFrame
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Line, Circle, String

st.set_page_config(page_title="HSS Node Designer", page_icon="🏗️",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
.stApp{background:#FFFFFF;font-family:'DM Sans',sans-serif}
section[data-testid="stSidebar"]{background:#F8FAFC;border-right:1px solid #E2E8F0}
section[data-testid="stSidebar"] *{font-family:'DM Sans',sans-serif !important}
h1,h2,h3{font-family:'DM Sans',sans-serif !important;font-weight:700 !important;letter-spacing:-0.03em;color:#0F172A !important}
div[data-testid="stMetric"]{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:14px 18px}
div[data-testid="stMetric"] label{color:#64748B !important;font-size:0.72rem !important;text-transform:uppercase;letter-spacing:0.06em;font-weight:600 !important}
div[data-testid="stMetric"] div[data-testid="stMetricValue"]{font-family:'JetBrains Mono',monospace !important;font-size:1.3rem !important;color:#0F172A !important;font-weight:600 !important}
.stTabs [data-baseweb="tab-list"]{border-bottom:2px solid #E2E8F0;gap:0}
.stTabs [data-baseweb="tab"]{font-family:'DM Sans',sans-serif;font-weight:600;color:#64748B;padding:10px 22px;border-bottom:3px solid transparent}
.stTabs [aria-selected="true"]{color:#1E40AF !important;border-bottom:3px solid #1E40AF !important}
.stButton>button{font-family:'DM Sans',sans-serif;font-weight:600;border-radius:8px;padding:0.45rem 1.4rem;border:1px solid #CBD5E1;transition:all 0.18s;background:#FFFFFF;color:#1E3A5F}
.stButton>button:hover{border-color:#1E40AF;color:#1E40AF;background:#EFF6FF}
.chip-pass{background:#F0FDF4;color:#166534;padding:3px 14px;border-radius:20px;font-size:0.83rem;font-weight:600;border:1px solid #BBF7D0;display:inline-block}
.chip-fail{background:#FEF2F2;color:#991B1B;padding:3px 14px;border-radius:20px;font-size:0.83rem;font-weight:600;border:1px solid #FECACA;display:inline-block}
.chip-warn{background:#FEFCE8;color:#854D0E;padding:3px 14px;border-radius:20px;font-size:0.83rem;font-weight:600;border:1px solid #FEF08A;display:inline-block}
.chip-na{background:#F1F5F9;color:#64748B;padding:3px 14px;border-radius:20px;font-size:0.83rem;font-weight:600;border:1px solid #CBD5E1;display:inline-block}
.info-box{background:#F0F7FF;border-left:4px solid #1E40AF;padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;font-size:0.88rem;color:#1E3A5F}
.warn-box{background:#FFFBEB;border-left:4px solid #D97706;padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0;font-size:0.88rem;color:#78350F}
.weld-ok{background:#F0FDF4;border:2px solid #22C55E;border-radius:10px;padding:16px 20px;margin:8px 0}
.weld-fail{background:#FEF2F2;border:2px solid #EF4444;border-radius:10px;padding:16px 20px;margin:8px 0}
.weld-warn{background:#FFFBEB;border:2px solid #F59E0B;border-radius:10px;padding:16px 20px;margin:8px 0}
.check-card{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:14px 18px;margin:6px 0}
.check-pass{border-left:4px solid #22C55E}
.check-fail{border-left:4px solid #EF4444}
.check-na{border-left:4px solid #94A3B8}
.hero{background:linear-gradient(135deg,#0F172A 0%,#1E3A5F 100%);color:white;padding:24px 30px;border-radius:12px;margin-bottom:20px}
.hero h1{color:white !important;margin:0 !important;font-size:1.5rem !important}
.hero p{color:#94A3B8;margin:5px 0 0 0;font-size:0.9rem}
.node-card{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:16px 20px;margin:10px 0}
.credit{position:fixed;bottom:12px;right:16px;background:#F1F5F9;border:1px solid #E2E8F0;border-radius:20px;padding:4px 14px;font-size:0.72rem;color:#64748B;font-family:'DM Sans',sans-serif;z-index:9999}
hr{border-color:#E2E8F0 !important}
</style>
<div class="credit">© Structured Design and Consulting</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SECTION PARSER
# ═══════════════════════════════════════════════════════════════
def parse_hss_section(name):
    if not isinstance(name, str): return None
    n = name.strip().upper()
    m = re.match(r'^HSS(\d+\.?\d*)X(\d+\.?\d*)$', n)
    if m:
        od = float(m.group(1)); wall = float(m.group(2))
        return {'B': od, 'H': od, 't': wall, 'type': 'pipe', 'raw': name}
    m = re.match(r'^HSS(\d+\.?\d*)X(\d+\.?\d*)X(\d+)/(\d+)([A-Z0-9_]*)$', n)
    if m:
        H = float(m.group(1)); B = float(m.group(2))
        t = round(float(m.group(3)) / float(m.group(4)) * 0.93, 4)
        return {'B': B, 'H': H, 't': t, 'type': 'rectangular', 'raw': name}
    m = re.match(r'^HSS(\d+\.?\d*)X(\d+\.?\d*)X(\d+)$', n)
    if m:
        H = float(m.group(1)); B = float(m.group(2))
        t = round(float(m.group(3)) / 16.0 * 0.93, 4)
        return {'B': B, 'H': H, 't': t, 'type': 'rectangular', 'raw': name}
    return None

def get_standard_rect_hss():
    sizes = []
    bases = [(3,3), (4,3), (4,4), (5,5), (6,4), (6,6), (8,6), (8,8), (10,10), (12,8), (12,12), (14,10), (14,14), (16,16)]
    for b, h in bases:
        for t_frac, t_nom in [("3/16", 0.1875), ("1/4", 0.25), ("5/16", 0.3125), ("3/8", 0.375), ("1/2", 0.5), ("5/8", 0.625), ("3/4", 0.75)]:
            t_des = round(t_nom * 0.93, 4)
            sizes.append({'B': max(b,h), 'H': min(b,h), 't': t_des, 'type': 'rectangular', 'raw': f"HSS{max(b,h)}X{min(b,h)}X{t_frac}"})
    return sizes

def get_standard_pipe():
    sizes = []
    ods = [2.375, 2.875, 3.5, 4.0, 4.5, 5.563, 6.625, 8.625, 10.75, 12.75, 14.0, 16.0]
    for od in ods:
        for t_nom in [0.154, 0.216, 0.237, 0.258, 0.280, 0.322, 0.375, 0.5, 0.625]:
            t_des = round(t_nom * 0.93, 4)
            sizes.append({'B': od, 'H': od, 't': t_des, 'type': 'pipe', 'raw': f"HSS{od}X{round(t_nom,3)}"})
    return sizes


# ═══════════════════════════════════════════════════════════════
#  DATA LOADER (WITH POINT-ON-LINE CONTINUOUS DETECTION)
# ═══════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def load_risa_data(nodes_b, members_b, forces_b):
    nodes_df   = pd.read_excel(io.BytesIO(nodes_b))
    members_df = pd.read_excel(io.BytesIO(members_b))
    forces_df  = pd.read_excel(io.BytesIO(forces_b))
    nodes_df.columns   = nodes_df.columns.str.strip()
    members_df.columns = members_df.columns.str.strip()

    nodes = {str(r['Label']).strip(): {
        'x': float(r['X [ft]']), 'y': float(r['Y [ft]']), 'z': float(r['Z [ft]'])
    } for _, r in nodes_df.iterrows()}

    members = {}
    for _, r in members_df.iterrows():
        sec = str(r['Section/Shape']).strip()
        members[str(r['Label']).strip()] = {
            'i_node':  str(r['I Node']).strip(),
            'j_node':  str(r['J Node']).strip(),
            'section': sec,
            'props':   parse_hss_section(sec),
            'material': str(r.get('Material', 'A992')).strip(),
            'pass_through_nodes': []
        }

    forces_df = forces_df.rename(
        columns={c: 'maxmin' for c in forces_df.columns if str(c).strip() == ''})
    forces_df['Member'] = forces_df['Member'].astype(str).str.strip()
    forces_df['maxmin'] = forces_df['maxmin'].astype(str).str.strip().str.lower()

    def col(kw):
        return next((c for c in forces_df.columns if kw.lower() in c.lower()), None)

    member_forces = {}
    for mid, grp in forces_df.groupby('Member'):
        mx = grp[grp['maxmin'] == 'max']
        mn = grp[grp['maxmin'] == 'min']
        def env(c):
            if not c: return (0.0, 0.0)
            try:
                pos = pd.to_numeric(mx[c], errors='coerce').max()
                neg = pd.to_numeric(mn[c], errors='coerce').min()
                return (float(pos) if not pd.isna(pos) else 0.0,
                        float(neg) if not pd.isna(neg) else 0.0)
            except: return (0.0, 0.0)
        member_forces[mid] = {
            'axial':  env(col('axial')),
            'vy':     env(col('y shear')),
            'vz':     env(col('z shear')),
            'torque': env(col('torque')),
            'myy':    env(col('y-y moment')),
            'mzz':    env(col('z-z moment')),
        }

    n2m = defaultdict(list)
    for mid, m in members.items():
        n2m[m['i_node']].append(mid)
        n2m[m['j_node']].append(mid)

    # 🚀 POINT-ON-LINE GEOMETRIC ENGINE
    # Scans for intermediate/orphan nodes lying geometrically on the 3D line of a continuous member
    for nid, nd in nodes.items():
        nx, ny, nz = nd['x'], nd['y'], nd['z']
        for mid, m in members.items():
            if m['i_node'] == nid or m['j_node'] == nid:
                continue
            i_nd = nodes.get(m['i_node'])
            j_nd = nodes.get(m['j_node'])
            if not i_nd or not j_nd: continue
            
            # Vector I to J
            vx, vy, vz = j_nd['x']-i_nd['x'], j_nd['y']-i_nd['y'], j_nd['z']-i_nd['z']
            len_ij = math.sqrt(vx**2 + vy**2 + vz**2)
            if len_ij < 1e-6: continue
            
            # Vector I to Selected Node (N)
            v_inx, v_iny, v_inz = nx-i_nd['x'], ny-i_nd['y'], nz-i_nd['z']
            
            # Project IN onto IJ
            t = (v_inx*vx + v_iny*vy + v_inz*vz) / (len_ij**2)
            if 0.001 < t < 0.999: # Ensures the point is strictly between I and J
                # Perpendicular intersection point on the line
                px = i_nd['x'] + t*vx
                py = i_nd['y'] + t*vy
                pz = i_nd['z'] + t*vz
                # Distance from node to the line
                dist = math.sqrt((nx-px)**2 + (ny-py)**2 + (nz-pz)**2)
                
                # Tolerance check (within 0.05 ft / ~0.6 inches)
                if dist < 0.05:
                    n2m[nid].append(mid)
                    m['pass_through_nodes'].append(nid)

    return nodes, members, member_forces, dict(n2m)


# ═══════════════════════════════════════════════════════════════
#  GEOMETRY HELPERS
# ═══════════════════════════════════════════════════════════════
def member_length_ft(nodes, m):
    i = nodes[m['i_node']]; j = nodes[m['j_node']]
    return math.sqrt((i['x']-j['x'])**2+(i['y']-j['y'])**2+(i['z']-j['z'])**2)

def unit_vec(nodes, m, from_node):
    nd = nodes[from_node]
    if m['i_node'] == from_node:
        other = nodes[m['j_node']]
    elif m['j_node'] == from_node:
        other = nodes[m['i_node']]
    else:
        # Pass-through continuous member
        i_nd = nodes[m['i_node']]; j_nd = nodes[m['j_node']]
        v = np.array([j_nd['x']-i_nd['x'], j_nd['y']-i_nd['y'], j_nd['z']-i_nd['z']])
        n = np.linalg.norm(v)
        return v/n if n > 1e-9 else v

    v = np.array([other['x']-nd['x'], other['y']-nd['y'], other['z']-nd['z']])
    n = np.linalg.norm(v)
    return v/n if n > 1e-9 else v

def angle_between(nodes, m1, m2, nid):
    u1 = unit_vec(nodes, m1, nid); u2 = unit_vec(nodes, m2, nid)
    # Native 3D angle. We adjust obtuse angles dynamically in the orchestrator later.
    return math.degrees(math.acos(np.clip(np.dot(u1, u2), -1.0, 1.0)))

def gf(t):
    a, b = t; return a if abs(a) >= abs(b) else b

def max_abs(t):
    return max(abs(t[0]), abs(t[1]))

def ncc(c):
    return "#94A3B8" if c<=2 else "#1E40AF" if c<=4 else "#D97706" if c<=6 else "#DC2626"

def ncl(c):
    return "Simple" if c<=2 else "Typical" if c<=4 else "Complex" if c<=6 else "Critical"


# ═══════════════════════════════════════════════════════════════
#  PLOTLY FIGURES (Y-AXIS UP)
# ═══════════════════════════════════════════════════════════════
def build_3d_full(nodes, members, n2m, highlight=None):
    fig = go.Figure()
    for mid, m in members.items():
        if m['i_node'] not in nodes or m['j_node'] not in nodes: continue
        i = nodes[m['i_node']]; j = nodes[m['j_node']]
        
        is_hl_connected = False
        if highlight:
            is_hl_connected = (highlight in [m['i_node'], m['j_node']] or highlight in m.get('pass_through_nodes', []))

        color = "#1E40AF" if is_hl_connected else ("#374151" if m['props'] else "#9CA3AF")
        fig.add_trace(go.Scatter3d(
            x=[i['x'],j['x']], y=[i['y'],j['y']], z=[i['z'],j['z']],
            mode='lines', line=dict(color=color, width=5 if is_hl_connected else (3 if m['props'] else 1.5)),
            opacity=1.0 if is_hl_connected else (0.45 if highlight else 0.8),
            showlegend=False,
            hovertemplate=f"<b>{mid}</b><br>{m['section']}<br>{m['i_node']}→{m['j_node']}<extra></extra>"))
    xs,ys,zs,cs,ss,ts = [],[],[],[],[],[]
    for nid, nd in nodes.items():
        cnt = len(n2m.get(nid, []))
        xs.append(nd['x']); ys.append(nd['y']); zs.append(nd['z'])
        cs.append(ncc(cnt)); ss.append(12 if nid==highlight else (7 if cnt>=5 else 5))
        ts.append(f"<b>{nid}</b><br>({nd['x']:.2f},{nd['y']:.2f},{nd['z']:.2f})<br>{cnt} members")
    fig.add_trace(go.Scatter3d(x=xs,y=ys,z=zs, mode='markers',
        marker=dict(color=cs,size=ss,line=dict(color='white',width=0.5)),
        text=ts, hovertemplate="%{text}<extra></extra>", showlegend=False))
    if highlight and highlight in nodes:
        nd = nodes[highlight]
        fig.add_trace(go.Scatter3d(x=[nd['x']],y=[nd['y']],z=[nd['z']],
            mode='markers+text', marker=dict(color='#DC2626',size=14,line=dict(color='white',width=2)),
            text=[highlight], textposition='top center',
            textfont=dict(size=13,color='#DC2626'), showlegend=False, hoverinfo='skip'))
    
    fig.update_layout(
        scene=dict(
            camera=dict(up=dict(x=0, y=1, z=0)),
            xaxis=dict(title='X (ft)',showbackground=False,gridcolor='#E2E8F0'),
            yaxis=dict(title='Y (ft)',showbackground=False,gridcolor='#E2E8F0'),
            zaxis=dict(title='Z (ft)',showbackground=False,gridcolor='#E2E8F0'),
            bgcolor='white', aspectmode='data'),
        paper_bgcolor='white', margin=dict(l=0,r=0,b=0,t=0),
        showlegend=False, uirevision='structure')
    return fig


def build_node_zoom(nodes, members, n2m, sel):
    fig = go.Figure()
    nd = nodes[sel]; ARM=0.35
    COLS=['#1E40AF','#D97706','#16A34A','#9333EA','#DC2626','#0891B2','#EA580C','#BE185D']
    
    for idx, mid in enumerate(n2m.get(sel,[])):
        m = members.get(mid)
        if not m: continue
        c = COLS[idx%len(COLS)]
        
        is_pass_through = (sel in m.get('pass_through_nodes', []))
        tips = []
        if is_pass_through:
            tips = [nodes[m['i_node']], nodes[m['j_node']]]
        else:
            ok = m['j_node'] if m['i_node']==sel else m['i_node']
            if ok in nodes: tips = [nodes[ok]]
            
        for tip in tips:
            ex=nd['x']+(tip['x']-nd['x'])*ARM; ey=nd['y']+(tip['y']-nd['y'])*ARM; ez=nd['z']+(tip['z']-nd['z'])*ARM
            fig.add_trace(go.Scatter3d(x=[nd['x'],ex],y=[nd['y'],ey],z=[nd['z'],ez],
                mode='lines+text', line=dict(color=c,width=6 if m['props'] else 3),
                text=['',mid], textposition='top center', textfont=dict(size=11,color='#0F172A'),
                showlegend=False, hovertemplate=f"<b>{mid}</b><br>{m['section']}<extra></extra>"))

    fig.add_trace(go.Scatter3d(x=[nd['x']],y=[nd['y']],z=[nd['z']],
        mode='markers+text', marker=dict(color='#DC2626',size=12,line=dict(color='white',width=2)),
        text=[f"<b>{sel}</b>"], textposition='top center', textfont=dict(size=14,color='#DC2626'),
        showlegend=False, hoverinfo='skip'))
    
    fig.update_layout(
        scene=dict(
            camera=dict(up=dict(x=0, y=1, z=0)),
            xaxis=dict(showbackground=False,gridcolor='#E2E8F0'),
            yaxis=dict(showbackground=False,gridcolor='#E2E8F0'),
            zaxis=dict(showbackground=False,gridcolor='#E2E8F0'),
            bgcolor='white', aspectmode='data'),
        paper_bgcolor='white', margin=dict(l=0,r=0,b=10,t=10), showlegend=False)
    return fig


def build_node_solid_zoom(nodes, members, n2m, sel):
    fig = go.Figure()
    nd = nodes[sel]
    ARM = 0.35 
    COLS = ['#1E40AF', '#D97706', '#16A34A', '#9333EA', '#DC2626', '#0891B2', '#EA580C', '#BE185D']
    
    fig.add_trace(go.Scatter3d(x=[nd['x']], y=[nd['y']], z=[nd['z']],
        mode='markers+text', marker=dict(color='#DC2626',size=8,line=dict(color='white',width=2)),
        text=[f"<b>{sel}</b>"], textposition='top center', textfont=dict(size=14,color='#DC2626'),
        showlegend=False, hoverinfo='skip'))

    for idx, mid in enumerate(n2m.get(sel, [])):
        m = members.get(mid)
        if not m or not m['props']: continue
        mesh_color = COLS[idx % len(COLS)]
        
        is_pass_through = (sel in m.get('pass_through_nodes', []))
        tips = []
        if is_pass_through:
            tips = [nodes[m['i_node']], nodes[m['j_node']]]
        else:
            ok = m['j_node'] if m['i_node'] == sel else m['i_node']
            if ok in nodes: tips = [nodes[ok]]
            
        for tip in tips:
            v = np.array([tip['x'] - nd['x'], tip['y'] - nd['y'], tip['z'] - nd['z']])
            L = np.linalg.norm(v)
            if L < 1e-9: continue
            Z_loc = v / L
            
            Y_glob = np.array([0, 1, 0])
            if abs(np.dot(Z_loc, Y_glob)) > 0.999:
                X_loc = np.array([1, 0, 0])
            else:
                X_loc = np.cross(Y_glob, Z_loc)
                X_loc /= np.linalg.norm(X_loc)
            Y_loc = np.cross(Z_loc, X_loc)
            
            B = m['props']['B'] / 12.0
            H = m['props']['H'] / 12.0
            arm_len = L * ARM
            
            if m['props']['type'] == 'rectangular':
                verts_local = [
                    [-B/2, -H/2, 0], [B/2, -H/2, 0], [B/2, H/2, 0], [-B/2, H/2, 0],
                    [-B/2, -H/2, arm_len], [B/2, -H/2, arm_len], [B/2, H/2, arm_len], [-B/2, H/2, arm_len]
                ]
                vx, vy, vz = [], [], []
                for vl in verts_local:
                    vg = np.array([nd['x'], nd['y'], nd['z']]) + vl[0]*X_loc + vl[1]*Y_loc + vl[2]*Z_loc
                    vx.append(vg[0]); vy.append(vg[1]); vz.append(vg[2])
                
                i = [0, 1, 5, 4, 1, 2, 6, 5, 2, 3, 7, 6, 3, 0, 4, 7, 4, 5, 6, 7, 0, 3, 2, 1]
                j = [1, 5, 4, 0, 2, 6, 5, 1, 3, 7, 6, 2, 0, 4, 7, 3, 5, 6, 7, 4, 3, 2, 1, 0]
                k = [5, 4, 0, 1, 6, 5, 1, 2, 7, 6, 2, 3, 4, 7, 3, 0, 6, 7, 4, 5, 2, 1, 0, 3]
                
                fig.add_trace(go.Mesh3d(x=vx, y=vy, z=vz, i=i, j=j, k=k,
                    color=mesh_color, opacity=0.9, flatshading=True, name=mid, hoverinfo='name', showlegend=False))
                
            elif m['props']['type'] == 'pipe':
                num_pts = 16
                vx, vy, vz = [], [], []
                for z_val in [0, arm_len]:
                    for ang in np.linspace(0, 2*np.pi, num_pts, endpoint=False):
                        xl = (B/2) * math.cos(ang)
                        yl = (B/2) * math.sin(ang)
                        vg = np.array([nd['x'], nd['y'], nd['z']]) + xl*X_loc + yl*Y_loc + z_val*Z_loc
                        vx.append(vg[0]); vy.append(vg[1]); vz.append(vg[2])
                        
                i, j, k = [], [], []
                for p in range(num_pts):
                    p1 = p
                    p2 = (p + 1) % num_pts
                    p3 = p + num_pts
                    p4 = p2 + num_pts
                    i.extend([p1, p2]); j.extend([p2, p4]); k.extend([p3, p3])
                    
                fig.add_trace(go.Mesh3d(x=vx, y=vy, z=vz, i=i, j=j, k=k,
                    color=mesh_color, opacity=0.9, flatshading=True, name=mid, hoverinfo='name', showlegend=False))

    fig.update_layout(
        scene=dict(
            camera=dict(up=dict(x=0, y=1, z=0)),
            xaxis=dict(showbackground=False, gridcolor='#E2E8F0', visible=False),
            yaxis=dict(showbackground=False, gridcolor='#E2E8F0', visible=False),
            zaxis=dict(showbackground=False, gridcolor='#E2E8F0', visible=False),
            bgcolor='white', aspectmode='data'),
        paper_bgcolor='white', margin=dict(l=0, r=0, b=10, t=10), showlegend=False)
    return fig


def check_equilibrium(nodes, members, member_forces, n2m, node_id):
    nd = nodes[node_id]; Fx=Fy=Fz=0.0
    for mid in n2m.get(node_id,[]):
        m=members.get(mid,{}); mf=member_forces.get(mid,{})
        axial=gf(mf.get('axial',(0,0)))
        i_nd=nodes.get(m.get('i_node','')); j_nd=nodes.get(m.get('j_node',''))
        if not i_nd or not j_nd: continue
        
        if m['i_node']==node_id: dx,dy,dz=j_nd['x']-nd['x'],j_nd['y']-nd['y'],j_nd['z']-nd['z']
        elif m['j_node']==node_id: dx,dy,dz=i_nd['x']-nd['x'],i_nd['y']-nd['y'],i_nd['z']-nd['z']
        else: continue # Skip pass-through members for node equilibrium check
        
        L=(dx**2+dy**2+dz**2)**0.5
        if L<1e-9: continue
        Fx+=axial*(dx/L); Fy+=axial*(dy/L); Fz+=axial*(dz/L)
    R=(Fx**2+Fy**2+Fz**2)**0.5
    return Fx,Fy,Fz, R<5.0


# ═══════════════════════════════════════════════════════════════
#  CHORD DETECTION
# ═══════════════════════════════════════════════════════════════
def detect_chord(node_id, hss_mids, nodes, members, member_forces):
    # Priority 1: Continuous pass-through member
    pass_throughs = [m for m in hss_mids if node_id in members.get(m, {}).get('pass_through_nodes', [])]
    if pass_throughs:
        chord = max(pass_throughs, key=lambda m: members[m]['props']['B'])
        return chord, "Continuous member passing through node"

    # Priority 2: Co-linear
    scores = {}
    for mid in hss_mids:
        p = members.get(mid,{}).get('props')
        if not p: continue
        scores[mid] = {'B': p['B'], 'axial_abs': max_abs(member_forces.get(mid,{}).get('axial',(0,0))), 'partner': None}
    mlist = list(scores.keys())
    for i in range(len(mlist)):
        for j in range(i+1, len(mlist)):
            if mlist[i] not in members or mlist[j] not in members: continue
            ang = angle_between(nodes, members[mlist[i]], members[mlist[j]], node_id)
            if ang > 90.0: ang = 180.0 - ang # Normalize obtuse angles
            if ang < 20.0:
                a,b = mlist[i],mlist[j]
                if scores[a]['B'] >= scores[b]['B']: scores[a]['partner'] = b
                else: scores[b]['partner'] = a
    has_cl = [(m,s) for m,s in scores.items() if s['partner']]
    if has_cl:
        chord = max(has_cl, key=lambda x: x[1]['B'])[0]
        reason = f"Co-linear with {scores[chord]['partner']} (angle <20°)"
    elif scores:
        chord = max(scores.keys(), key=lambda m:(scores[m]['B'],scores[m]['axial_abs']))
        reason = "Largest section / highest axial"
    else:
        chord = hss_mids[0] if hss_mids else None
        reason = "Default"
    return chord, reason


# ═══════════════════════════════════════════════════════════════
#  AISC 360-22 CHAPTER K — LIMIT STATE CHECKS
# ═══════════════════════════════════════════════════════════════
def _check(name, ref, phi_r, Rn, Ru, unit='kips', note='', formula=''):
    pR = phi_r * Rn
    uc = abs(Ru) / pR if pR > 1e-9 else 0.0
    return dict(name=name, ref=ref, phi=phi_r, Rn=Rn, phiRn=pR, Ru=abs(Ru),
                uc=uc, unit=unit, status='PASS' if uc<=1.0 else 'FAIL',
                status_na=False, note=note, formula=formula, hint='')

def _na(name, ref, note):
    return dict(name=name, ref=ref, phi='-', Rn=0, phiRn=0, Ru=0, uc=0,
                unit='kips', status='N/A', status_na=True, note=note, formula='', hint='')


def check_rect_to_rect(chord_p, branch_p, bf, theta_deg, Qf,
                        chord_Fy=50.0, branch_Fy=50.0, E=29000.0):
    checks = []; phi=0.90
    theta = math.radians(max(theta_deg, 30.0)); sin_t = math.sin(theta)
    B=chord_p['B']; H=chord_p['H']; t=chord_p['t']
    Bb=branch_p['B']; Hb=branch_p['H']; tb=branch_p['t']
    beta=Bb/B; gamma=B/(2*t); eta=Hb/B
    be_oi = min(10*(t/tb)*(chord_Fy*t)/(branch_Fy*Bb), Bb)
    Pu=gf(bf['axial']); Vu=gf(bf.get('vy',(0,0))); Vz=gf(bf.get('vz',(0,0)))
    V=math.sqrt(Vu**2+Vz**2)
    Myy=gf(bf.get('myy',(0,0))); Mzz=gf(bf.get('mzz',(0,0)))

    checks.append(dict(name="Chord B/t ≤ 35",ref="AISC K1.3",phi='-',Rn='-',phiRn=35.0,
        Ru=round(B/t,2),uc=(B/t)/35,unit='ratio',note='',
        status='PASS' if B/t<=35 else 'FAIL', status_na=False,
        formula=f"B/t = {B}/{t:.4f} = {B/t:.2f}  ≤  35"))
    lim_br = 1.25*math.sqrt(E/branch_Fy)
    checks.append(dict(name="Branch Bb/tb",ref="Table K4.2A",phi='-',Rn='-',phiRn=round(lim_br,2),
        Ru=round(Bb/tb,2),uc=(Bb/tb)/lim_br,unit='ratio',note='',
        status='PASS' if Bb/tb<=lim_br else 'FAIL', status_na=False,
        formula=f"Bb/tb = {Bb}/{tb:.4f} = {Bb/tb:.2f}  ≤  {lim_br:.2f}"))
    checks.append(dict(name="Width ratio β",ref="AISC K3.3",phi='-',Rn='-',phiRn=1.0,
        Ru=round(beta,3), uc=0 if 0.25<=beta<=1.0 else 1.5, unit='ratio',
        note=f'β={beta:.3f}', status='PASS' if 0.25<=beta<=1.0 else 'FAIL', status_na=False,
        formula=f"β = Bb/B = {Bb}/{B} = {beta:.3f}  (req. 0.25 ≤ β ≤ 1.0)"))

    if beta < 1.0:
        Rn_p = chord_Fy*t**2/sin_t*(2*eta/sin_t+4*(1-beta)**0.5)*Qf
        checks.append(_check("Chord Face Plastification","AISC K2-1",phi,Rn_p,Pu,
            note=f'β={beta:.3f}, η={eta:.3f}, Qf={Qf:.3f}',
            formula=(f"φPn = φ·Fy·t²/sinθ·(2η/sinθ + 4√(1−β))·Qf\n"
                     f"     = {phi}·{chord_Fy}·{t:.4f}²/{sin_t:.4f}·(2·{eta:.3f}/{sin_t:.4f} + 4·√(1−{beta:.3f}))·{Qf:.3f}\n"
                     f"     = {phi*Rn_p:.2f} kips")))
    else:
        checks.append(_na("Chord Face Plastification","AISC K2-1","N/A: β = 1.0"))

    if beta >= 0.85:
        Rn_sw = 2*chord_Fy*t*(Hb/sin_t+5*t)
        checks.append(_check("Chord Sidewall Yielding","AISC K2-2",1.00,Rn_sw,Pu,
            formula=(f"φPn = 1.0·2·Fy·t·(Hb/sinθ + 5t)\n"
                     f"     = 2·{chord_Fy}·{t:.4f}·({Hb}/{sin_t:.4f} + 5·{t:.4f})\n"
                     f"     = {Rn_sw:.2f} kips")))
    else:
        checks.append(_na("Chord Sidewall Yielding","AISC K2-2","N/A: β < 0.85"))

    if beta >= 0.85:
        Rn_cr = 1.6*t**2*(1+3*Hb/(H*sin_t))*math.sqrt(E*chord_Fy)*Qf
        checks.append(_check("Chord Sidewall Crippling","AISC K2-3",0.75,Rn_cr,Pu,
            formula=f"φPn = 0.75·1.6t²·(1+3Hb/(H·sinθ))·√(E·Fy)·Qf = {0.75*Rn_cr:.2f} kips"))
    else:
        checks.append(_na("Chord Sidewall Crippling","AISC K2-3","N/A: β < 0.85"))

    Ag_eff = tb*(2*Hb+2*be_oi-4*tb)
    Rn_br = branch_Fy*Ag_eff
    checks.append(_check("Branch Local Yielding","AISC K2-5",phi,Rn_br,Pu,
        note=f'be_oi={be_oi:.3f}"  Ag_eff={Ag_eff:.3f} in²',
        formula=(f"φPn = φ·Fyb·(2Hb + 2·be_oi − 4tb)·tb\n"
                 f"     be_oi = min[10(t/tb)(Fyt)/(Fyb·Bb), Bb] = {be_oi:.4f}\"\n"
                 f"     Ag_eff = {Ag_eff:.3f} in²\n"
                 f"     φPn = {phi}·{branch_Fy}·{Ag_eff:.3f} = {phi*Rn_br:.2f} kips")))

    Av = 2*Hb*tb
    checks.append(_check("Branch Shear","AISC J4.2",phi,0.6*branch_Fy*Av,V,
        note=f'Av={Av:.3f} in²',
        formula=f"φVn = φ·0.6·Fyb·Av = {phi}·0.6·{branch_Fy}·{Av:.3f} = {phi*0.6*branch_Fy*Av:.2f} kips"))

    if abs(Mzz) > 0.05:
        Ze = tb*(Hb**2/4+Hb*be_oi/2)
        Mn = branch_Fy*Ze/12.0
        checks.append(_check("Moment In-Plane","AISC K2+DG24",phi,Mn,abs(Mzz),unit='kip-ft',
            formula=f"φMn = φ·Fyb·Ze/12  Ze≈{Ze:.3f} in³  φMn={phi*Mn:.2f} kip-ft"))
    if abs(Myy) > 0.05:
        Ze = tb*(Bb**2/4+Bb*be_oi/2)
        Mn = branch_Fy*Ze/12.0
        checks.append(_check("Moment Out-of-Plane","AISC K2+DG24",phi,Mn,abs(Myy),unit='kip-ft',
            formula=f"φMn = φ·Fyb·Ze/12  Ze≈{Ze:.3f} in³  φMn={phi*Mn:.2f} kip-ft"))

    return checks, dict(beta=beta,gamma=gamma,eta=eta,be_oi=be_oi,B_t=B/t,theta_deg=theta_deg)


def check_round_to_rect(chord_p, branch_p, bf, theta_deg, Qf,
                         chord_Fy=50.0, branch_Fy=50.0, E=29000.0):
    checks = []; phi=0.90
    theta = math.radians(max(theta_deg, 30.0)); sin_t = math.sin(theta)
    D=chord_p['B']; t=chord_p['t']
    Bb=branch_p['B']; Hb=branch_p['H']; tb=branch_p['t']
    beta=Bb/D; gamma=D/(2*t); eta=Hb/D
    Pu=gf(bf['axial']); Vu=gf(bf.get('vy',(0,0))); Vz=gf(bf.get('vz',(0,0)))
    V=math.sqrt(Vu**2+Vz**2)
    Mzz=gf(bf.get('mzz',(0,0))); Myy=gf(bf.get('myy',(0,0)))

    checks.append(dict(name="Chord D/t ≤ 50",ref="AISC K3.3",phi='-',Rn='-',phiRn=50.0,
        Ru=round(D/t,2),uc=(D/t)/50,unit='ratio',note='',
        status='PASS' if D/t<=50 else 'FAIL', status_na=False,
        formula=f"D/t = {D}/{t} = {D/t:.2f}  ≤  50"))
    checks.append(dict(name="Width ratio β = Bb/D",ref="AISC K3.3",phi='-',Rn='-',phiRn=1.0,
        Ru=round(beta,3), uc=0 if 0.2<=beta<=1.0 else 1.5, unit='ratio',
        note=f'β={beta:.3f}', status='PASS' if 0.2<=beta<=1.0 else 'FAIL', status_na=False,
        formula=f"β = Bb/D = {Bb}/{D} = {beta:.3f}  (req. 0.2 ≤ β ≤ 1.0)"))

    if beta <= 0.5:
        Rn_p = 5.7*chord_Fy*t**2/sin_t*gamma**0.2*Qf
        checks.append(_check("Chord Face Plastification","AISC K3-1",phi,Rn_p,Pu,
            note=f'γ={gamma:.2f}, β≤0.5',
            formula=(f"φPn = φ·5.7·Fy·t²/sinθ·γ⁰·²·Qf\n"
                     f"     γ=D/(2t)={D}/(2·{t})={gamma:.2f}\n"
                     f"     φPn={phi}·5.7·{chord_Fy}·{t:.4f}²/{sin_t:.4f}·{gamma:.2f}^0.2·{Qf:.3f}={phi*Rn_p:.2f} kips")))
    else:
        Rn_p = chord_Fy*t**2*(3.1+15.6*beta**2)*gamma**0.2*Qf/sin_t
        checks.append(_check("Chord Face Plastification","AISC K3-2",phi,Rn_p,Pu,
            note=f'γ={gamma:.2f}, β={beta:.3f}',
            formula=(f"φPn = φ·Fy·t²·(3.1+15.6β²)·γ⁰·²·Qf/sinθ\n"
                     f"     = {phi}·{chord_Fy}·{t:.4f}²·(3.1+15.6·{beta:.3f}²)·{gamma:.2f}^0.2·{Qf:.3f}/{sin_t:.4f}\n"
                     f"     = {phi*Rn_p:.2f} kips")))

    Av=2*Hb*tb; Rn_v=0.6*branch_Fy*Av
    checks.append(_check("Branch Shear","AISC J4.2",phi,Rn_v,V,
        note=f'Av={Av:.3f} in²',
        formula=(f"φVn = φ·0.6·Fyb·Av\n"
                 f"     Av=2·Hb·tb=2·{Hb}·{tb:.4f}={Av:.3f} in²\n"
                 f"     φVn={phi}·0.6·{branch_Fy}·{Av:.3f}={phi*Rn_v:.2f} kips")))

    if abs(Mzz) > 0.05:
        F_eq = abs(Mzz)*12.0/(0.9*Hb); comb=abs(Pu)+F_eq; pR=phi*Rn_p
        uc = comb/pR if pR>1e-9 else 0
        checks.append(dict(name="Axial+Moment Interaction",ref="DG24 §4.3",phi=phi,
            Rn=Rn_p,phiRn=pR,Ru=comb,uc=uc,unit='kips',
            status='PASS' if uc<=1.0 else 'FAIL', status_na=False,
            note=f'F_equiv={F_eq:.2f}k',
            formula=(f"(Pu + F_equiv)/φPn ≤ 1.0\n"
                     f"     F_equiv=|Mzz|·12/(0.9·Hb)={abs(Mzz):.3f}·12/(0.9·{Hb})={F_eq:.2f} k\n"
                     f"     ({abs(Pu):.2f}+{F_eq:.2f})/{pR:.2f} = {uc:.3f}")))

    return checks, dict(beta=beta,gamma=gamma,eta=eta,D_t=D/t,theta_deg=theta_deg)


# ═══════════════════════════════════════════════════════════════
#  NEXT-UP SIZING & EXACT REQUIREMENT SOLVER
# ═══════════════════════════════════════════════════════════════
def find_next_size(chord_p, branch_p, bf, theta_deg, Qf, chord_Fy, branch_Fy, failed_check_name, target='chord'):
    p_to_iterate = chord_p if target == 'chord' else branch_p
    std_sizes = get_standard_rect_hss() if p_to_iterate['type'] == 'rectangular' else get_standard_pipe()
    
    for test_p in std_sizes:
        if test_p['B'] < p_to_iterate['B'] - 1e-3 or test_p['H'] < p_to_iterate['H'] - 1e-3 or test_p['t'] < p_to_iterate['t'] - 1e-3:
            continue
        if abs(test_p['B'] - p_to_iterate['B']) < 1e-3 and abs(test_p['H'] - p_to_iterate['H']) < 1e-3 and abs(test_p['t'] - p_to_iterate['t']) < 1e-3:
            continue
            
        test_chord = test_p if target == 'chord' else chord_p
        test_branch = test_p if target == 'branch' else branch_p
        
        if test_chord['type'] == 'pipe':
            c, _ = check_round_to_rect(test_chord, test_branch, bf, theta_deg, Qf, chord_Fy, branch_Fy)
        else:
            c, _ = check_rect_to_rect(test_chord, test_branch, bf, theta_deg, Qf, chord_Fy, branch_Fy)
            
        for chk in c:
            if chk['name'] == failed_check_name and chk['status'] == 'PASS':
                return test_p['raw']
    return None

def get_exact_req(failed_check_name, chord_p, branch_p, bf, theta_deg, Qf, chord_Fy, branch_Fy):
    """
    Reverse-engineers the exact dimension required to satisfy a limit state.
    """
    if failed_check_name in ["Chord Face Plastification", "Chord Sidewall Yielding", "Chord Sidewall Crippling", "Chord B/t ≤ 35", "Chord D/t ≤ 50", "Axial+Moment Interaction"]:
        param = 't'; is_chord = True; name_str = "Chord t"
    elif failed_check_name in ["Branch Local Yielding", "Branch Shear"]:
        param = 't'; is_chord = False; name_str = "Branch tb"
    else:
        return None, 0, 0, ""

    cur_val = chord_p[param] if is_chord else branch_p[param]
    test_val = cur_val
    step = 0.005 # Highly precise iteration
    
    for _ in range(400): 
        test_val += step
        test_chord = chord_p.copy()
        test_branch = branch_p.copy()
        if is_chord: test_chord[param] = test_val
        else: test_branch[param] = test_val
        
        if test_chord['type'] == 'pipe':
            c, _ = check_round_to_rect(test_chord, test_branch, bf, theta_deg, Qf, chord_Fy, branch_Fy)
        else:
            c, _ = check_rect_to_rect(test_chord, test_branch, bf, theta_deg, Qf, chord_Fy, branch_Fy)
        
        chk = next((x for x in c if x['name'] == failed_check_name), None)
        if chk and chk['status'] == 'PASS':
            return name_str, test_val, cur_val, "in."
            
    return None, 0, 0, ""


# ═══════════════════════════════════════════════════════════════
#  WELD DESIGN ENGINE WITH AUTO-ITERATION
# ═══════════════════════════════════════════════════════════════
def design_weld(branch_p, chord_p, bf, theta_deg,
                chord_Fy=50.0, branch_Fy=50.0, FEXX=70.0,
                conn_type='moment', user_D16=None):
    phi_w=0.75
    t=chord_p['t']; Bb=branch_p['B']; Hb=branch_p['H']; tb=branch_p['t']
    Pu=gf(bf['axial']); Vu=gf(bf.get('vy',(0,0))); Vz=gf(bf.get('vz',(0,0)))
    Myy=gf(bf.get('myy',(0,0))); Mzz=gf(bf.get('mzz',(0,0))); T=gf(bf.get('torque',(0,0)))
    V_total=math.sqrt(Vu**2+Vz**2)
    F_myy = abs(Myy)*12.0/(0.9*Bb) if Bb>0 else 0.0
    F_mzz = abs(Mzz)*12.0/(0.9*Hb) if Hb>0 else 0.0
    perimeter = 2*(Bb+Hb)
    V_tor = abs(T)*12.0/(perimeter/(2*math.pi)) if perimeter>0 else 0.0

    if conn_type=='pinned':
        F_total = math.sqrt(Pu**2+V_total**2)
    else:
        F_total = math.sqrt((abs(Pu)+F_mzz+F_myy)**2+(V_total+V_tor)**2)
    F_total = max(F_total, 0.001)

    t_thin = min(t, tb)
    D16_min = 2 if t_thin<=0.25 else 3 if t_thin<=0.5 else 4 if t_thin<=0.75 else 5
    D16_max = max(2, math.floor(tb*16))

    def calc_phi_rn(d16):
        return phi_w*0.6*FEXX*0.707*(d16/16)*perimeter

    if user_D16 and isinstance(user_D16, int) and 2<=user_D16<=16:
        D16_prov = user_D16
    else:
        cap_per_16th = calc_phi_rn(1)
        D16_req = F_total/cap_per_16th if cap_per_16th>0 else 2.0
        D16_prov = max(math.ceil(D16_req), D16_min)
        D16_prov = min(max(D16_prov, 2), D16_max)

    weld_override_note = ""
    orig_D16 = D16_prov
    
    if F_total > calc_phi_rn(D16_prov):
        for test_d in range(D16_prov + 1, 9):
            if F_total <= calc_phi_rn(test_d):
                weld_override_note = f"💡 Increased weld size from {orig_D16}/16\" to {test_d}/16\" to make member pass."
                D16_prov = test_d
                break

    phi_Rn = calc_phi_rn(D16_prov)
    uc_weld = F_total/phi_Rn if phi_Rn>0 else 0.0
    Rn_BM = 1.0*0.6*branch_Fy*tb*perimeter
    uc_BM = F_total/Rn_BM if Rn_BM>0 else 0.0

    Rn_per_in = phi_w*0.6*FEXX*0.707*(D16_prov/16)
    L_req = F_total/Rn_per_in if Rn_per_in>0 else perimeter
    perim_ok = L_req <= perimeter
    perim_note = ""
    if not perim_ok:
        perim_note = (f"⚠ Perimeter insufficient: L_req={L_req:.2f}\" > perimeter={perimeter:.2f}\". "
                      f"Increase weld size to {min(D16_prov+1,D16_max)}/16\" or add weld reinforcement. "
                      f"<br>💡 <b>Alternative:</b> Provide branch end cap plates or side gussets to artificially increase the available footprint perimeter for welding.")

    formula = (
        f"Weld demand:\n"
        f"  F_Mzz = |Mzz|·12/(0.9·Hb) = {abs(Mzz):.3f}·12/(0.9·{Hb}) = {F_mzz:.2f} k\n"
        f"  F_Myy = |Myy|·12/(0.9·Bb) = {abs(Myy):.3f}·12/(0.9·{Bb}) = {F_myy:.2f} k\n"
        f"  F_total = √((|Pu|+F_Mzz+F_Myy)²+(V+V_tor)²)\n"
        f"          = √(({abs(Pu):.2f}+{F_mzz:.2f}+{F_myy:.2f})²+({V_total:.2f}+{V_tor:.2f})²)\n"
        f"          = {F_total:.2f} kips\n\n"
        f"Weld capacity:\n"
        f"  φRn = φ·0.6·FEXX·0.707·w·L = {phi_w}·0.6·{FEXX}·0.707·({D16_prov}/16)·{perimeter:.2f}\n"
        f"       = {phi_Rn:.2f} kips  (UC={uc_weld:.3f})\n\n"
        f"Required length at {D16_prov}/16\" size:\n"
        f"  L_req = F_total / (φ·0.6·FEXX·0.707·w)\n"
        f"        = {F_total:.2f} / {Rn_per_in:.3f} = {L_req:.2f}\"\n"
        f"  Available perimeter = {perimeter:.2f}\"  →  {'OK ✓' if perim_ok else 'INSUFFICIENT ✗'}"
    )

    return dict(
        F_total=round(F_total,2), F_axial=round(abs(Pu),2),
        F_mzz=round(F_mzz,2), F_myy=round(F_myy,2),
        V_total=round(V_total,2), V_tor=round(V_tor,2),
        perimeter_in=round(perimeter,2), L_req_in=round(L_req,2),
        perim_ok=perim_ok, perim_note=perim_note,
        D16_req=round(D16_prov,2), D16_min=D16_min, D16_max=D16_max,
        D16_prov=D16_prov, D_frac=f"{D16_prov}/16\"",
        D_dec=round(D16_prov/16,4),
        phi_Rn=round(phi_Rn,2), uc_weld=round(uc_weld,3), uc_BM=round(uc_BM,3),
        status_weld='PASS' if uc_weld<=1.0 else 'FAIL',
        status_BM='PASS' if uc_BM<=1.0 else 'FAIL',
        weld_override_note=weld_override_note,
        conn_type=conn_type, FEXX=FEXX, tb=tb, t_chord=t,
        formula=formula)


# ═══════════════════════════════════════════════════════════════
#  NODE DESIGN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════
def run_node_design(sel, nodes, members, member_forces, n2m,
                    chord_override=None, conn_types=None, weld_sizes=None,
                    Qf=1.0, FEXX=70, chord_Fy=50.0, branch_Fy=50.0):
    connected = n2m.get(sel, [])
    hss_mids  = [m for m in connected if members.get(m,{}).get('props')]
    chord_mid, chord_reason = detect_chord(sel, hss_mids, nodes, members, member_forces)
    if chord_override and chord_override in hss_mids:
        chord_mid = chord_override; chord_reason = "User override"
    if not chord_mid:
        return {'error': 'No HSS members at this node'}

    chord_m = members[chord_mid]; chord_p = chord_m['props']
    branches = [m for m in hss_mids if m != chord_mid]
    results_br = []

    hints_map = {
        "Chord Face Plastification": "✨ Fix: Increase chord wall thickness or increase branch width (β) to push load to the sidewalls.",
        "Chord Sidewall Yielding": "✨ Fix: Increase chord wall thickness or decrease branch angle.",
        "Chord Sidewall Crippling": "✨ Fix: Increase chord wall thickness or decrease branch angle.",
        "Branch Local Yielding": "✨ Fix: Increase branch thickness or decrease branch angle.",
        "Branch Shear": "✨ Fix: Increase branch thickness or depth.",
        "Moment In-Plane": "✨ Fix: Increase branch width/depth or chord thickness.",
        "Moment Out-of-Plane": "✨ Fix: Increase branch width/depth or chord thickness.",
        "Axial+Moment Interaction": "✨ Fix: Increase chord thickness or reduce applied moments."
    }

    for bmid in branches:
        bm = members[bmid]; bp = bm['props']
        if not bp: continue
        bf_data = member_forces.get(bmid, {'axial':(0,0),'vy':(0,0),'vz':(0,0),
                                            'torque':(0,0),'myy':(0,0),'mzz':(0,0)})
        theta_deg = angle_between(nodes, bm, chord_m, sel)
        if theta_deg > 90.0: theta_deg = 180.0 - theta_deg # Normalize to acute angle
        if theta_deg < 10: theta_deg = 90.0 # Collinear safety

        auto_type = 'moment' if (max_abs(bf_data.get('myy',(0,0)))>0.1 or
                                  max_abs(bf_data.get('mzz',(0,0)))>0.1) else 'pinned'
        ctype = (conn_types or {}).get(bmid, auto_type)
        user_D16 = (weld_sizes or {}).get(bmid, None)

        if chord_p['type'] == 'pipe':
            checks, geo = check_round_to_rect(chord_p, bp, bf_data, theta_deg, Qf,
                                               chord_Fy=chord_Fy, branch_Fy=branch_Fy)
        else:
            checks, geo = check_rect_to_rect(chord_p, bp, bf_data, theta_deg, Qf,
                                              chord_Fy=chord_Fy, branch_Fy=branch_Fy)
                                              
        for chk in checks:
            if chk['status'] == 'FAIL':
                is_chord = chk['name'] in ["Chord Face Plastification", "Chord Sidewall Yielding", "Chord Sidewall Crippling", "Axial+Moment Interaction", "Chord B/t ≤ 35", "Chord D/t ≤ 50"]
                target = 'chord' if is_chord else 'branch'
                
                # Retrieve standard next size
                next_sz = find_next_size(chord_p, bp, bf_data, theta_deg, Qf, chord_Fy, branch_Fy, chk['name'], target)
                base_hint = hints_map.get(chk['name'], "✨ Fix: Review member sizing and loads.")
                
                # Retrieve Exact Requirement via internal iteration solver
                req_var, req_val, cur_val, req_unit = get_exact_req(chk['name'], chord_p, bp, bf_data, theta_deg, Qf, chord_Fy, branch_Fy)
                if req_var:
                    deficit = req_val - cur_val
                    base_hint += f"<br>📐 <b>Exact Requirement:</b> {req_var}_req = <b>{req_val:.3f}</b> {req_unit} (Current = <b>{cur_val:.3f}</b> {req_unit} | Deficit = <b>{deficit:.3f}</b> {req_unit})"
                
                if next_sz:
                    base_hint += f"<br>📦 Next viable standard section to pass: <b>{next_sz}</b>."
                    
                if chk['name'] in ["Chord Face Plastification", "Chord Sidewall Yielding", "Axial+Moment Interaction"]:
                    base_hint += "<br>💡 <b>Alternative:</b> Provide a 3/8\" thick branch end cap plate (footprint extension) to distribute the force, or introduce longitudinal gusset plates to dump load directly into the rigid chord sidewalls."
                    
                chk['hint'] = base_hint

        weld = design_weld(bp, chord_p, bf_data, theta_deg,
                           chord_Fy=chord_Fy, branch_Fy=branch_Fy,
                           FEXX=FEXX, conn_type=ctype, user_D16=user_D16)

        gov_uc = max((c['uc'] for c in checks if not c.get('status_na')), default=0.0)
        overall = 'PASS' if (gov_uc<=1.0 and weld['status_weld']=='PASS'
                              and weld['status_BM']=='PASS') else 'FAIL'

        results_br.append(dict(
            member_id=bmid, section=bm['section'], props=bp,
            length_ft=round(member_length_ft(nodes, bm),2),
            theta_deg=round(theta_deg,1), conn_type=ctype,
            forces=bf_data, checks=checks, geo=geo, weld=weld,
            gov_uc=round(gov_uc,3), overall=overall))

    nd = nodes[sel]
    return dict(
        node_id=sel, coords=nd,
        chord_mid=chord_mid, chord_reason=chord_reason,
        chord_section=chord_m['section'], chord_props=chord_p,
        Qf=Qf, FEXX=FEXX, branches=results_br,
        overall='PASS' if all(b['overall']=='PASS' for b in results_br) else 'FAIL',
        non_hss=[m for m in connected if not members.get(m,{}).get('props')])


# ═══════════════════════════════════════════════════════════════
#  NODE SKETCH — ISOMETRIC 3D WIREFRAME
# ═══════════════════════════════════════════════════════════════
SKETCH_COLORS_RL = [
    colors.HexColor('#1E40AF'), colors.HexColor('#D97706'),
    colors.HexColor('#16A34A'), colors.HexColor('#9333EA'),
    colors.HexColor('#DC2626'), colors.HexColor('#0891B2'),
    colors.HexColor('#EA580C'), colors.HexColor('#BE185D'),
]

def build_node_sketch(result, nodes, members, n2m, W=460, H_sk=290):
    d = Drawing(W, H_sk)
    cx, cy = W/2, H_sk/2
    nd = nodes[result['node_id']]
    ARM = min(W, H_sk)*0.38
    all_mids = n2m.get(result['node_id'], [])
    chord_mid = result['chord_mid']

    cos30 = math.cos(math.radians(30))
    sin30 = math.sin(math.radians(30))
    def iso_proj(dx, dy, dz):
        u = (dx - dz) * cos30
        v = dy + (dx + dz) * sin30
        return u, v

    d.add(Circle(cx, cy, 10, fillColor=colors.HexColor('#DC2626'),
                 strokeColor=colors.white, strokeWidth=2))
    d.add(String(cx+13, cy+3, result['node_id'],
                 fontSize=9, fontName='Helvetica-Bold', fillColor=colors.HexColor('#0F172A')))

    for idx, mid in enumerate(all_mids):
        m = members.get(mid)
        if not m: continue
        
        is_pass_through = (result['node_id'] in m.get('pass_through_nodes', []))
        tips = []
        if is_pass_through:
            tips = [nodes[m['i_node']], nodes[m['j_node']]]
        else:
            ok = m['j_node'] if m['i_node']==result['node_id'] else m['i_node']
            if ok in nodes: tips = [nodes[ok]]
            
        for tip in tips:
            dx=tip['x']-nd['x']; dy=tip['y']-nd['y']; dz=tip['z']-nd['z']
            
            u, v = iso_proj(dx, dy, dz)
            ln = math.sqrt(u**2 + v**2)
            if ln < 1e-9: u, v, ln = 1.0, 0.0, 1.0
            ux, uy = u/ln, v/ln
            ex = cx + ux*ARM; ey = cy + uy*ARM
            
            is_chord=(mid==chord_mid)
            lc = colors.HexColor('#0F172A') if is_chord else SKETCH_COLORS_RL[idx%len(SKETCH_COLORS_RL)]
            lw = 4 if is_chord else 2.5
            d.add(Line(cx,cy,ex,ey, strokeColor=lc, strokeWidth=lw))
            
            ah=8; aw=5
            d.add(Line(ex,ey, ex-ah*(ux-aw*uy/ah),ey-ah*(uy+aw*ux/ah), strokeColor=lc,strokeWidth=lw))
            d.add(Line(ex,ey, ex-ah*(ux+aw*uy/ah),ey-ah*(uy-aw*ux/ah), strokeColor=lc,strokeWidth=lw))
            
            lx=cx+ux*(ARM+22); ly=cy+uy*(ARM+22)
            tag=f"{mid}"+(" [CHORD]" if is_chord else "")
            d.add(String(lx-18,ly+3, tag, fontSize=8 if is_chord else 7,
                         fontName='Helvetica-Bold' if is_chord else 'Helvetica', fillColor=lc))
            d.add(String(lx-18,ly-8, m.get('section',''),
                         fontSize=6, fontName='Courier', fillColor=colors.HexColor('#64748B')))

    lbl="Isometric View (Y is UP)"
    d.add(String(6,8, f"Node {result['node_id']} — {lbl}  (schematic, not to scale)",
                 fontSize=6.5, fontName='Helvetica', fillColor=colors.HexColor('#94A3B8')))
    return d


# ═══════════════════════════════════════════════════════════════
#  PDF REPORT
# ═══════════════════════════════════════════════════════════════
def generate_pdf(result, nodes, members, n2m, project_name="Project", designer="—"):
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.6*inch, bottomMargin=0.6*inch)
    styles=getSampleStyleSheet()
    def PS(n,**kw): return ParagraphStyle(n,parent=kw.pop('parent',styles['Normal']),**kw)
    title_s=PS('T',fontName='Helvetica-Bold',fontSize=16,leading=20,textColor=colors.HexColor('#0F172A'),spaceAfter=2)
    sub_s  =PS('S',fontName='Helvetica',fontSize=9,textColor=colors.HexColor('#64748B'),spaceAfter=14)
    h2_s   =PS('H2',fontName='Helvetica-Bold',fontSize=11,textColor=colors.HexColor('#0F172A'),spaceBefore=14,spaceAfter=6)
    h3_s   =PS('H3',fontName='Helvetica-Bold',fontSize=10,textColor=colors.HexColor('#1E40AF'),spaceBefore=10,spaceAfter=4)
    normal_s=PS('N',fontName='Helvetica',fontSize=9,leading=12)
    mono_s =PS('M',fontName='Courier',fontSize=7.5,leading=11,textColor=colors.HexColor('#1E3A5F'),backColor=colors.HexColor('#F0F7FF'))
    small_s=PS('SM',fontName='Helvetica',fontSize=7,textColor=colors.HexColor('#64748B'))
    hint_s =PS('HINT',fontName='Helvetica-Bold',fontSize=8,textColor=colors.HexColor('#D97706'),spaceBefore=3,spaceAfter=3)

    PC=colors.HexColor; HDR=PC('#F1F5F9'); BRD=PC('#E2E8F0')
    PASSC=PC('#166534'); FAILC=PC('#991B1B'); WBKG=PC('#ECFDF5'); WFBKG=PC('#FEF2F2')

    def mktbl(data,cw,ex=None):
        base=[('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
              ('FONTNAME',(0,1),(-1,-1),'Helvetica'),
              ('FONTSIZE',(0,0),(-1,-1),8),('BACKGROUND',(0,0),(-1,0),HDR),
              ('TEXTCOLOR',(0,0),(-1,0),PC('#374151')),
              ('LINEBELOW',(0,0),(-1,0),1,BRD),('LINEBELOW',(0,1),(-1,-1),0.5,BRD),
              ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
              ('VALIGN',(0,0),(-1,-1),'MIDDLE')]
        if ex: base.extend(ex)
        t=Table(data,colWidths=cw, hAlign='LEFT'); t.setStyle(TableStyle(base)); return t

    story=[]

    # Cover
    story.append(Paragraph("HSS Node Connection Design Report",title_s))
    story.append(Paragraph(
        f"Project: {project_name} &nbsp;|&nbsp; Node: {result['node_id']} &nbsp;|&nbsp; "
        f"Designer: {designer} &nbsp;|&nbsp; Date: {datetime.date.today().strftime('%B %d, %Y')}",sub_s))
    story.append(HRFlowable(width='100%',thickness=1.5,color=PC('#1E40AF')))
    story.append(Spacer(1,8))

    ov=result['overall']; ov_c=PASSC if ov=='PASS' else FAILC; ov_bg=WBKG if ov=='PASS' else WFBKG
    ov_tbl=Table([[f"OVERALL STATUS: {ov}"]],colWidths=[6.5*inch], hAlign='LEFT')
    ov_tbl.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),ov_bg),('TEXTCOLOR',(0,0),(-1,-1),ov_c),
        ('FONTNAME',(0,0),(-1,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),13),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),('TOPPADDING',(0,0),(-1,-1),7),
        ('BOTTOMPADDING',(0,0),(-1,-1),7),('BOX',(0,0),(-1,-1),1.5,ov_c)]))
    story.append(ov_tbl); story.append(Spacer(1,8))
    
    # 3D Model Global Context
    story.append(Paragraph("Global 3D Model Context", h2_s))
    try:
        fig_global = build_3d_full(nodes, members, n2m, highlight=result['node_id'])
        img_bytes = fig_global.to_image(format="png", engine="kaleido", width=800, height=450)
        story.append(RLImage(io.BytesIO(img_bytes), width=6.5*inch, height=3.6*inch))
        story.append(Spacer(1, 10))
    except Exception as e:
        story.append(Paragraph(f"<i>[Global 3D screenshot unavailable. Server environment missing 'kaleido' package.]</i>", normal_s))
        story.append(Spacer(1, 10))

    # Design basis
    story.append(Paragraph("Design Basis",h2_s))
    story.append(mktbl([['Parameter','Value'],
        ['Standard','AISC 360-22 (LRFD)'],['Chapter / Guide','K — HSS Connections / AISC DG-24'],
        ['Weld Standard','AWS D1.1'],['Steel','A992/A500 Gr.C — Fy=50 ksi, Fu=65 ksi'],
        ['Electrode',f'E{result["FEXX"]:.0f} — FEXX={result["FEXX"]} ksi'],
        ['φ connection','0.90'],['φ weld','0.75'],['Qf',f'{result["Qf"]:.3f}']],
        [2.5*inch,4.0*inch]))
    story.append(Spacer(1,6))

    # Node geometry
    story.append(Paragraph("Node Geometry",h2_s))
    nd=result['coords']
    story.append(Paragraph(f"Node {result['node_id']}:  X={nd['x']:.4f} ft  Y={nd['y']:.4f} ft  Z={nd['z']:.4f} ft",normal_s))
    story.append(Spacer(1,4))
    cp=result['chord_props']
    geo_rows=[['Parameter','Value'],
              ['Chord Member',f"{result['chord_mid']} — {result['chord_section']}"],
              ['Chord ID Method',result['chord_reason']]]
    if cp['type']=='pipe':
        geo_rows+=[['Chord D(OD)',f'{cp["B"]:.3f}"'],['Chord t',f'{cp["t"]:.4f}"'],['Chord D/t',f'{cp["B"]/cp["t"]:.2f}']]
    else:
        geo_rows+=[['Chord B',f'{cp["B"]:.3f}"'],['Chord H',f'{cp["H"]:.3f}"'],['Chord t',f'{cp["t"]:.4f}"']]
    geo_rows.append(['HSS Branches Designed',str(len(result['branches']))])
    if result['non_hss']:
        geo_rows.append(['Non-HSS (not designed)',', '.join(result['non_hss'])])
    story.append(mktbl(geo_rows,[2.5*inch,4.0*inch]))
    story.append(Spacer(1,10))

    # Sketch & Solid Rendering (Side by Side)
    story.append(Paragraph("Connection Geometry (Solid Render & Isometric Sketch)",h3_s))
    
    # Solid 3D Snapshot
    try:
        fig_solid = build_node_solid_zoom(nodes, members, n2m, result['node_id'])
        img_bytes_solid = fig_solid.to_image(format="png", engine="kaleido", width=600, height=400)
        img_solid_rl = RLImage(io.BytesIO(img_bytes_solid), width=3.3*inch, height=2.2*inch)
    except Exception as e:
        img_solid_rl = Paragraph(f"<i>[Solid Model Render unavailable.]</i>", normal_s)

    # Isometric Sketch (Scaled Down)
    sketch_draw = build_node_sketch(result, nodes, members, n2m, 460, 290)
    sketch_draw.width = 460 * 0.55
    sketch_draw.height = 290 * 0.55
    sketch_draw.scale(0.55, 0.55)

    # Place in Table
    img_tbl = Table([[img_solid_rl, sketch_draw]], colWidths=[3.4*inch, 3.4*inch], hAlign='CENTER')
    img_tbl.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(img_tbl)
    story.append(Spacer(1, 6))

    # Summary directly below
    story.append(Paragraph("Design Summary — All Branches",h2_s))
    sum_rows=[['Branch','Section','θ°','Type','Max D/C','Weld','L_req\"','L_avail\"','Status']]
    for b in result['branches']:
        w=b['weld']
        perim_flag="⚠" if not w['perim_ok'] else "✓"
        sum_rows.append([b['member_id'],b['section'],f"{b['theta_deg']:.0f}°",
                          b['conn_type'].capitalize(),f"{b['gov_uc']:.3f}",
                          f"★{w['D_frac']}", f"{w['L_req_in']:.2f}",
                          f"{w['perimeter_in']:.2f} {perim_flag}",b['overall']])
    sum_tbl=Table(sum_rows,colWidths=[0.55*inch,1.1*inch,0.38*inch,0.6*inch,0.55*inch,
                                       0.65*inch,0.65*inch,0.8*inch,0.55*inch], hAlign='LEFT')
    ex_s=[]
    for i,b in enumerate(result['branches'],1):
        c=PASSC if b['overall']=='PASS' else FAILC
        ex_s+=[ ('TEXTCOLOR',(8,i),(8,i),c),('FONTNAME',(8,i),(8,i),'Helvetica-Bold'),
                ('BACKGROUND',(5,i),(5,i),WBKG if b['weld']['status_weld']=='PASS' else WFBKG) ]
        if not b['weld']['perim_ok']:
            ex_s.append(('TEXTCOLOR',(7,i),(7,i),PC('#D97706')))
    sum_tbl.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTNAME',(0,1),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),7.5),
        ('BACKGROUND',(0,0),(-1,0),HDR),('LINEBELOW',(0,0),(-1,0),1,BRD),
        ('LINEBELOW',(0,1),(-1,-1),0.5,BRD),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),*ex_s]))
    story.append(sum_tbl)
    story.append(Spacer(1,4))
    story.append(Paragraph("★ = Provided weld size. ⚠ = Perimeter insufficient for required weld length — see branch detail.",small_s))

    # Per-branch pages
    for b in result['branches']:
        story.append(PageBreak())
        story.append(Paragraph(f"Branch {b['member_id']} — {b['section']}",h2_s))
        story.append(Paragraph(
            f"Chord: {result['chord_mid']} ({result['chord_section']})  "
            f"θ={b['theta_deg']}°  {'Moment-Resisting' if b['conn_type']=='moment' else 'Pinned'}  L={b['length_ft']:.2f} ft",
            normal_s)); story.append(Spacer(1,6))

        # Limit state checks
        story.append(Paragraph("Limit State Checks — AISC 360-22 Chapter K",h3_s))
        for chk in b['checks']:
            if chk['status_na']:
                na_t=Table([[f"[N/A]  {chk['name']} ({chk['ref']})  —  {chk.get('note','')}"]],colWidths=[6.5*inch], hAlign='LEFT')
                na_t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Helvetica'),
                    ('FONTSIZE',(0,0),(-1,-1),8),('TEXTCOLOR',(0,0),(-1,-1),PC('#94A3B8')),
                    ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
                story.append(na_t); continue
            uc=chk['uc']; st=chk['status']
            c_c=PASSC if st=='PASS' else FAILC; c_bg=WBKG if st=='PASS' else WFBKG
            unit=chk.get('unit','kips'); is_ratio=(unit=='ratio')
            cap_s=(f"Limit:{chk['phiRn']}" if is_ratio else
                   (f"φRn={chk['phiRn']:.2f} {unit}" if isinstance(chk['phiRn'],float) else "—"))
            dem_s=(f"Value:{chk['Ru']}" if is_ratio else
                   (f"Ru={chk['Ru']:.2f} {unit}" if isinstance(chk['Ru'],float) else "—"))
            ht=Table([[f"{chk['name']}",f"Ref: {chk['ref']}",f"D/C={uc:.3f}",st]],
                     colWidths=[2.8*inch,1.6*inch,1.1*inch,0.7*inch], hAlign='LEFT')
            ht.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Helvetica-Bold'),
                ('FONTSIZE',(0,0),(-1,-1),8.5),('BACKGROUND',(0,0),(-1,-1),c_bg),
                ('TEXTCOLOR',(3,0),(3,0),c_c),('TOPPADDING',(0,0),(-1,-1),5),
                ('BOTTOMPADDING',(0,0),(-1,-1),5),('BOX',(0,0),(-1,-1),0.5,BRD),
                ('LINEAFTER',(0,0),(2,0),0.5,BRD)]))
            story.append(ht)
            cd=Table([[cap_s,dem_s,f"φ={chk['phi']}",chk.get('note','')]],
                     colWidths=[1.7*inch,1.7*inch,0.7*inch,2.6*inch], hAlign='LEFT')
            cd.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Courier'),
                ('FONTSIZE',(0,0),(-1,-1),8),('BACKGROUND',(0,0),(-1,-1),PC('#F8FAFC')),
                ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
                ('BOX',(0,0),(-1,-1),0.5,BRD)]))
            story.append(cd)
            for fl in chk.get('formula','').split('\n'):
                if fl.strip(): story.append(Paragraph(fl,mono_s))
            if chk.get('hint'):
                clean_hint = chk['hint'].replace('<br>', ' ')
                story.append(Paragraph(clean_hint, hint_s))
            story.append(Spacer(1,5))

        story.append(Spacer(1,4))

        # Weld design
        story.append(Paragraph("Weld Design — AWS D1.1 / AISC J2.2",h3_s))
        w=b['weld']; wpass=(w['status_weld']=='PASS' and w['status_BM']=='PASS')
        w_bg=WBKG if wpass else WFBKG; w_c=PASSC if wpass else FAILC
        
        if w.get('weld_override_note'):
            story.append(Paragraph(w['weld_override_note'], hint_s))
            
        callout=Table([[f"PROVIDE: {w['D_frac']} FILLET WELD  E{w['FEXX']:.0f}  —  FULL PERIMETER",
                        f"L_req={w['L_req_in']:.2f}\" / L_avail={w['perimeter_in']:.2f}\"  "
                        f"{'✓ OK' if w['perim_ok'] else '⚠ INSUFFICIENT'}"]],
                      colWidths=[3.8*inch,2.7*inch], hAlign='LEFT')
        callout.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Helvetica-Bold'),
            ('FONTSIZE',(0,0),(0,0),10),('FONTSIZE',(1,0),(1,0),9),
            ('BACKGROUND',(0,0),(-1,-1),w_bg),('TEXTCOLOR',(0,0),(-1,-1),w_c),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('BOX',(0,0),(-1,-1),2,w_c),('LINEAFTER',(0,0),(0,0),1,w_c)]))
        story.append(callout); story.append(Spacer(1,5))
        if not w['perim_ok']:
            clean_perim_note = w['perim_note'].replace('<br>', ' ')
            story.append(Paragraph(clean_perim_note, PS('PN',fontName='Helvetica-Bold',fontSize=8,
                textColor=PC('#92400E'),backColor=PC('#FFFBEB'))))
            story.append(Spacer(1,4))

        wr=[['Check','φRn (k)','Demand (k)','UC','Status'],
            ['Weld Strength (J2.2)',f'{w["phi_Rn"]:.2f}',f'{w["F_total"]:.2f}',f'{w["uc_weld"]:.3f}',w['status_weld']],
            ['Base Metal (branch)',f'{round(1.0*0.6*50.0*w["tb"]*w["perimeter_in"],2):.2f}',f'{w["F_total"]:.2f}',f'{w["uc_BM"]:.3f}',w['status_BM']]]
        wx=Table(wr,colWidths=[2.2*inch,1.0*inch,1.0*inch,0.7*inch,0.7*inch], hAlign='LEFT')
        ex2=[]
        for i in range(1,3):
            sv=wr[i][-1]; c=PASSC if sv=='PASS' else FAILC
            ex2+=[ ('TEXTCOLOR',(4,i),(4,i),c),('FONTNAME',(4,i),(4,i),'Helvetica-Bold') ]
        wx.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
            ('FONTNAME',(0,1),(-1,-1),'Helvetica'),('FONTNAME',(1,1),(-1,-1),'Courier'),
            ('FONTSIZE',(0,0),(-1,-1),8),('BACKGROUND',(0,0),(-1,0),HDR),
            ('LINEBELOW',(0,0),(-1,0),1,BRD),('LINEBELOW',(0,1),(-1,-1),0.5,BRD),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),*ex2]))
        story.append(wx)

    # Footer
    story.append(Spacer(1,14))
    story.append(HRFlowable(width='100%',thickness=0.5,color=BRD))
    story.append(Spacer(1,5))
    story.append(Paragraph(
        "Generated by HSS Node Explorer &amp; Connection Designer &nbsp;|&nbsp; "
        "AISC 360-22 Chapter K &amp; AISC DG-24 &nbsp;|&nbsp; AWS D1.1 &nbsp;|&nbsp; "
        "Forces from RISA 3D envelope &nbsp;|&nbsp; "
        "Preliminary design only — EOR must verify all calculations before construction. &nbsp;|&nbsp; "
        "© Structured Design and Consulting", small_s))
    doc.build(story); buf.seek(0); return buf


# ═══════════════════════════════════════════════════════════════
#  HELPER UI
# ═══════════════════════════════════════════════════════════════
def bdg(status):
    if status=='PASS':  return '<span class="chip-pass">✓ PASS</span>'
    if status=='FAIL':  return '<span class="chip-fail">✗ FAIL</span>'
    if status=='N/A':   return '<span class="chip-na">N/A</span>'
    return f'<span class="chip-warn">{status}</span>'


# ═══════════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════════
def main():
    st.markdown("""
    <div class="hero">
      <h1>🏗️ HSS Node Explorer & Connection Designer</h1>
      <p>RISA 3D Import &nbsp;·&nbsp; 3D Model &nbsp;·&nbsp; Node Inspector &nbsp;·&nbsp;
         AISC 360-22 Ch. K &nbsp;·&nbsp; Weld Sizing &nbsp;·&nbsp; PDF Report</p>
    </div>""", unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("### 📂 Data Source")
        load_mode = st.radio("Load Method", ["Manual Upload", "Auto Load (Local Folder)"])
        uploaded = False
        nf_bytes, mf_bytes, ff_bytes = None, None, None

        if load_mode == "Auto Load (Local Folder)":
            files_exist = all(os.path.exists(f) for f in ["Nodes.xlsx", "Member.xlsx", "Member_Forces.xlsx"])
            if files_exist:
                nf_bytes = open("Nodes.xlsx", "rb").read()
                mf_bytes = open("Member.xlsx", "rb").read()
                ff_bytes = open("Member_Forces.xlsx", "rb").read()
                uploaded = True
                st.success("✅ Auto-loaded 3 files from current directory.")
            else:
                st.warning("⚠️ Could not find Nodes.xlsx, Member.xlsx, and Member_Forces.xlsx in the app folder.")
        else:
            nf = st.file_uploader("Nodes.xlsx", type=['xlsx'], key='nf')
            mf = st.file_uploader("Member.xlsx", type=['xlsx'], key='mf')
            ff = st.file_uploader("Member_Forces.xlsx", type=['xlsx'], key='ff')
            if nf and mf and ff:
                nf_bytes = nf.read()
                mf_bytes = mf.read()
                ff_bytes = ff.read()
                uploaded = True

        st.markdown("---")
        st.markdown("### 🔍 Node Selection")
        node_input = st.text_input("Node ID", value=st.session_state.get('node_sel',''),
                                   placeholder="e.g. N117")

        if uploaded:
            try:
                _n,_m,_mf2,_ntm = load_risa_data(nf_bytes, mf_bytes, ff_bytes)
                top5 = sorted(_ntm.items(), key=lambda x:-len(x[1]))[:5]
                st.caption("Quick-pick complex nodes:")
                cols_sb = st.columns(2)
                for idx,(nid,mids) in enumerate(top5):
                    if cols_sb[idx%2].button(f"{nid} ({len(mids)})", key=f"qk_{nid}",
                                              use_container_width=True):
                        st.session_state['node_sel'] = nid
                        st.rerun()
            except: pass

        st.markdown("---")
        st.markdown("### ⚙️ Design Parameters")
        Qf_val   = st.number_input("Qf (chord stress factor)", 0.1, 1.0, 1.0, 0.05,
                                   help="1.0 = no chord axial/moment stress")
        FEXX_val = st.selectbox("Weld Electrode FEXX (ksi)", [70, 80], index=0,
                                 format_func=lambda x: f"E{x} ({x} ksi)")
        st.markdown("---")
        st.markdown("### 📋 Project Info")
        proj_name = st.text_input("Project Name", "Tree House Project")
        designer  = st.text_input("Designer", "—")

    if not uploaded:
        st.markdown("""
        <div style='text-align:center;padding:80px 20px;color:#94A3B8'>
          <div style='font-size:3rem'>🏗️</div>
          <div style='font-size:1.1rem;font-weight:600;color:#374151;margin:14px 0 6px'>
            Provide your RISA 3D exports to begin
          </div>
          <div style='font-size:0.9rem'>
            <b>Nodes.xlsx</b> &nbsp;·&nbsp; <b>Member.xlsx</b> &nbsp;·&nbsp; <b>Member_Forces.xlsx</b>
          </div>
        </div>""", unsafe_allow_html=True)
        return

    with st.spinner("Parsing RISA exports…"):
        try:
            nodes, members, member_forces, n2m = load_risa_data(nf_bytes, mf_bytes, ff_bytes)
        except Exception as e:
            st.error(f"Parse error: {e}"); return

    hss_cnt=sum(1 for m in members.values() if m['props'])
    cplx=sum(1 for v in n2m.values() if len(v)>=5)
    mx=max(n2m.items(),key=lambda x:len(x[1]))
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Nodes",len(nodes)); c2.metric("Members",len(members))
    c3.metric("HSS",hss_cnt); c4.metric("Complex (5+)",cplx)
    c5.metric("Max Connected",f"{mx[0]} ({len(mx[1])})")
    st.markdown("---")

    tab_3d,tab_ins,tab_des,tab_batch,tab_dir = st.tabs([
        "🌐 3D Model","🔍 Node Inspector","🔩 Connection Design","📦 Batch Processing","📋 Node Directory"])

    # ════════ 3D MODEL ═══════════════════════════════════════════
    with tab_3d:
        hl = node_input.strip().upper() if node_input else None
        if hl and hl not in nodes: hl=None
        st.markdown("#### 3D Centerline Model")
        st.caption("Hover nodes/members · Blue lines = connected to selected node")
        st.plotly_chart(build_3d_full(nodes,members,n2m,hl),use_container_width=True,height=600)
        st.markdown("""<div style='font-size:0.8rem;color:#64748B;display:flex;gap:20px;flex-wrap:wrap'>
          <span>⬤ <span style='color:#94A3B8'>≤2</span></span>
          <span>⬤ <span style='color:#1E40AF'>3-4</span></span>
          <span>⬤ <span style='color:#D97706'>5-6</span></span>
          <span>⬤ <span style='color:#DC2626'>7+</span></span>
        </div>""",unsafe_allow_html=True)

    # ════════ NODE INSPECTOR ════════════════════════════════════
    with tab_ins:
        if not node_input or not node_input.strip():
            st.markdown('<div class="info-box">Enter a Node ID in the sidebar to inspect.</div>',
                        unsafe_allow_html=True)
            st.markdown("#### Most Connected Nodes")
            top12=sorted(n2m.items(),key=lambda x:-len(x[1]))[:12]
            cols2=st.columns(4)
            for i,(nid,mids) in enumerate(top12):
                nd2=nodes.get(nid,{}); cnt=len(mids)
                with cols2[i%4]:
                    st.markdown(
                        f'<div class="node-card"><b>{nid}</b><br>'
                        f'<span style="font-size:0.8rem;color:#64748B;font-family:monospace">'
                        f'({nd2.get("x",0):.1f},{nd2.get("y",0):.1f},{nd2.get("z",0):.1f}) ft</span><br><br>'
                        f'<span class="chip-{"fail" if cnt>=7 else "warn" if cnt>=5 else "chip-na"}">'
                        f'{cnt} members</span></div>',unsafe_allow_html=True)
        else:
            sel=node_input.strip().upper()
            if sel not in nodes:
                st.error(f"Node '{sel}' not found."); 
            else:
                nd2=nodes[sel]; connected=n2m.get(sel,[]); cnt=len(connected)
                st.markdown(
                    f'<div class="node-card"><span style="font-size:1.1rem;font-weight:700">{sel}</span><br>'
                    f'<span style="font-family:monospace;font-size:0.82rem;color:#64748B">'
                    f'X={nd2["x"]:.4f} ft  Y={nd2["y"]:.4f} ft  Z={nd2["z"]:.4f} ft</span><br><br>'
                    f'<span class="chip-{"fail" if cnt>=7 else "warn" if cnt>=5 else "chip-na"}">'
                    f'{cnt} members · {ncl(cnt)}</span></div>',unsafe_allow_html=True)
                cz,cf=st.columns([1,2])
                with cz:
                    st.markdown("**Node Zoom**")
                    zoom_tabs = st.tabs(["Wireframe", "3D Solid Render"])
                    with zoom_tabs[0]:
                        st.plotly_chart(build_node_zoom(nodes,members,n2m,sel),use_container_width=True)
                    with zoom_tabs[1]:
                        st.plotly_chart(build_node_solid_zoom(nodes,members,n2m,sel),use_container_width=True)
                    
                    Fx,Fy,Fz,bal=check_equilibrium(nodes,members,member_forces,n2m,sel)
                    R=(Fx**2+Fy**2+Fz**2)**0.5
                    st.markdown(
                        f'<div class="node-card"><b>Axial Equilibrium</b><br>'
                        f'<span style="font-family:monospace;font-size:0.82rem;line-height:1.9">'
                        f'ΣFx={Fx:+.2f}k ΣFy={Fy:+.2f}k ΣFz={Fz:+.2f}k<br>R={R:.2f}k</span><br><br>'
                        f'<span class="{"chip-pass" if bal else "chip-warn"}">{"✓ Balanced" if bal else "⚠ Check"}</span>'
                        f'</div>',unsafe_allow_html=True)
                with cf:
                    st.markdown("**Member Forces (Envelope)**")
                    rows_i=[]
                    for mid in sorted(connected):
                        m2=members.get(mid,{}); mf2=member_forces.get(mid,{})
                        ln2=member_length_ft(nodes,m2) if m2.get('i_node') in nodes else 0
                        
                        end_str = "Intermediate" if sel in m2.get('pass_through_nodes', []) else ("I-end" if m2.get('i_node')==sel else "J-end")
                        rows_i.append({'Member':mid,'Section':m2.get('section','—'),
                            'Position': end_str,
                            'L(ft)':round(ln2,1),
                            'Axial(k)':round(gf(mf2.get('axial',(0,0))),2),
                            'Vy(k)':round(gf(mf2.get('vy',(0,0))),2),
                            'Vz(k)':round(gf(mf2.get('vz',(0,0))),2),
                            'Myy(k-ft)':round(gf(mf2.get('myy',(0,0))),2),
                            'Mzz(k-ft)':round(gf(mf2.get('mzz',(0,0))),2)})
                    if rows_i:
                        st.dataframe(pd.DataFrame(rows_i),use_container_width=True,hide_index=True)

    # ════════ CONNECTION DESIGN ═════════════════════════════════
    with tab_des:
        if not node_input or not node_input.strip():
            st.markdown('<div class="info-box">Enter a Node ID to run connection design.</div>',
                        unsafe_allow_html=True)
        else:
            sel=node_input.strip().upper()
            if sel not in nodes:
                st.error(f"Node '{sel}' not found.")
            else:
                connected=n2m.get(sel,[])
                hss_mids=[m for m in connected if members.get(m,{}).get('props')]

                with st.expander("⚙️ Override chord / connection types / weld sizes", expanded=False):
                    chord_opts=['Auto-detect']+sorted(hss_mids)
                    chord_ov=st.selectbox("Chord member",chord_opts,key='chord_ov')
                    chord_override=None if chord_ov=='Auto-detect' else chord_ov
                    preview_branches=sorted(m for m in hss_mids if m!=(chord_override or ''))

                    st.markdown("**Per-branch settings:**")
                    conn_types={}; weld_sizes={}
                    for mid in preview_branches:
                        mf2=member_forces.get(mid,{})
                        auto='moment' if (max_abs(mf2.get('myy',(0,0)))>0.1 or
                                          max_abs(mf2.get('mzz',(0,0)))>0.1) else 'pinned'
                        rc1,rc2,rc3=st.columns([2,1,1])
                        rc1.markdown(f"**{mid}** `{members[mid]['section']}`")
                        conn_types[mid]=rc2.selectbox("Type",['pinned','moment'],
                            index=0 if auto=='pinned' else 1, key=f'ct_{mid}',
                            label_visibility='collapsed')
                        bp2=members[mid]['props']
                        t_thin=min(chord_override and members.get(chord_override,{}).get('props',{}).get('t',0.25) or 0.25,
                                   bp2['t'] if bp2 else 0.25)
                        d16_min=2 if t_thin<=0.25 else 3 if t_thin<=0.5 else 4 if t_thin<=0.75 else 5
                        d16_max=max(2, math.floor(bp2['t']*16)) if bp2 else 8
                        user_weld=rc3.number_input(f"Weld (x/16\")",
                            min_value=0,max_value=16,value=0,step=1,
                            key=f'wd_{mid}', label_visibility='collapsed',
                            help=f"Weld size in sixteenths. Enter 0 for Auto-Sizing.")
                        if user_weld > 0:
                            weld_sizes[mid]=int(user_weld)

                if st.button("🚀  Run Connection Design", type="primary"):
                    with st.spinner("Running AISC 360-22 Chapter K checks…"):
                        result=run_node_design(sel,nodes,members,member_forces,n2m,
                                               chord_override=chord_override,
                                               conn_types=conn_types,
                                               weld_sizes=weld_sizes,
                                               Qf=Qf_val, FEXX=FEXX_val)
                    st.session_state['design_result']=result
                    st.session_state['design_node']=sel

                if 'design_result' not in st.session_state:
                    st.markdown('<div class="info-box">Click <b>Run Connection Design</b> above.</div>',
                                unsafe_allow_html=True)
                else:
                    result=st.session_state['design_result']
                    if 'error' in result:
                        st.error(result['error'])
                    elif st.session_state.get('design_node') != sel:
                        st.markdown('<div class="warn-box">⚠ Result is for a different node. Re-run.</div>',
                                    unsafe_allow_html=True)
                    else:
                        ov=result['overall']
                        gov_uc=max((b['gov_uc'] for b in result['branches']),default=0)
                        max_wuc=max((b['weld']['uc_weld'] for b in result['branches']),default=0)
                        s1,s2,s3,s4,s5=st.columns(5)
                        s1.metric("Status",ov); s2.metric("Branches",len(result['branches']))
                        s3.metric("Max D/C",f"{gov_uc:.3f}"); s4.metric("Max Weld UC",f"{max_wuc:.3f}")
                        s5.metric("Chord",result['chord_mid'])
                        st.markdown(
                            f'{bdg(ov)} &nbsp; Chord: <b>{result["chord_mid"]}</b> '
                            f'({result["chord_section"]}) &nbsp;|&nbsp; <i>{result["chord_reason"]}</i>',
                            unsafe_allow_html=True)
                        if result['non_hss']:
                            st.markdown(
                                f'<div class="warn-box">⚠ Non-HSS members (not designed here): '
                                f'{", ".join(result["non_hss"])}</div>',unsafe_allow_html=True)
                        st.markdown("---")

                        d1,d2,d3=st.tabs(["📊 Limit States","🔧 Weld Sizing","📄 PDF Report"])

                        with d1:
                            for b in result['branches']:
                                with st.expander(
                                    f"**{b['member_id']}** {b['section']}  "
                                    f"θ={b['theta_deg']}°  UC={b['gov_uc']:.3f}",
                                    expanded=(b['overall']=='FAIL')):
                                    st.markdown(f"{bdg(b['overall'])} &nbsp; "
                                                f"{'Moment' if b['conn_type']=='moment' else 'Pinned'} "
                                                f"&nbsp;|&nbsp; L={b['length_ft']:.2f} ft",
                                                unsafe_allow_html=True)
                                    g=b['geo']
                                    gc1,gc2,gc3,gc4=st.columns(4)
                                    gc1.metric("β",f'{g.get("beta",0):.3f}')
                                    gc2.metric("γ",f'{g.get("gamma",0):.2f}')
                                    gc3.metric("θ",f'{g.get("theta_deg",90):.1f}°')
                                    gc4.metric("η" if "eta" in g else "D/t",
                                               f'{g.get("eta",g.get("D_t",0)):.3f}')
                                    st.markdown("---")
                                    for chk in b['checks']:
                                        s=chk['status']
                                        if chk['status_na']:
                                            st.markdown(
                                                f'<div class="check-card check-na" style="opacity:0.55">'
                                                f'<span style="font-weight:600">{chk["name"]}</span> '
                                                f'<span style="color:#94A3B8;font-size:0.78rem">'
                                                f'({chk["ref"]}) — {chk.get("note","N/A")}</span></div>',
                                                unsafe_allow_html=True); continue
                                        cls="check-pass" if s=='PASS' else "check-fail"
                                        unit=chk.get('unit','kips'); is_ratio=(unit=='ratio')
                                        cap=(f"Limit={chk['phiRn']}" if is_ratio else
                                             (f"φRn={chk['phiRn']:.2f} {unit}" if isinstance(chk['phiRn'],float) else "—"))
                                        dem=(f"Value={chk['Ru']}" if is_ratio else
                                             (f"Ru={chk['Ru']:.2f} {unit}" if isinstance(chk['Ru'],float) else "—"))
                                        formula_html=''
                                        if chk.get('formula'):
                                            flines=chk['formula'].replace('\n','<br>')
                                            formula_html=(f'<br><span style="display:block;'
                                                          f'font-size:0.76rem;font-family:monospace;'
                                                          f'background:#F0F7FF;padding:6px 8px;'
                                                          f'border-radius:4px;color:#1E3A5F;margin-top:4px">'
                                                          f'{flines}</span>')
                                        if chk.get('hint'):
                                            formula_html += f'<br><span style="display:block;margin-top:6px;color:#D97706;font-weight:500;line-height:1.4;background:#FFFBEB;padding:8px;border-radius:4px">{chk["hint"]}</span>'

                                        st.markdown(
                                            f'<div class="check-card {cls}">'
                                            f'<span style="font-weight:700">{chk["name"]}</span> '
                                            f'{bdg(s)} '
                                            f'<span style="color:#94A3B8;font-size:0.78rem">{chk["ref"]}</span><br>'
                                            f'<span style="font-family:monospace;font-size:0.83rem">'
                                            f'{cap} &nbsp;|&nbsp; {dem} &nbsp;|&nbsp; '
                                            f'<b>D/C={chk["uc"]:.3f}</b></span>'
                                            f'{formula_html}</div>',unsafe_allow_html=True)
                                        st.progress(min(chk['uc'],1.5)/1.5)

                        with d2:
                            st.markdown("#### Fillet Weld Design — Weld Length Callouts")
                            st.markdown(
                                '<div class="info-box">Green = weld fits within member perimeter. '
                                'Red = insufficient perimeter — increase weld size or add supplemental weld. '
                                'Weld length required is at the <b>provided</b> fillet size.</div>',
                                unsafe_allow_html=True)
                            for b in result['branches']:
                                w=b['weld']
                                wpass=(w['status_weld']=='PASS' and w['status_BM']=='PASS')
                                perim_ok=w['perim_ok']
                                box_cls="weld-ok" if (wpass and perim_ok) else ("weld-warn" if (wpass and not perim_ok) else "weld-fail")
                                util_pct=min(w['uc_weld']*100,100)
                                bar_c="#22C55E" if wpass else "#EF4444"

                                if w.get('weld_override_note'):
                                    st.markdown(f'<div class="info-box" style="background:#FFFBEB;border-color:#F59E0B;color:#92400E"><b>{w["weld_override_note"]}</b></div>', unsafe_allow_html=True)

                                if perim_ok:
                                    perim_str=(f'<span style="color:#166534;font-weight:600">'
                                               f'✓ Perimeter OK: {w["L_req_in"]:.2f}" required ≤ {w["perimeter_in"]:.2f}" available</span>')
                                else:
                                    perim_str=(f'<span style="color:#991B1B;font-weight:700">'
                                               f'⚠ PERIMETER INSUFFICIENT: L_req={w["L_req_in"]:.2f}" > L_avail={w["perimeter_in"]:.2f}" — '
                                               f'Increase weld size to {min(w["D16_prov"]+1, w["D16_max"])}/16" or add supplemental weld length.<br>'
                                               f'<span style="font-weight:500;color:#D97706">💡 Alternative: Provide branch end cap plates or side gussets to artificially increase the footprint perimeter available for welding.</span></span>')

                                st.markdown(
                                    f'<div class="{box_cls}">'
                                    f'<div style="font-size:1.0rem;font-weight:700;margin-bottom:8px">'
                                    f'{b["member_id"]} — {b["section"]}</div>'
                                    f'<div style="font-size:0.9rem;font-family:monospace;line-height:2.1">'
                                    f'<b>WELD SIZE:</b> &nbsp;'
                                    f'<span style="font-size:1.1rem;font-weight:800;'
                                    f'color:{"#166534" if wpass else "#991B1B"}">'
                                    f'{w["D_frac"]} FILLET — E{w["FEXX"]:.0f}</span><br>'
                                    f'<b>REQUIRED LENGTH:</b> &nbsp;'
                                    f'<span style="font-size:1.0rem;font-weight:700">{w["L_req_in"]:.2f}"</span>'
                                    f' &nbsp;/&nbsp; Available perimeter = {w["perimeter_in"]:.2f}"<br>'
                                    f'{perim_str}<br>'
                                    f'<b>Weld UC:</b> {w["uc_weld"]:.3f} &nbsp;|&nbsp; '
                                    f'<b>Base Metal UC:</b> {w["uc_BM"]:.3f}'
                                    f'</div></div>',unsafe_allow_html=True)

                                st.markdown(
                                    f'<div style="background:#E2E8F0;border-radius:6px;height:10px;margin:4px 0">'
                                    f'<div style="width:{util_pct:.0f}%;background:{bar_c};height:10px;border-radius:6px"></div></div>'
                                    f'<span style="font-size:0.74rem;color:#64748B">Weld utilization: {util_pct:.1f}%</span>',
                                    unsafe_allow_html=True)

                                with st.expander(f"Force breakdown — {b['member_id']}"):
                                    wc1,wc2,wc3=st.columns(3)
                                    wc1.metric("Axial",f"{w['F_axial']:.2f} k")
                                    wc1.metric("F_mzz equiv.",f"{w['F_mzz']:.2f} k")
                                    wc2.metric("F_myy equiv.",f"{w['F_myy']:.2f} k")
                                    wc2.metric("Shear",f"{w['V_total']:.2f} k")
                                    wc3.metric("Torsion",f"{w['V_tor']:.2f} k")
                                    wc3.metric("F_total (SRSS)",f"{w['F_total']:.2f} k")
                                    st.code(w['formula'], language='text')
                                st.markdown("---")

                        with d3:
                            st.markdown("#### PDF Calculation Report")
                            st.markdown(
                                '<div class="info-box">'
                                'Includes: design basis · 3D solid renderings · all limit state checks '
                                'with full equation traces & structural hints · weld force breakdown.'
                                '</div>',unsafe_allow_html=True)
                            pdf_buf=generate_pdf(result,nodes,members,n2m,
                                                  project_name=proj_name,designer=designer)
                            fname=f"Node_{result['node_id']}_Connection_{datetime.date.today().strftime('%Y%m%d')}.pdf"
                            st.download_button("📥  Download PDF Report",
                                data=pdf_buf,file_name=fname,mime="application/pdf",
                                type="primary",use_container_width=True)
                            st.caption("AISC 360-22 Ch. K · AISC DG-24 · AWS D1.1 · Forces from RISA 3D envelope")

    # ════════ BATCH PROCESSING & ZIP EXPORT ═════════════════════
    with tab_batch:
        st.markdown("#### Bulk Connection Design & Export")
        st.markdown(
            '<div class="info-box">Select nodes to process. Set overrides globally per node, '
            'or leave as "Auto" to use the engine\'s auto-detection.</div>',
            unsafe_allow_html=True)
            
        eligible_nodes = []
        for nid, mids in n2m.items():
            hss_mids = [m for m in mids if members.get(m, {}).get('props')]
            if len(hss_mids) >= 2:
                eligible_nodes.append((nid, hss_mids))
                
        if not eligible_nodes:
            st.info("No eligible nodes with ≥ 2 HSS members found.")
        else:
            batch_data = []
            for nid, hss_mids in eligible_nodes:
                batch_data.append({
                    "Include": True,
                    "Node ID": nid,
                    "HSS Count": len(hss_mids),
                    "Chord Override": "Auto", 
                    "Conn Type": "Auto", 
                    "Weld (16ths)": 0 
                })
            batch_df = pd.DataFrame(batch_data)
            
            st.markdown("**Eligible Nodes Matrix**")
            edited_df = st.data_editor(
                batch_df,
                column_config={
                    "Include": st.column_config.CheckboxColumn("Include", default=True),
                    "Node ID": st.column_config.TextColumn("Node", disabled=True),
                    "HSS Count": st.column_config.NumberColumn("HSS Members", disabled=True),
                    "Chord Override": st.column_config.TextColumn("Chord Override (ID or Auto)"),
                    "Conn Type": st.column_config.SelectboxColumn("Conn Type", options=["Auto", "pinned", "moment"]),
                    "Weld (16ths)": st.column_config.NumberColumn("Weld Size (0=Auto)", min_value=0, max_value=16, step=1)
                },
                hide_index=True,
                use_container_width=True,
                height=400
            )
            
            st.markdown("---")
            if st.button("🚀 Run Batch & Generate ZIP Package", type="primary"):
                tasks = edited_df[edited_df["Include"] == True]
                total_tasks = len(tasks)
                
                if total_tasks == 0:
                    st.warning("No nodes selected for batch processing.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        
                        for i, (idx, row) in enumerate(tasks.iterrows()):
                            nid = row["Node ID"]
                            status_text.text(f"Processing {i+1} of {total_tasks}: Node {nid}...")
                            
                            chord_val = str(row["Chord Override"]).strip()
                            conn_val = str(row["Conn Type"]).strip()
                            weld_val = int(row["Weld (16ths)"])
                            
                            chord_ov = None if chord_val.lower() == 'auto' else chord_val
                            conn_types = {}
                            weld_sizes = {}
                            
                            node_hss = [m for m in n2m.get(nid, []) if members.get(m, {}).get('props')]
                            for bmid in node_hss:
                                if conn_val.lower() != "auto": 
                                    conn_types[bmid] = conn_val.lower()
                                if weld_val > 0: 
                                    weld_sizes[bmid] = weld_val
                                    
                            res = run_node_design(
                                nid, nodes, members, member_forces, n2m,
                                chord_override=chord_ov,
                                conn_types=conn_types,
                                weld_sizes=weld_sizes,
                                Qf=Qf_val, FEXX=FEXX_val
                            )
                            
                            if 'error' not in res:
                                pdf_buf = generate_pdf(res, nodes, members, n2m, project_name=proj_name, designer=designer)
                                filename = f"Node_{nid}_Calculations.pdf"
                                zip_file.writestr(filename, pdf_buf.getvalue())
                                
                            progress_bar.progress((i + 1) / total_tasks)
                            
                    status_text.success(f"Successfully processed {total_tasks} nodes!")
                    
                    st.download_button(
                        label=f"📥 Download {total_tasks} PDFs (.zip)",
                        data=zip_buffer.getvalue(),
                        file_name=f"HSS_Batch_Designs_{datetime.date.today().strftime('%Y%m%d')}.zip",
                        mime="application/zip",
                        type="primary",
                        use_container_width=True
                    )

    # ════════ NODE DIRECTORY ════════════════════════════════════
    with tab_dir:
        st.markdown("#### Node Directory")
        fc1,fc2=st.columns([1,2])
        min_c=fc1.slider("Min connections",1,10,1)
        srch=fc2.text_input("Search","",placeholder="Filter by node ID…")
        dir_rows=[]
        for nid in sorted(n2m.keys(), key=lambda x:int(re.sub(r'\D','',x) or 0)):
            cnt=len(n2m[nid])
            if cnt<min_c: continue
            if srch and srch.upper() not in nid.upper(): continue
            nd2=nodes.get(nid,{})
            has_mom=any(max(max_abs(member_forces.get(m,{}).get('myy',(0,0))),
                            max_abs(member_forces.get(m,{}).get('mzz',(0,0))))>0.1
                        for m in n2m[nid])
            dir_rows.append({'Node':nid,'X(ft)':round(nd2.get('x',0),3),
                'Y(ft)':round(nd2.get('y',0),3),'Z(ft)':round(nd2.get('z',0),3),
                'Members':cnt,'Complexity':ncl(cnt),
                'Connected':','.join(sorted(n2m[nid])),
                'Moment?':'⚠ Yes' if has_mom else '—'})
        if dir_rows:
            st.dataframe(pd.DataFrame(dir_rows),use_container_width=True,hide_index=True,
                column_config={'Complexity':st.column_config.TextColumn(width='small'),
                               'Moment?':st.column_config.TextColumn(width='small'),
                               'Members':st.column_config.NumberColumn(width='small')})
            st.caption(f"{len(dir_rows)} nodes shown")

    st.markdown("""
    <div style='text-align:center;color:#94A3B8;font-size:0.77rem;
                padding:18px 0;border-top:1px solid #E2E8F0;margin-top:28px'>
        HSS Node Explorer &amp; Connection Designer &nbsp;·&nbsp; AISC 360-22 Chapter K &nbsp;·&nbsp;
        For preliminary design — EOR must verify all calculations &nbsp;·&nbsp;
        © Structured Design and Consulting
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()