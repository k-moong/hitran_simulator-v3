"""
HITRAN CRDS 시뮬레이터 - 농도별 시뮬레이션 탭 추가 (간결한 버전)
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import io
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from data_handler.hitran_api import HitranAPI
from spectrum_calc.absorption import SpectrumCalculator
from constants import HITRAN_MOLECULES, MOLECULE_CATEGORIES, WAVELENGTH_SHORTCUTS, DEFAULT_CONCENTRATIONS

# 페이지 설정
st.set_page_config(
    page_title="HITRAN CRDS Simulator Enhanced",
    page_icon="🌟",
    layout="wide"
)

# Session State 초기화
for key in ['calculation_results', 'calculation_params', 'concentration_results', 'concentration_params']:
    if key not in st.session_state:
        st.session_state[key] = None

# 제목
st.title("🌟 HITRAN CRDS Simulator Enhanced")
st.markdown("**전체 HITRAN 분자 지원 및 농도별 시뮬레이션**")

# 메인 탭 생성
tab1, tab2 = st.tabs(["🧪 혼합 스펙트럼", "📊 농도별 시뮬레이션"])

# =====================================
# 탭 1: 혼합 스펙트럼
# =====================================
with tab1:
    # 사이드바 - 파라미터 설정
    with st.sidebar:
        st.header("📊 혼합 스펙트럼 파라미터")
        
        # 분자 선택
        st.subheader("🧪 분자 선택")
        selection_method = st.radio("선택 방법:", ["카테고리별", "자주 사용", "전체 목록"], index=0)
        
        selected_molecules = []
        if selection_method == "카테고리별":
            selected_category = st.selectbox("분자 카테고리", list(MOLECULE_CATEGORIES.keys()))
            available_mols = MOLECULE_CATEGORIES[selected_category]
            selected_molecules = st.multiselect(
                f"{selected_category} ({len(available_mols)}개)",
                available_mols,
                default=available_mols[:3] if len(available_mols) >= 3 else available_mols,
                format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})"
            )
        elif selection_method == "자주 사용":
            common_molecules = [mol for mol, info in HITRAN_MOLECULES.items() if info["common"]]
            selected_molecules = st.multiselect(
                f"자주 사용하는 분자 ({len(common_molecules)}개)",
                common_molecules,
                default=["H2O", "CO2", "CH4"],
                format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})"
            )
        else:
            all_molecules = list(HITRAN_MOLECULES.keys())
            selected_molecules = st.multiselect(
                f"전체 분자 목록 ({len(all_molecules)}개)",
                all_molecules,
                default=["H2O"],
                format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})",
                help="최대 15개까지 선택 가능합니다."
            )
        
        if selected_molecules:
            st.success(f"✅ {len(selected_molecules)}개 분자 선택됨")
            if len(selected_molecules) > 15:
                st.warning("⚠️ 최대 15개까지만 선택해주세요.")
                selected_molecules = selected_molecules[:15]
        
        # 파장 범위
        st.subheader("📏 파장 범위 (nm)")
        with st.expander("🔗 파장 대역 바로가기"):
            for shortcut_id, shortcut_data in WAVELENGTH_SHORTCUTS.items():
                if st.button(f"{shortcut_data['description']}", key=f"mix_{shortcut_id}"):
                    st.session_state.mix_wl_min = float(shortcut_data['min'])
                    st.session_state.mix_wl_max = float(shortcut_data['max'])
                    st.rerun()
        
        col1, col2 = st.columns(2)
        with col1:
            wavelength_min = st.number_input("최소", value=st.session_state.get('mix_wl_min', 1500.0), min_value=100.0, max_value=50000.0, step=0.01)
        with col2:
            wavelength_max = st.number_input("최대", value=st.session_state.get('mix_wl_max', 1520.0), min_value=100.0, max_value=50000.0, step=0.01)
        
        # 물리 조건
        st.subheader("🌡️ 물리 조건")
        temperature = st.number_input("온도 (K)", value=296.15, min_value=200.0, max_value=400.0, step=0.1)
        pressure_torr = st.number_input("압력 (torr)", value=760.0, min_value=1.0, max_value=15000.0, step=1.0)
        path_length_m = st.number_input("경로 길이 (m)", value=1000.0, min_value=1.0, max_value=50000.0, step=1.0)
        
        # 분자별 농도 설정
        molecule_concentrations = {}
        if selected_molecules:
            st.subheader("🧪 분자별 농도 (ppb)")
            conc_method = st.radio("농도 입력 방식", ["개별 설정", "일괄 설정"], index=0)
            
            if conc_method == "일괄 설정":
                bulk_concentration = st.number_input("모든 분자 농도 (ppb)", value=1000.0, min_value=0.1, max_value=10000000.0, step=0.1)
                for molecule in selected_molecules:
                    molecule_concentrations[molecule] = bulk_concentration
            else:
                for molecule in selected_molecules:
                    default_conc = DEFAULT_CONCENTRATIONS.get(molecule, 100.0)
                    concentration = st.number_input(
                        f"{molecule} ({HITRAN_MOLECULES[molecule]['name']})",
                        value=default_conc,
                        min_value=0.1,
                        max_value=10000000.0,
                        step=0.1,
                        key=f"conc_{molecule}"
                    )
                    molecule_concentrations[molecule] = concentration
        
        # 계산 버튼
        st.markdown("---")
        calculate_button = st.button("🧮 혼합 스펙트럼 계산", type="primary", use_container_width=True)
        
        if st.session_state.calculation_results is not None:
            if st.button("🗑️ 결과 초기화", type="secondary", use_container_width=True):
                st.session_state.calculation_results = None
                st.session_state.calculation_params = None
                st.rerun()

    # 메인 화면
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.subheader("📋 현재 설정")
        st.write(f"**선택된 분자:** {len(selected_molecules)}개")
        
        if selected_molecules:
            categories_used = {}
            for mol in selected_molecules:
                cat = HITRAN_MOLECULES[mol]["category"]
                categories_used.setdefault(cat, []).append(mol)
            
            for cat, mols in categories_used.items():
                st.write(f"  - **{cat}:** {', '.join(mols)}")
        
        pressure_atm = pressure_torr / 760.0
        path_length_km = path_length_m / 1000.0
        
        st.write(f"**온도:** {temperature} K ({temperature-273.15:.1f}°C)")
        st.write(f"**압력:** {pressure_torr:.1f} torr ({pressure_atm:.2f} atm)")
        st.write(f"**경로 길이:** {path_length_m:.0f} m ({path_length_km:.1f} km)")
        st.write(f"**파장 범위:** {wavelength_min:.2f}-{wavelength_max:.2f} nm")
    
    # 혼합 스펙트럼 계산 및 결과 표시
    with col1:
        if calculate_button and selected_molecules and wavelength_min < wavelength_max:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # 주파수 격자 생성
                freq_min = 1e7 / wavelength_max
                freq_max = 1e7 / wavelength_min
                frequency_grid = np.linspace(freq_min, freq_max, 5000)
                
                # API 초기화
                hitran_api = HitranAPI()
                calc = SpectrumCalculator()
                
                # 각 분자별 스펙트럼 계산
                individual_spectra = {}
                combined_absorption = np.zeros_like(frequency_grid)
                failed_molecules = []
                
                for i, molecule in enumerate(selected_molecules):
                    progress = int(20 + (i / len(selected_molecules)) * 60)
                    status_text.text(f"📥 {molecule} 데이터 처리 중... ({i+1}/{len(selected_molecules)})")
                    progress_bar.progress(progress)
                    
                    try:
                        hitran_data = hitran_api.download_molecule_data(molecule, wavelength_min, wavelength_max)
                        
                        if hitran_data is not None and len(hitran_data) > 0:
                            concentration = molecule_concentrations[molecule] / 1e9
                            spectrum = calc.calculate_absorption_spectrum(
                                hitran_data=hitran_data,
                                frequency_grid=frequency_grid,
                                temperature=temperature,
                                pressure=pressure_atm,
                                concentration=concentration,
                                path_length=path_length_m,
                                molecule=molecule
                            )
                            individual_spectra[molecule] = spectrum
                            combined_absorption += spectrum['absorption_coeff']
                        else:
                            failed_molecules.append(molecule)
                    except Exception as e:
                        failed_molecules.append(molecule)
                
                # 결과 저장
                if individual_spectra:
                    status_text.text("🧮 혼합 스펙트럼 계산 중...")
                    progress_bar.progress(90)
                    
                    combined_transmittance = np.exp(-combined_absorption * path_length_m)
                    combined_absorbance = -np.log10(combined_transmittance)
                    wavelength_nm = 1e7 / frequency_grid
                    
                    st.session_state.calculation_results = {
                        'individual_spectra': individual_spectra,
                        'combined_transmittance': combined_transmittance,
                        'combined_absorbance': combined_absorbance,
                        'wavelength_nm': wavelength_nm,
                        'failed_molecules': failed_molecules
                    }
                    
                    progress_bar.progress(100)
                    status_text.text("✅ 계산 완료!")
                    
                else:
                    st.error("❌ 선택한 파장 범위에서 사용 가능한 분자 데이터가 없습니다!")
                    
            except Exception as e:
                st.error(f"❌ 에러 발생: {str(e)}")
        
        # 결과 표시
        if st.session_state.calculation_results is not None:
            results = st.session_state.calculation_results
            
            st.subheader("📊 스펙트럼 결과")
            
            if results.get('failed_molecules'):
                st.warning(f"⚠️ 데이터 없음: {', '.join(results['failed_molecules'])}")
            
            # 그래프 생성
            fig = make_subplots(
                rows=3, cols=1,
                subplot_titles=('개별 분자 흡광도', '혼합 투과율', '혼합 흡광도'),
                vertical_spacing=0.08
            )
            
            colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
            
            # 개별 분자 흡광도
            for i, (molecule, spectrum) in enumerate(results['individual_spectra'].items()):
                fig.add_trace(
                    go.Scatter(
                        x=results['wavelength_nm'],
                        y=spectrum['absorbance'],
                        mode='lines',
                        name=f'{molecule} ({HITRAN_MOLECULES[molecule]["name"]})',
                        line=dict(color=colors[i % len(colors)], width=1)
                    ),
                    row=1, col=1
                )
            
            # 혼합 투과율
            fig.add_trace(
                go.Scatter(
                    x=results['wavelength_nm'],
                    y=results['combined_transmittance'],
                    mode='lines',
                    name='혼합 투과율',
                    line=dict(color='black', width=2)
                ),
                row=2, col=1
            )
            
            # 혼합 흡광도
            fig.add_trace(
                go.Scatter(
                    x=results['wavelength_nm'],
                    y=results['combined_absorbance'],
                    mode='lines',
                    name='혼합 흡광도',
                    line=dict(color='darkred', width=2)
                ),
                row=3, col=1
            )
            
            fig.update_layout(height=800, showlegend=True)
            fig.update_xaxes(title_text="파장 (nm)", row=3, col=1)
            fig.update_yaxes(title_text="흡광도", row=1, col=1)
            fig.update_yaxes(title_text="투과율", row=2, col=1)
            fig.update_yaxes(title_text="흡광도", row=3, col=1)
            
            st.plotly_chart(fig, use_container_width=True)

# =====================================
# 탭 2: 농도별 시뮬레이션
# =====================================
with tab2:
    st.header("📊 농도별 시뮬레이션")
    st.markdown("**단일 분자의 농도 변화에 따른 스펙트럼 변화를 분석합니다**")
    
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("🔧 시뮬레이션 설정")
        
        # 분자 선택
        st.write("**분석할 분자 선택:**")
        conc_method = st.radio("선택 방법:", ["자주 사용", "카테고리별", "전체 목록"], index=0, key="conc_method")
        
        selected_molecule = None
        if conc_method == "자주 사용":
            common_molecules = [mol for mol, info in HITRAN_MOLECULES.items() if info["common"]]
            selected_molecule = st.selectbox(
                "분자 선택:",
                common_molecules,
                format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})"
            )
        elif conc_method == "카테고리별":
            conc_category = st.selectbox("분자 카테고리:", list(MOLECULE_CATEGORIES.keys()))
            available_mols = MOLECULE_CATEGORIES[conc_category]
            selected_molecule = st.selectbox(
                "분자 선택:",
                available_mols,
                format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})"
            )
        else:
            all_molecules = list(HITRAN_MOLECULES.keys())
            selected_molecule = st.selectbox(
                "분자 선택:",
                all_molecules,
                format_func=lambda x: f"{x} ({HITRAN_MOLECULES[x]['name']})"
            )
        
        if selected_molecule:
            mol_info = HITRAN_MOLECULES[selected_molecule]
            st.info(f"**선택된 분자:** {selected_molecule} ({mol_info['name']})")
        
        # 농도 범위 설정
        st.write("**농도 범위 설정 (ppb):**")
        default_min, default_max = (1000, 50000) if selected_molecule == "H2O" else (10, 5000)
        
        conc_min = st.number_input("최소 농도 (ppb):", value=float(default_min), min_value=0.1, max_value=10000000.0)
        conc_max = st.number_input("최대 농도 (ppb):", value=float(default_max), min_value=0.1, max_value=10000000.0)
        conc_steps = st.slider("농도 단계 수:", min_value=3, max_value=20, value=8)
        
        # 파장 범위
        st.write("**파장 범위 (nm):**")
        with st.expander("🔗 파장 대역 바로가기"):
            for shortcut_id, shortcut_data in WAVELENGTH_SHORTCUTS.items():
                if st.button(f"{shortcut_data['description']}", key=f"conc_{shortcut_id}"):
                    st.session_state.conc_wl_min = float(shortcut_data['min'])
                    st.session_state.conc_wl_max = float(shortcut_data['max'])
                    st.rerun()
        
        col_wl1, col_wl2 = st.columns(2)
        with col_wl1:
            conc_wavelength_min = st.number_input("최소:", value=st.session_state.get('conc_wl_min', 1500.0), min_value=100.0, max_value=50000.0)
        with col_wl2:
            conc_wavelength_max = st.number_input("최대:", value=st.session_state.get('conc_wl_max', 1520.0), min_value=100.0, max_value=50000.0)
        
        # 물리 조건
        st.write("**물리 조건:**")
        conc_temperature = st.number_input("온도 (K):", value=296.15, min_value=200.0, max_value=400.0)
        conc_pressure_torr = st.number_input("압력 (torr):", value=760.0, min_value=1.0, max_value=15000.0)
        conc_path_length_m = st.number_input("경로 길이 (m):", value=1000.0, min_value=1.0, max_value=50000.0)
        
        # 계산 버튼
        st.markdown("---")
        conc_calc_button = st.button("🔬 농도별 시뮬레이션 실행", type="primary", use_container_width=True)
        
        if st.session_state.concentration_results is not None:
            if st.button("🗑️ 결과 초기화", type="secondary", use_container_width=True, key="conc_clear"):
                st.session_state.concentration_results = None
                st.session_state.concentration_params = None
                st.rerun()
    
    # 농도별 시뮬레이션 실행 및 결과
    with col_right:
        if conc_calc_button and selected_molecule and conc_wavelength_min < conc_wavelength_max and conc_min < conc_max:
            st.subheader(f"🔬 {selected_molecule} 농도별 스펙트럼 분석")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # 농도 배열 생성
                concentrations_ppb = np.linspace(conc_min, conc_max, conc_steps)
                
                # 주파수 격자 생성
                freq_min = 1e7 / conc_wavelength_max
                freq_max = 1e7 / conc_wavelength_min
                frequency_grid = np.linspace(freq_min, freq_max, 3000)
                wavelength_nm = 1e7 / frequency_grid
                
                # API 초기화
                hitran_api = HitranAPI()
                calc = SpectrumCalculator()
                
                # HITRAN 데이터 다운로드
                status_text.text(f"📥 {selected_molecule} HITRAN 데이터 다운로드 중...")
                progress_bar.progress(10)
                
                hitran_data = hitran_api.download_molecule_data(selected_molecule, conc_wavelength_min, conc_wavelength_max)
                
                if hitran_data is None or len(hitran_data) == 0:
                    st.error(f"❌ {selected_molecule} 데이터를 찾을 수 없습니다")
                else:
                    # 각 농도별 스펙트럼 계산
                    conc_pressure_atm = conc_pressure_torr / 760.0
                    concentration_spectra = {}
                    
                    for i, conc_ppb in enumerate(concentrations_ppb):
                        progress = int(10 + (i / len(concentrations_ppb)) * 80)
                        status_text.text(f"🧮 농도 {conc_ppb:.1f} ppb 계산 중... ({i+1}/{conc_steps})")
                        progress_bar.progress(progress)
                        
                        concentration_molfrac = conc_ppb / 1e9
                        spectrum = calc.calculate_absorption_spectrum(
                            hitran_data=hitran_data,
                            frequency_grid=frequency_grid,
                            temperature=conc_temperature,
                            pressure=conc_pressure_atm,
                            concentration=concentration_molfrac,
                            path_length=conc_path_length_m,
                            molecule=selected_molecule
                        )
                        concentration_spectra[conc_ppb] = spectrum
                    
                    # 분석 데이터 생성
                    status_text.text("📊 분석 데이터 생성 중...")
                    progress_bar.progress(90)
                    
                    max_absorbances = [np.max(concentration_spectra[c]['absorbance']) for c in concentrations_ppb]
                    avg_absorbances = [np.mean(concentration_spectra[c]['absorbance']) for c in concentrations_ppb]
                    min_transmittances = [np.min(concentration_spectra[c]['transmittance']) for c in concentrations_ppb]
                    
                    # 결과 저장
                    st.session_state.concentration_results = {
                        'selected_molecule': selected_molecule,
                        'concentrations_ppb': concentrations_ppb,
                        'wavelength_nm': wavelength_nm,
                        'concentration_spectra': concentration_spectra,
                        'max_absorbances': max_absorbances,
                        'avg_absorbances': avg_absorbances,
                        'min_transmittances': min_transmittances,
                        'total_lines': len(hitran_data)
                    }
                    
                    st.session_state.concentration_params = {
                        'selected_molecule': selected_molecule,
                        'conc_min': conc_min,
                        'conc_max': conc_max,
                        'conc_steps': conc_steps,
                        'wavelength_min': conc_wavelength_min,
                        'wavelength_max': conc_wavelength_max,
                        'temperature': conc_temperature,
                        'pressure_torr': conc_pressure_torr
                    }
                    
                    progress_bar.progress(100)
                    status_text.text("✅ 농도별 시뮬레이션 완료!")
                    
            except Exception as e:
                st.error(f"❌ 에러 발생: {str(e)}")
        
        # 결과 표시
        if st.session_state.concentration_results is not None:
            conc_results = st.session_state.concentration_results
            conc_params = st.session_state.concentration_params
            
            st.subheader(f"📊 {conc_results['selected_molecule']} 농도별 분석 결과")
            
            # 결과 요약
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("분석 분자", conc_results['selected_molecule'])
            with col2:
                st.metric("농도 범위", f"{conc_params['conc_min']:.1f}-{conc_params['conc_max']:.1f} ppb")
            with col3:
                st.metric("농도 단계", f"{conc_params['conc_steps']}")
            with col4:
                st.metric("HITRAN 라인", f"{conc_results['total_lines']:,}")
            
            # 그래프
            col_graph1, col_graph2 = st.columns(2)
            
            with col_graph1:
                # 농도별 스펙트럼
                st.write("**농도별 스펙트럼 변화**")
                fig_spectrum = go.Figure()
                
                colors = ['darkblue', 'blue', 'green', 'orange', 'red', 'darkred']
                for i, conc_ppb in enumerate(conc_results['concentrations_ppb']):
                    color_idx = min(int(i * len(colors) / len(conc_results['concentrations_ppb'])), len(colors)-1)
                    spectrum = conc_results['concentration_spectra'][conc_ppb]
                    
                    fig_spectrum.add_trace(
                        go.Scatter(
                            x=conc_results['wavelength_nm'],
                            y=spectrum['absorbance'],
                            mode='lines',
                            name=f'{conc_ppb:.1f} ppb',
                            line=dict(color=colors[color_idx], width=2)
                        )
                    )
                
                fig_spectrum.update_layout(
                    title=f"{conc_results['selected_molecule']} 농도별 흡광도",
                    xaxis_title="파장 (nm)",
                    yaxis_title="흡광도",
                    height=400
                )
                st.plotly_chart(fig_spectrum, use_container_width=True)
            
            with col_graph2:
                # 농도 vs 최대 흡광도
                st.write("**농도 vs 최대 흡광도 관계**")
                fig_linearity = go.Figure()
                
                # 데이터 점
                fig_linearity.add_trace(
                    go.Scatter(
                        x=conc_results['concentrations_ppb'],
                        y=conc_results['max_absorbances'],
                        mode='markers+lines',
                        name='최대 흡광도',
                        line=dict(color='red', width=2),
                        marker=dict(size=8, color='red')
                    )
                )
                
                # 선형 회귀
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    conc_results['concentrations_ppb'], 
                    conc_results['max_absorbances']
                )
                
                line_x = np.linspace(conc_params['conc_min'], conc_params['conc_max'], 100)
                line_y = slope * line_x + intercept
                
                fig_linearity.add_trace(
                    go.Scatter(
                        x=line_x,
                        y=line_y,
                        mode='lines',
                        name=f'회귀선 (R²={r_value**2:.4f})',
                        line=dict(color='blue', width=2, dash='dash')
                    )
                )
                
                fig_linearity.update_layout(
                    title="농도-흡광도 선형성 분석",
                    xaxis_title="농도 (ppb)",
                    yaxis_title="최대 흡광도",
                    height=400
                )
                st.plotly_chart(fig_linearity, use_container_width=True)
            
            # 선형성 분석 결과
            st.subheader("📈 선형성 분석")
            
            col_lin1, col_lin2, col_lin3, col_lin4 = st.columns(4)
            with col_lin1:
                st.metric("R² (결정계수)", f"{r_value**2:.6f}")
            with col_lin2:
                st.metric("기울기", f"{slope:.2e}")
            with col_lin3:
                st.metric("절편", f"{intercept:.2e}")
            with col_lin4:
                detection_limit = 3 * std_err / slope if slope != 0 else 0
                st.metric("검출한계 (3σ)", f"{detection_limit:.1f} ppb")
            
            # 선형성 평가
            if r_value**2 > 0.99:
                st.success("✅ 매우 우수한 선형성 (R² > 0.99)")
            elif r_value**2 > 0.95:
                st.info("✅ 우수한 선형성 (R² > 0.95)")
            elif r_value**2 > 0.90:
                st.warning("⚠️ 보통 선형성 (R² > 0.90)")
            else:
                st.error("❌ 낮은 선형성 (R² < 0.90)")
            
            # 데이터 테이블
            st.subheader("📋 농도별 상세 데이터")
            table_data = []
            for i, conc_ppb in enumerate(conc_results['concentrations_ppb']):
                table_data.append({
                    '농도 (ppb)': f"{conc_ppb:.1f}",
                    '농도 (ppm)': f"{conc_ppb/1000:.3f}",
                    '최대 흡광도': f"{conc_results['max_absorbances'][i]:.6f}",
                    '평균 흡광도': f"{conc_results['avg_absorbances'][i]:.6f}",
                    '최소 투과율': f"{conc_results['min_transmittances'][i]:.6f}"
                })
            
            st.dataframe(pd.DataFrame(table_data), use_container_width=True)

# 하단 정보
st.markdown("---")
col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.markdown("**개발:** HITRAN CRDS Simulator v5.0")
    st.markdown("**새로운 기능:** 농도별 시뮬레이션")

with col_info2:
    st.markdown("**데이터:** HITRAN Database")
    st.markdown(f"**지원 분자:** {len(HITRAN_MOLECULES)}개")

with col_info3:
    st.markdown("**분석 기능:** 혼합 스펙트럼 + 농도별 분석")
    st.markdown("**고급 기능:** 선형성 분석, 검출한계 추정")