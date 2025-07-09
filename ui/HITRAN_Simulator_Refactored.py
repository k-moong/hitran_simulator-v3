"""
HITRAN CRDS Simulator - 리팩토링된 버전
모듈화된 구조로 유지보수가 편하도록 개선
"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.components.sidebar import show_sidebar
from ui.components.simulation_engine import SimulationEngine
from ui.components.visualization import (
    show_oa_icos_performance_metrics,
    show_matrix_gas_info,
    plot_mixed_spectrum,
    plot_concentration_analysis,
    show_line_shape_comparison
)
from core.line_shape_calculator import LineShapeCalculator

def main():
    """메인 함수"""
    st.set_page_config(page_title="HITRAN CRDS Simulator", page_icon="🔬", layout="wide")
    st.title("🔬 HITRAN CRDS Simulator (리팩토링 완료)")

    # 사이드바에서 설정 가져오기
    config = show_sidebar()
    
    # 설정 요약 표시
    summary = f"모드: {config.spectrometer_mode}, 분석: {config.mode}, 온도: {config.temperature}K, 파장: {config.wavelength_min}~{config.wavelength_max} nm, 경로: {config.path_length:.1f}m, 해상도: {config.num_points:,} 포인트"
    if config.oa_icos:
        summary += f", 미러 R: {config.oa_icos.mirror_reflectivity}, 캐비티: {config.oa_icos.cavity_length}cm, 손실: {config.oa_icos.mirror_loss}, 노이즈: {config.oa_icos.detector_noise}, 드리프트: {config.oa_icos.baseline_drift}, Line Shape: {config.oa_icos.line_shape}"
    if config.matrix_gas:
        summary += f", Matrix Gas: {config.matrix_gas.gas_type}, 압력: {config.matrix_gas.total_pressure_torr:.1f} torr"
    st.info(summary)
    
    if config.mode == "🧪 혼합 스펙트럼":
        st.info(f"분자: {', '.join(config.molecules) if config.molecules else '선택 없음'}")
    else:
        st.info(f"분자: {config.molecule}, 농도: {config.concentration_min}~{config.concentration_max} ppb ({config.concentration_steps}단계)")
    if config.matrix_gas:
        st.info(f"Matrix Gas: {config.matrix_gas.gas_type}, 압력: {config.matrix_gas.total_pressure_torr:.1f} torr")

    # Line Shape 비교 예시
    st.subheader("🌊 Line Shape 모델 비교 예시")
    demo_x = np.linspace(-2, 2, 1000)
    demo_gamma_L = 0.3
    demo_gamma_G = 0.4
    line_calc = LineShapeCalculator()
    fig_demo = go.Figure()
    for shape_name, color in zip(["Voigt", "Gaussian", "Lorentzian", "Hartmann-Tran"], ["red", "blue", "green", "orange"]):
        y_demo = line_calc.calculate_line_shape(demo_x, 0, demo_gamma_L, demo_gamma_G, shape_name)
        fig_demo.add_trace(go.Scatter(x=demo_x, y=y_demo, name=shape_name, line=dict(color=color, width=2)))
    fig_demo.update_layout(title="Line Shape 모델 비교", xaxis_title="주파수 오프셋", yaxis_title="정규화된 강도", height=300)
    st.plotly_chart(fig_demo, use_container_width=True, key="main_line_shape_demo")

    # 시뮬레이션 실행 버튼
    btn_text = "🧮 혼합 스펙트럼 계산" if config.mode == "🧪 혼합 스펙트럼" else "📈 농도별 분석 실행"
    if st.button(btn_text, type="primary"):
        with st.spinner('계산 중...'):
            # 시뮬레이션 엔진 실행
            engine = SimulationEngine()
            result = engine.run_simulation(config)
            
            # 결과 시각화
            if config.mode == "🧪 혼합 스펙트럼":
                plot_mixed_spectrum(result.results, result.wavelength_grid, config)
            else:
                plot_concentration_analysis(result.results, result.wavelength_grid, config)

    # Line Shape 비교 시뮬레이션
    show_line_shape_comparison()
    
    # 하단 정보
    st.markdown("---")
    st.markdown("**🔬 HITRAN CRDS Simulator (리팩토링 완료)** | OA-ICOS 분광기 + Line Shape 시뮬레이션 | 실제 장비 스펙 반영")

if __name__ == "__main__":
    main() 