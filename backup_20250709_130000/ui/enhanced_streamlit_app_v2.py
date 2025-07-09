"""
HITRAN CRDS 시뮬레이터 v2 - 통합 UI 간결 버전
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_handler.hitran_api import HitranAPI
from spectrum_calc.absorption import SpectrumCalculator
from constants import HITRAN_MOLECULES, MOLECULE_CATEGORIES, WAVELENGTH_SHORTCUTS, DEFAULT_CONCENTRATIONS

# 페이지 설정
st.set_page_config(page_title="HITRAN CRDS Simulator v2", page_icon="🌟", layout="wide")

# Session State 초기화
if 'results' not in st.session_state:
    st.session_state.results = None

# 제목
st.title("🌟 HITRAN CRDS Simulator Enhanced v2")

# 사이드바 - 모든 설정
with st.sidebar:
    st.header("⚙️ 시뮬레이션 설정")
    
    # 1. 모드 선택
    mode = st.radio("📊 분석 모드", ["🧪 혼합 스펙트럼", "📈 농도별 분석"], index=0)
    
    st.markdown("---")
    
    # 2. 공통 파라미터
    st.subheader("🌡️ 물리 조건")
    temp = st.number_input("온도 (K)", value=296.15, min_value=200.0, max_value=400.0)
    pressure = st.number_input("압력 (torr)", value=760.0, min_value=1.0, max_value=15000.0)
    path = st.number_input("경로 길이 (m)", value=1000.0, min_value=1.0, max_value=50000.0)
    
    # 3. 파장 범위
    st.subheader("📏 파장 범위 (nm)")
    col1, col2 = st.columns(2)
    with col1:
        wl_min = st.number_input("최소", value=1500.0, min_value=100.0, max_value=50000.0)
    with col2:
        wl_max = st.number_input("최대", value=1520.0, min_value=100.0, max_value=50000.0)
    
    with st.expander("파장 바로가기"):
        for name, data in list(WAVELENGTH_SHORTCUTS.items())[:5]:  # 주요 5개만
            if st.button(data['description']):
                st.session_state.wl_min = data['min']
                st.session_state.wl_max = data['max']
                st.rerun()
    
    st.markdown("---")
    
    # 4. 모드별 설정
    if mode == "🧪 혼합 스펙트럼":
        st.subheader("🧪 분자 선택")
        
        # 모든 분자 표시
        all_molecules = list(HITRAN_MOLECULES.keys())
        molecules = st.multiselect(
            f"분자 선택 (총 {len(all_molecules)}개)",
            all_molecules,
            default=["H2O", "CO2", "CH4"],
            format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})",
            help="최대 15개까지 선택 가능합니다"
        )
        
        if len(molecules) > 15:
            st.warning("⚠️ 최대 15개까지만 선택 가능합니다.")
            molecules = molecules[:15]
        
        # 농도 설정
        if molecules:
            st.subheader("💨 농도 (ppb)")
            use_same = st.checkbox("모든 분자 동일 농도", value=False)
            
            concs = {}
            if use_same:
                same_conc = st.number_input("농도", value=1000.0, min_value=0.1)
                for mol in molecules:
                    concs[mol] = same_conc
            else:
                for mol in molecules:
                    concs[mol] = st.number_input(
                        f"{mol}", 
                        value=DEFAULT_CONCENTRATIONS.get(mol, 100.0),
                        min_value=0.1,
                        key=f"c_{mol}"
                    )
    
    else:  # 농도별 분석
        st.subheader("🧪 분자 선택")
        all_molecules = list(HITRAN_MOLECULES.keys())
        molecule = st.selectbox(
            f"분석할 분자 (총 {len(all_molecules)}개)",
            all_molecules,
            format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})",
            index=all_molecules.index("CH4") if "CH4" in all_molecules else 0
        )
        
        st.subheader("📊 농도 범위")
        c_min = st.number_input("최소 (ppb)", value=10.0, min_value=0.1)
        c_max = st.number_input("최대 (ppb)", value=5000.0, min_value=0.1)
        c_steps = st.slider("단계 수", 3, 20, 10)
    
    # 5. 실행 버튼
    st.markdown("---")
    btn_text = "🧮 혼합 스펙트럼 계산" if mode == "🧪 혼합 스펙트럼" else "📈 농도별 분석 실행"
    calc_btn = st.button(btn_text, type="primary", use_container_width=True)

# 메인 화면 - 결과
if calc_btn:
    if wl_min >= wl_max:
        st.error("❌ 파장 범위를 확인하세요!")
    else:
        with st.spinner('계산 중...'):
            # API 초기화
            api = HitranAPI()
            calc = SpectrumCalculator()
            
            # 주파수 격자
            freq_min = 1e7 / wl_max
            freq_max = 1e7 / wl_min
            freq_grid = np.linspace(freq_min, freq_max, 3000)
            wl_grid = 1e7 / freq_grid
            
            if mode == "🧪 혼합 스펙트럼" and molecules:
                # 혼합 스펙트럼 계산
                results = {'spectra': {}, 'combined': None}
                combined_abs = np.zeros_like(freq_grid)
                
                progress = st.progress(0)
                for i, mol in enumerate(molecules):
                    progress.progress((i+1)/len(molecules))
                    
                    data = api.download_molecule_data(mol, wl_min, wl_max)
                    if data is not None and len(data) > 0:
                        spec = calc.calculate_absorption_spectrum(
                            data, freq_grid, temp, pressure/760.0, 
                            concs[mol]/1e9, path, mol
                        )
                        results['spectra'][mol] = spec
                        combined_abs += spec['absorption_coeff']
                
                results['combined'] = {
                    'transmittance': np.exp(-combined_abs * path),
                    'absorbance': -np.log10(np.exp(-combined_abs * path))
                }
                results['wavelength'] = wl_grid
                st.session_state.results = ('mix', results)
                
            elif mode == "📈 농도별 분석":
                # 농도별 분석
                if c_min >= c_max:
                    st.error("❌ 농도 범위를 확인하세요!")
                else:
                    concs_array = np.linspace(c_min, c_max, c_steps)
                    results = {'spectra': {}, 'analysis': {}}
                    
                    # HITRAN 데이터 다운로드
                    data = api.download_molecule_data(molecule, wl_min, wl_max)
                    
                    if data is not None and len(data) > 0:
                        max_abs = []
                        progress = st.progress(0)
                        
                        for i, c in enumerate(concs_array):
                            progress.progress((i+1)/c_steps)
                            spec = calc.calculate_absorption_spectrum(
                                data, freq_grid, temp, pressure/760.0,
                                c/1e9, path, molecule
                            )
                            results['spectra'][c] = spec
                            max_abs.append(np.max(spec['absorbance']))
                        
                        # 선형성 분석
                        slope, intercept, r_value, _, _ = stats.linregress(concs_array, max_abs)
                        results['analysis'] = {
                            'concentrations': concs_array,
                            'max_absorbances': max_abs,
                            'r_squared': r_value**2,
                            'slope': slope,
                            'intercept': intercept
                        }
                        results['wavelength'] = wl_grid
                        results['molecule'] = molecule
                        st.session_state.results = ('conc', results)

# 결과 표시
if st.session_state.results:
    result_type, results = st.session_state.results
    
    if result_type == 'mix':
        st.subheader("📊 혼합 스펙트럼 결과")
        
        # 3단 그래프
        fig = make_subplots(rows=3, cols=1, 
                           subplot_titles=['개별 분자', '혼합 투과율', '혼합 흡광도'],
                           vertical_spacing=0.1)
        
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']
        
        # 개별 분자
        for i, (mol, spec) in enumerate(results['spectra'].items()):
            fig.add_trace(
                go.Scatter(x=results['wavelength'], y=spec['absorbance'],
                          name=f"{mol} ({HITRAN_MOLECULES[mol]['name']})",
                          line=dict(color=colors[i % len(colors)])),
                row=1, col=1
            )
        
        # 혼합 투과율
        fig.add_trace(
            go.Scatter(x=results['wavelength'], y=results['combined']['transmittance'],
                      name='혼합', line=dict(color='black', width=2)),
            row=2, col=1
        )
        
        # 혼합 흡광도
        fig.add_trace(
            go.Scatter(x=results['wavelength'], y=results['combined']['absorbance'],
                      name='혼합', line=dict(color='darkred', width=2)),
            row=3, col=1
        )
        
        fig.update_xaxes(title_text="파장 (nm)", row=3, col=1)
        fig.update_yaxes(title_text="흡광도", row=1, col=1)
        fig.update_yaxes(title_text="투과율", row=2, col=1)
        fig.update_yaxes(title_text="흡광도", row=3, col=1)
        fig.update_layout(height=800, showlegend=True)
        
        st.plotly_chart(fig, use_container_width=True)
        
    else:  # 농도별 분석
        st.subheader(f"📈 {results['molecule']} 농도별 분석 결과")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 농도별 스펙트럼
            fig1 = go.Figure()
            colors = ['darkblue', 'blue', 'lightblue', 'green', 'yellow', 'orange', 'red', 'darkred']
            
            for i, (c, spec) in enumerate(results['spectra'].items()):
                color_idx = int(i * (len(colors)-1) / (len(results['spectra'])-1))
                fig1.add_trace(
                    go.Scatter(x=results['wavelength'], y=spec['absorbance'],
                              name=f'{c:.1f} ppb',
                              line=dict(color=colors[color_idx]))
                )
            
            fig1.update_layout(title="농도별 스펙트럼", xaxis_title="파장 (nm)", 
                              yaxis_title="흡광도", height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # 선형성 분석
            fig2 = go.Figure()
            
            analysis = results['analysis']
            fig2.add_trace(
                go.Scatter(x=analysis['concentrations'], y=analysis['max_absorbances'],
                          mode='markers', name='데이터', marker=dict(size=10, color='red'))
            )
            
            # 회귀선
            x_fit = np.linspace(analysis['concentrations'][0], analysis['concentrations'][-1], 100)
            y_fit = analysis['slope'] * x_fit + analysis['intercept']
            fig2.add_trace(
                go.Scatter(x=x_fit, y=y_fit, mode='lines',
                          name=f"R² = {analysis['r_squared']:.5f}",
                          line=dict(color='blue', dash='dash'))
            )
            
            fig2.update_layout(title="농도-흡광도 선형성", xaxis_title="농도 (ppb)",
                              yaxis_title="최대 흡광도", height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        # 분석 결과
        st.subheader("📊 선형성 분석")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("R²", f"{analysis['r_squared']:.6f}")
        with col2:
            st.metric("기울기", f"{analysis['slope']:.2e}")
        with col3:
            st.metric("절편", f"{analysis['intercept']:.2e}")
        with col4:
            detection_limit = 3 * 0.001 / analysis['slope'] if analysis['slope'] > 0 else 0
            st.metric("검출한계 (3σ)", f"{detection_limit:.1f} ppb")

# 하단 정보
st.markdown("---")
st.markdown("**HITRAN CRDS Simulator v2** | 통합 UI | 간결 버전")