"""
CIA (Collision-Induced Absorption) UI Component
"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.cia_calculator import CIACalculator


def show_cia_settings() -> dict:
    """사이드바 CIA 설정 UI, cia_config 반환"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("💨 CIA 설정")

    enabled = st.sidebar.checkbox("CIA 계산 활성화", value=False, key="cia_enabled")

    if not enabled:
        return {'enabled': False, 'pairs': []}

    calc = CIACalculator()
    available_pairs = list(calc.supported_pairs.keys())

    selected_pairs = st.sidebar.multiselect(
        "CIA 분자 쌍 선택",
        options=available_pairs,
        default=['N2-N2', 'O2-O2'],
        key="cia_pairs"
    )

    return {'enabled': enabled, 'pairs': selected_pairs}


def calculate_cia_contribution(cia_config: dict, wl_grid: np.ndarray, temperature: float,
                                concentrations: dict, pressure_atm: float, path_length: float) -> dict:
    """
    CIA 기여도 계산

    Args:
        cia_config: CIA 설정 (enabled, pairs)
        wl_grid: 파장 그리드 (nm)
        temperature: 온도 (K)
        concentrations: 분자별 농도 (ppb)
        pressure_atm: 압력 (atm)
        path_length: 광경로 (m)

    Returns:
        dict: pair -> absorption array (nm 공간)
    """
    if not cia_config.get('enabled') or not cia_config.get('pairs'):
        return {}

    # nm → cm⁻¹ 변환
    wavenumber = 1e7 / wl_grid
    sort_idx = np.argsort(wavenumber)
    wn_sorted = wavenumber[sort_idx]

    path_cm = path_length * 100  # m → cm

    calc = CIACalculator()
    results = {}

    for pair in cia_config['pairs']:
        mol1, mol2 = pair.split('-')

        if mol1 not in concentrations or mol2 not in concentrations:
            continue

        density1 = calc.get_density_from_concentration(
            mol1, concentrations[mol1], temperature, pressure_atm
        )
        density2 = calc.get_density_from_concentration(
            mol2, concentrations[mol2], temperature, pressure_atm
        )

        wn_range = (float(wn_sorted.min()), float(wn_sorted.max()))
        if calc.load_cia_data(pair, wn_range):
            cia_sorted = calc.calculate_cia_absorption(
                pair, wn_sorted, temperature, density1, density2, path_cm
            )
            cia = np.zeros_like(wl_grid)
            cia[sort_idx] = cia_sorted
            results[pair] = np.maximum(cia, 0)

    return results


def show_cia_analysis(cia_results: dict, wl_grid: np.ndarray) -> np.ndarray:
    """
    CIA 분석 결과 표시

    Returns:
        np.ndarray: 전체 CIA 흡수 합계
    """
    if not cia_results:
        st.info("CIA 계산 결과가 없습니다.")
        return np.zeros_like(wl_grid)

    st.subheader("💨 CIA 분석 결과")

    fig = go.Figure()
    total_cia = np.zeros_like(wl_grid)
    colors = ['red', 'orange', 'green', 'purple', 'brown', 'pink']

    for i, (pair, absorption) in enumerate(cia_results.items()):
        fig.add_trace(go.Scatter(
            x=wl_grid, y=absorption,
            name=pair, line=dict(color=colors[i % len(colors)], width=2)
        ))
        total_cia += absorption

    if len(cia_results) > 1:
        fig.add_trace(go.Scatter(
            x=wl_grid, y=total_cia,
            name="CIA 합계", line=dict(color='black', width=3, dash='dash')
        ))

    fig.update_layout(
        title="분자 쌍별 CIA 흡수",
        xaxis_title="파장 (nm)", yaxis_title="CIA 흡수도", height=400
    )
    st.plotly_chart(fig, use_container_width=True)

    cols = st.columns(len(cia_results))
    for i, (pair, absorption) in enumerate(cia_results.items()):
        with cols[i]:
            st.metric(pair, f"{np.max(absorption):.2e}", "최대 흡수")

    return total_cia


def combine_cia_with_line_absorption(molecular_results: dict, cia_results: dict,
                                      wl_grid: np.ndarray) -> np.ndarray:
    """분자 라인 흡수와 CIA 흡수 합산"""
    total = np.zeros_like(wl_grid)

    for mol, spec in molecular_results.items():
        if mol not in ['cia', 'combined', 'combined_oa_icos'] and not mol.endswith('_oa_icos'):
            if isinstance(spec, dict) and 'absorbance' in spec:
                total += spec['absorbance']

    for absorption in cia_results.values():
        total += absorption

    return total


def show_cia_info():
    """CIA 개념 설명 UI"""
    with st.expander("💡 CIA (Collision-Induced Absorption) 란?", expanded=False):
        st.markdown("""
        **CIA**는 두 분자가 충돌하는 순간 일시적으로 쌍을 이루면서 빛을 흡수하는 현상입니다.

        - **특징**: 특정 피크 없이 넓은 파장 대역에 걸쳐 흡수 발생
        - **중요 조건**: 고압 환경 (압력이 높을수록 CIA 증가)
        - **주요 분자 쌍**: N₂-N₂, O₂-O₂, H₂-H₂, CO₂-CO₂

        | 분자 쌍 | 주요 흡수 영역 |
        |---------|--------------|
        | N₂-N₂ | 중적외선 (4 μm) |
        | O₂-O₂ | 근적외선 (1.27 μm) |
        | H₂-H₂ | 원적외선 (< 10 μm) |
        | CO₂-CO₂ | 중적외선 (4.3 μm) |
        """)


def create_cia_demo():
    """시뮬레이션 실행 전 CIA 샘플 미리보기"""
    st.info("💡 사이드바에서 CIA를 활성화하고 스펙트럼 계산을 실행하면 실제 CIA 분석 결과가 표시됩니다.")

    st.subheader("CIA 샘플 미리보기 (N₂-N₂, O₂-O₂, CO₂-CO₂)")

    calc = CIACalculator()
    wl_demo = np.linspace(1000, 5000, 500)
    wn_demo = 1e7 / wl_demo
    sort_idx = np.argsort(wn_demo)
    wn_sorted = wn_demo[sort_idx]

    fig = go.Figure()
    demo_pairs = [('N2-N2', 'blue'), ('O2-O2', 'green'), ('CO2-CO2', 'red')]

    for pair, color in demo_pairs:
        wn_range = (float(wn_sorted.min()), float(wn_sorted.max()))
        if calc.load_cia_data(pair, wn_range):
            density = 2.5e19
            cia_sorted = calc.calculate_cia_absorption(
                pair, wn_sorted, 296.15, density, density, 100000
            )
            cia = np.zeros(len(wl_demo))
            cia[sort_idx] = cia_sorted
            fig.add_trace(go.Scatter(
                x=wl_demo, y=np.maximum(cia, 0),
                name=pair, line=dict(color=color, width=2)
            ))

    fig.update_layout(
        title="CIA 흡수 샘플 (대기 조건, 경로 1 km)",
        xaxis_title="파장 (nm)", yaxis_title="CIA 흡수도", height=350
    )
    st.plotly_chart(fig, use_container_width=True)
