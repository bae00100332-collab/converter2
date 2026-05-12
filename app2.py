import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 페이지 설정
st.set_page_config(page_title="Half-Bridge Converter Simulator", layout="wide")
st.title("⚡ Half-Bridge Converter Interactive Simulator")
st.markdown("1차측 누설 인덕턴스($L_{lk}$)가 포함된 하프 브리지 회로의 동특성을 시뮬레이션합니다.")

# 사이드바: 파라미터 조절
st.sidebar.header("⚙️ Circuit Parameters")
Vi = st.sidebar.slider("Input Voltage (Vi) [V]", 20, 400, 100)
fs = st.sidebar.slider("Switching Frequency (fs) [kHz]", 10, 200, 100) * 1000
D = st.sidebar.slider("Duty Cycle (D)", 0.05, 0.45, 0.3)
L_lk = st.sidebar.slider("Leakage Inductance (L_lk) [uH]", 0.1, 20.0, 2.0) * 1e-6
L_out = st.sidebar.slider("Output Inductor (L) [uH]", 10.0, 500.0, 100.0) * 1e-6
C_out = st.sidebar.slider("Output Capacitor (C) [uF]", 10, 1000, 100) * 1e-6
R_load = st.sidebar.slider("Load Resistance (Ro) [Ohm]", 1.0, 50.0, 10.0)

# 시뮬레이션 시간 설정
T = 1/fs
dt = T / 2000
t_sim = np.arange(0, 2*T, dt)

# 초기값 및 저장 리스트
ip, iL, Vo = 0.0, 0.0, (Vi/2 * D) # 초기 출력전압 추정값
history = []

# 시뮬레이션 루프
for t in t_sim:
    t_mod = t % T
    
    # 게이트 신호 (Half-bridge)
    g1 = 1 if t_mod < D*T else 0
    g2 = 1 if (T/2 <= t_mod < T/2 + D*T) else 0
    
    # 1차측 인가 전압
    V_pri = (Vi/2 if g1 else (-Vi/2 if g2 else 0))
    
    # 물리 엔진: L_lk에 의한 Commutation 로직
    target_ip = iL if g1 else (-iL if g2 else 0)
    
    # 1차측 전류 변화 (L_lk 모델링)
    if g1:
        if ip < target_ip:
            dip_dt = (Vi/2) / L_lk
            v_rect = 0 # Commutation 중에는 2차측 전압 0 (다이오드 쇼트)
        else:
            ip = target_ip
            dip_dt = 0
            v_rect = Vi/2
    elif g2:
        if ip > target_ip:
            dip_dt = (-Vi/2) / L_lk
            v_rect = 0
        else:
            ip = target_ip
            dip_dt = 0
            v_rect = Vi/2 # 전파 정류이므로 양수
    else:
        # Freewheeling (S1, S2 Off)
        v_rect = 0
        # 누설 에너지는 빠르게 소산된다고 가정 (이상적 스너버)
        dip_dt = -ip / (dt * 2) 
        
    ip += dip_dt * dt
    
    # 2차측 Buck 필터 거동
    vL = v_rect - Vo
    diL_dt = vL / L_out
    iL += diL_dt * dt
    
    dVo_dt = (iL - Vo/R_load) / C_out
    Vo += dVo_dt * dt
    
    history.append([t, g1, g2, ip, vL, iL, Vo])

# 데이터프레임 변환
df = pd.DataFrame(history, columns=['t', 'g1', 'g2', 'ip', 'vL', 'iL', 'Vo'])

# Plotly 그래프 생성
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.08,
                    subplot_titles=("Gate Signals & Primary Current", "Inductor Voltage (VL)", "Output Current & Voltage"))

# Subplot 1: 게이트 및 1차측 전류
fig.add_trace(go.Scatter(x=df['t'], y=df['g1'], name="S1 Gate", line=dict(color='blue')), row=1, col=1)
fig.add_trace(go.Scatter(x=df['t'], y=df['ip'], name="Primary Current (ip)", line=dict(color='purple')), row=1, col=1)

# Subplot 2: 인덕터 전압 (VL)
fig.add_trace(go.Scatter(x=df['t'], y=df['vL'], name="Inductor Voltage (VL)", fill='tozeroy', line=dict(color='green')), row=2, col=1)

# Subplot 3: 출력 전류 및 전압
fig.add_trace(go.Scatter(x=df['t'], y=df['iL'], name="Inductor Current (iL)", line=dict(color='orange')), row=3, col=1)
fig.add_trace(go.Scatter(x=df['t'], y=df['Vo'], name="Output Voltage (Vo)", line=dict(color='red', dash='dot')), row=3, col=1)

fig.update_layout(height=800, template="plotly_dark", showlegend=True)
st.plotly_chart(fig, use_container_width=True)

# 이론적 수식 설명
st.markdown("---")
st.latex(r"V_{o, ideal} = \frac{V_i}{2} \cdot D")
st.latex(r"\Delta V_{loss} \approx f_s \cdot L_{lk} \cdot I_o")
st.write("누설 인덕턴스($L_{lk}$)가 클수록, 1차측 전류가 부하 전류까지 차오르는 시간이 길어져 유효 시비율이 깎이게 됩니다.")
