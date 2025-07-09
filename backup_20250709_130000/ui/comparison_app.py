"""
HITRAN CRDS 스펙트럼 비교 도구
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
import io
from itertools import cycle
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from data_handler.hitran_api import HitranAPI
from spectrum_calc.absorption import SpectrumCalculator

# 페이지 설정
st.set_page_config(
    page_title="HITRAN Spectrum Comparison",
    page_icon="📊",
    layout="wide"
)

# Session State 초기화
if 'comparison_results' not in st.session_state:
    st.session_state.comparison_results = []
if 'comparison_count' not in st.session_state:
    st.session_state.comparison_count = 0

st.title("📊 HITRAN CRDS Spectrum Comparison Tool")
st.markdown("**다중 조건 스펙트럼 비교 및 분석 도구**")

# 사이드바 - 비교 모드 선택
st.sidebar.header("🔍 비교 분석 모드")

comparison_mode = st.sidebar.selectbox(
    "분석 모드 선택",
    ["농도별 비교", "온도별 비교", "압력별 비교", "사용자 정의"]
)

# 공통 설정
st.sidebar.subheader("🧪 공통 설정")

# 분자 선택 (단일)
molecule = st.sidebar.selectbox(
    "분자 선택",
    ["H2O", "CO2", "CH4", "NH3", "N2O", "CO"]
)

# 파장 범위
col1, col2 = st.sidebar.columns(2)
with col1:
    wavelength_min = st.number_input("최소 파장 (nm)", value=1500, min_value=100, max_value=10000)
with col2:
    wavelength_max = st.number_input("최대 파장 (nm)", value=1520, min_value=100, max_value=10000)

# 모드별 설정
st.sidebar.subheader(f"📈 {comparison_mode} 설정")

if comparison_mode == "농도별 비교":
    # 고정 조건
    base_temp = st.sidebar.number_input("온도 (K)", value=296.15, min_value=200.0, max_value=400.0, step=0.1)
    base_pressure = st.sidebar.number_input("압력 (torr)", value=760.0, min_value=1.0, max_value=15000.0, step=1.0)
    base_path = st.sidebar.number_input("경로 길이 (m)", value=1000.0, min_value=1.0, max_value=50000.0, step=1.0)
    
    # 농도 범위 설정
    st.sidebar.write("**농도 범위 (ppb)**")
    conc_min = st.sidebar.number_input("최소 농도", value=100.0, min_value=0.1, max_value=1000000.0)
    conc_max = st.sidebar.number_input("최대 농도", value=1000.0, min_value=0.1, max_value=1000000.0)
    conc_steps = st.sidebar.slider("농도 단계", 3, 10, 5)
    
    # 농도 리스트 생성
    concentrations = np.linspace(conc_min, conc_max, conc_steps)
    
    conditions = []
    for conc in concentrations:
        conditions.append({
            'name': f'{conc:.0f}ppb',
            'molecule': molecule,
            'concentration': conc,
            'temperature': base_temp,
            'pressure': base_pressure,
            'path_length': base_path
        })

elif comparison_mode == "온도별 비교":
    # 고정 조건
    base_conc = st.sidebar.number_input("농도 (ppb)", value=1000.0, min_value=0.1, max_value=1000000.0)
    base_pressure = st.sidebar.number_input("압력 (torr)", value=760.0, min_value=1.0, max_value=15000.0, step=1.0)
    base_path = st.sidebar.number_input("경로 길이 (m)", value=1000.0, min_value=1.0, max_value=50000.0, step=1.0)
    
    # 온도 범위 설정
    st.sidebar.write("**온도 범위 (K)**")
    temp_min = st.sidebar.number_input("최소 온도", value=250.0, min_value=200.0, max_value=400.0)
    temp_max = st.sidebar.number_input("최대 온도", value=350.0, min_value=200.0, max_value=400.0)
    temp_steps = st.sidebar.slider("온도 단계", 3, 10, 5)
    
    # 온도 리스트 생성
    temperatures = np.linspace(temp_min, temp_max, temp_steps)
    
    conditions = []
    for temp in temperatures:
        conditions.append({
            'name': f'{temp:.0f}K',
            'molecule': molecule,
            'concentration': base_conc,
            'temperature': temp,
            'pressure': base_pressure,
            'path_length': base_path
        })

elif comparison_mode == "압력별 비교":
    # 고정 조건
    base_conc = st.sidebar.number_input("농도 (ppb)", value=1000.0, min_value=0.1, max_value=1000000.0)
    base_temp = st.sidebar.number_input("온도 (K)", value=296.15, min_value=200.0, max_value=400.0, step=0.1)
    base_path = st.sidebar.number_input("경로 길이 (m)", value=1000.0, min_value=1.0, max_value=50000.0, step=1.0)
    
    # 압력 범위 설정
    st.sidebar.write("**압력 범위 (torr)**")
    pressure_min = st.sidebar.number_input("최소 압력", value=100.0, min_value=1.0, max_value=15000.0)
    pressure_max = st.sidebar.number_input("최대 압력", value=2000.0, min_value=1.0, max_value=15000.0)
    pressure_steps = st.sidebar.slider("압력 단계", 3, 10, 5)
    
    # 압력 리스트 생성
    pressures = np.linspace(pressure_min, pressure_max, pressure_steps)
    
    conditions = []
    for pressure in pressures:
        conditions.append({
            'name': f'{pressure:.0f}torr',
            'molecule': molecule,
            'concentration': base_conc,
            'temperature': base_temp,
            'pressure': pressure,
            'path_length': base_path
        })

else:  # 사용자 정의
    st.sidebar.write("**사용자 정의 조건들**")
    num_conditions = st.sidebar.slider("비교할 조건 수", 2, 8, 3)
    
    conditions = []
    for i in range(num_conditions):
        st.sidebar.write(f"--- 조건 {i+1} ---")
        name = st.sidebar.text_input(f"조건 {i+1} 이름", value=f"조건{i+1}", key=f"name_{i}")
        conc = st.sidebar.number_input(f"농도 (ppb)", value=1000.0, key=f"conc_{i}")
        temp = st.sidebar.number_input(f"온도 (K)", value=296.15, key=f"temp_{i}")
        pressure = st.sidebar.number_input(f"압력 (torr)", value=760.0, key=f"pressure_{i}")
        path = st.sidebar.number_input(f"경로 길이 (m)", value=1000.0, key=f"path_{i}")
        
        conditions.append({
            'name': name,
            'molecule': molecule,
            'concentration': conc,
            'temperature': temp,
            'pressure': pressure,
            'path_length': path
        })

# 계산 버튼
calculate_button = st.sidebar.button("🧮 비교 스펙트럼 계산", type="primary")

# 결과 초기화 버튼
if st.session_state.comparison_results:
    if st.sidebar.button("🗑️ 결과 초기화"):
        st.session_state.comparison_results = []
        st.session_state.comparison_count = 0
        st.rerun()

# 메인 화면
col1, col2 = st.columns([3, 1])

with col2:
    st.subheader("📋 비교 조건")
    st.write(f"**분석 모드:** {comparison_mode}")
    st.write(f"**분자:** {molecule}")
    st.write(f"**파장 범위:** {wavelength_min}-{wavelength_max} nm")
    
    if conditions:
        st.subheader("🔍 조건 목록")
        for i, condition in enumerate(conditions):
            st.write(f"**{condition['name']}:**")
            st.write(f"- 농도: {condition['concentration']:.1f} ppb")
            st.write(f"- 온도: {condition['temperature']:.1f} K")
            st.write(f"- 압력: {condition['pressure']:.1f} torr")
            st.write(f"- 경로: {condition['path_length']:.0f} m")
            st.write("---")

# 계산 실행
with col1:
    if calculate_button and conditions:
        if wavelength_min >= wavelength_max:
            st.error("❌ 최소 파장이 최대 파장보다 작아야 합니다!")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # 주파수 격자 생성
                freq_min = 1e7 / wavelength_max
                freq_max = 1e7 / wavelength_min
                frequency_grid = np.linspace(freq_min, freq_max, 5000)
                wavelength_nm = 1e7 / frequency_grid
                
                hitran_api = HitranAPI()
                calc = SpectrumCalculator()
                
                # 각 조건별 스펙트럼 계산
                comparison_spectra = []
                
                for i, condition in enumerate(conditions):
                    progress = int((i / len(conditions)) * 90)
                    status_text.text(f"📥 {condition['name']} 계산 중... ({i+1}/{len(conditions)})")
                    progress_bar.progress(progress)
                    
                    # HITRAN 데이터 다운로드 (첫 번째 조건에서만)
                    if i == 0:
                        hitran_data = hitran_api.download_molecule_data(molecule, wavelength_min, wavelength_max)
                        if hitran_data is None or len(hitran_data) == 0:
                            st.error(f"❌ {molecule} 데이터를 찾을 수 없습니다!")
                            break
                    
                    # 스펙트럼 계산
                    spectrum = calc.calculate_absorption_spectrum(
                        hitran_data=hitran_data,
                        frequency_grid=frequency_grid,
                        temperature=condition['temperature'],
                        pressure=condition['pressure'] / 760.0,  # torr to atm
                        concentration=condition['concentration'] / 1e9,  # ppb to 몰분율
                        path_length=condition['path_length'],
                        molecule=molecule
                    )
                    
                    comparison_spectra.append({
                        'condition': condition,
                        'spectrum': spectrum
                    })
                
                progress_bar.progress(100)
                status_text.text("✅ 비교 스펙트럼 계산 완료!")
                
                # 결과 저장
                result = {
                    'id': st.session_state.comparison_count,
                    'mode': comparison_mode,
                    'molecule': molecule,
                    'wavelength_range': f"{wavelength_min}-{wavelength_max}nm",
                    'wavelength_nm': wavelength_nm,
                    'spectra': comparison_spectra,
                    'timestamp': pd.Timestamp.now()
                }
                
                st.session_state.comparison_results.append(result)
                st.session_state.comparison_count += 1
                
            except Exception as e:
                st.error(f"❌ 에러 발생: {str(e)}")
                progress_bar.empty()
                status_text.empty()

# 결과 표시
if st.session_state.comparison_results:
    latest_result = st.session_state.comparison_results[-1]
    
    with col1:
        st.subheader(f"📊 {latest_result['mode']} 결과")
        
        # 색상 팔레트
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
        color_cycle = cycle(colors)
        
        # 비교 그래프 생성
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('투과율 비교', '흡광도 비교', '최대 흡광도 vs 조건', '차이 스펙트럼'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # 기준 스펙트럼 (첫 번째)
        reference_spectrum = latest_result['spectra'][0]['spectrum']
        
        # 1. 투과율 비교
        for i, spec_data in enumerate(latest_result['spectra']):
            color = next(color_cycle)
            fig.add_trace(
                go.Scatter(
                    x=latest_result['wavelength_nm'],
                    y=spec_data['spectrum']['transmittance'],
                    mode='lines',
                    name=spec_data['condition']['name'],
                    line=dict(color=color, width=2)
                ),
                row=1, col=1
            )
        
        # 색상 사이클 리셋
        color_cycle = cycle(colors)
        
        # 2. 흡광도 비교
        for i, spec_data in enumerate(latest_result['spectra']):
            color = next(color_cycle)
            fig.add_trace(
                go.Scatter(
                    x=latest_result['wavelength_nm'],
                    y=spec_data['spectrum']['absorbance'],
                    mode='lines',
                    name=spec_data['condition']['name'],
                    line=dict(color=color, width=2),
                    showlegend=False
                ),
                row=1, col=2
            )
        
        # 3. 최대 흡광도 vs 조건
        if comparison_mode == "농도별 비교":
            x_values = [spec['condition']['concentration'] for spec in latest_result['spectra']]
            x_title = "농도 (ppb)"
        elif comparison_mode == "온도별 비교":
            x_values = [spec['condition']['temperature'] for spec in latest_result['spectra']]
            x_title = "온도 (K)"
        elif comparison_mode == "압력별 비교":
            x_values = [spec['condition']['pressure'] for spec in latest_result['spectra']]
            x_title = "압력 (torr)"
        else:
            x_values = [spec['condition']['name'] for spec in latest_result['spectra']]
            x_title = "조건"
        
        y_values = [np.max(spec['spectrum']['absorbance']) for spec in latest_result['spectra']]
        
        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode='markers+lines',
                name='최대 흡광도',
                marker=dict(size=8, color='red'),
                line=dict(color='red', width=2),
                showlegend=False
            ),
            row=2, col=1
        )
        
        # 4. 차이 스펙트럼 (기준 대비)
        for i, spec_data in enumerate(latest_result['spectra'][1:], 1):
            color = colors[i % len(colors)]
            diff_spectrum = spec_data['spectrum']['absorbance'] - reference_spectrum['absorbance']
            fig.add_trace(
                go.Scatter(
                    x=latest_result['wavelength_nm'],
                    y=diff_spectrum,
                    mode='lines',
                    name=f"{spec_data['condition']['name']} - {latest_result['spectra'][0]['condition']['name']}",
                    line=dict(color=color, width=1),
                    showlegend=False
                ),
                row=2, col=2
            )
        
        # 레이아웃 업데이트
        fig.update_layout(height=800, showlegend=True)
        fig.update_xaxes(title_text="파장 (nm)", row=1, col=1)
        fig.update_xaxes(title_text="파장 (nm)", row=1, col=2)
        fig.update_xaxes(title_text=x_title, row=2, col=1)
        fig.update_xaxes(title_text="파장 (nm)", row=2, col=2)
        
        fig.update_yaxes(title_text="투과율", row=1, col=1)
        fig.update_yaxes(title_text="흡광도", row=1, col=2)
        fig.update_yaxes(title_text="최대 흡광도", row=2, col=1)
        fig.update_yaxes(title_text="흡광도 차이", row=2, col=2)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 통계 분석
        st.subheader("📈 통계 분석")
        
        stats_data = []
        for spec_data in latest_result['spectra']:
            stats_data.append({
                '조건': spec_data['condition']['name'],
                '최대 흡광도': f"{np.max(spec_data['spectrum']['absorbance']):.4f}",
                '최소 투과율': f"{np.min(spec_data['spectrum']['transmittance']):.4f}",
                '평균 흡광도': f"{np.mean(spec_data['spectrum']['absorbance']):.4f}",
                '흡광도 표준편차': f"{np.std(spec_data['spectrum']['absorbance']):.4f}"
            })
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True)
        
        # 검량선 분석 (농도별 비교인 경우)
        if comparison_mode == "농도별 비교":
            st.subheader("📏 검량선 분석")
            
            concentrations = [spec['condition']['concentration'] for spec in latest_result['spectra']]
            max_absorbances = [np.max(spec['spectrum']['absorbance']) for spec in latest_result['spectra']]
            
            # 선형 회귀
            coeffs = np.polyfit(concentrations, max_absorbances, 1)
            r_squared = np.corrcoef(concentrations, max_absorbances)[0, 1]**2
            
            col_cal1, col_cal2 = st.columns(2)
            
            with col_cal1:
                st.metric("기울기", f"{coeffs[0]:.2e}")
                st.metric("절편", f"{coeffs[1]:.4f}")
            
            with col_cal2:
                st.metric("R²", f"{r_squared:.4f}")
                st.metric("검출한계 (3σ)", f"{3 * np.std(max_absorbances) / coeffs[0]:.1f} ppb")
        
        # 데이터 내보내기
        st.subheader("📁 비교 데이터 내보내기")
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            # 모든 스펙트럼 데이터 CSV
            export_data = {'Wavelength_nm': latest_result['wavelength_nm']}
            
            for spec_data in latest_result['spectra']:
                name = spec_data['condition']['name']
                export_data[f'{name}_Transmittance'] = spec_data['spectrum']['transmittance']
                export_data[f'{name}_Absorbance'] = spec_data['spectrum']['absorbance']
            
            export_df = pd.DataFrame(export_data)
            csv_data = export_df.to_csv(index=False)
            
            st.download_button(
                label="📊 비교 스펙트럼 데이터 (CSV)",
                data=csv_data,
                file_name=f"comparison_{latest_result['mode']}_{latest_result['molecule']}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col_exp2:
            # 통계 데이터 CSV
            stats_csv = stats_df.to_csv(index=False)
            
            st.download_button(
                label="📈 통계 분석 데이터 (CSV)",
                data=stats_csv,
                file_name=f"stats_{latest_result['mode']}_{latest_result['molecule']}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

# 하단 정보
st.markdown("---")
st.markdown("**개발:** HITRAN CRDS Spectrum Comparison Tool v1.0 | **데이터:** HITRAN Database")