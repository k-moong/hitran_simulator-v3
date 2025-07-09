"""
시각화 컴포넌트
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, Any, List

from ui.models.config import SimulationConfig
from ui.utils.helpers import get_molecule_label
from core.oa_icos_simulator import OAICOSSimulator

def show_oa_icos_performance_metrics(config: SimulationConfig):
    """OA-ICOS 성능 지표 표시"""
    if config.spectrometer_mode == "🔬 분광기" and config.oa_icos:
        oa_icos_sim = OAICOSSimulator()
        params = config.oa_icos
        effective_path = oa_icos_sim.calculate_effective_path_length(
            params.mirror_reflectivity, params.cavity_length, params.mirror_loss
        )
        enhancement_factor = effective_path / params.cavity_length
        
        st.subheader("🔬 OA-ICOS 성능 지표 + Line Shape")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("유효 광경로", f"{effective_path:.1f} cm")
        with col2:
            st.metric("향상 인수", f"{enhancement_factor:.0f}x")
        with col3:
            st.metric("미러 반사율", f"{params.mirror_reflectivity:.5f}")
        with col4:
            st.metric("레이저 선폭", "N/A")
        with col5:
            line_shape_display = params.line_shape
            st.metric("Line Shape", line_shape_display)

def show_matrix_gas_info(config: SimulationConfig):
    """Matrix Gas 정보 표시"""
    if config.matrix_gas:
        st.subheader("🌬️ Matrix Gas 조건")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Matrix Gas", config.matrix_gas.gas_type)
        with col2:
            st.metric("총 압력", f"{config.matrix_gas.total_pressure_torr:.1f} torr")
        with col3:
            broadening_status = "ON" if config.matrix_gas.enable_pressure_broadening else "OFF"
            st.metric("압력 확산", broadening_status)
        with col4:
            line_shift_status = "ON" if config.matrix_gas.enable_line_shifting else "OFF"
            st.metric("선 이동", line_shift_status)

def plot_mixed_spectrum(results: Dict[str, Any], wl_grid: List[float], config: SimulationConfig):
    """혼합 스펙트럼 플롯"""
    st.subheader("📊 혼합 스펙트럼 결과")
    
    # Line Shape 정보 표시 (OA-ICOS 모드인 경우)
    if config.spectrometer_mode == "🔬 분광기" and config.oa_icos:
        line_shape_used = config.oa_icos.line_shape
        st.info(f"🌊 **적용된 Line Shape**: {line_shape_used}")
    
    # OA-ICOS 모드인 경우 2단 그래프, 기본 모드인 경우 1단 그래프
    is_oa_icos = config.spectrometer_mode == "🔬 분광기"
    rows = 2 if is_oa_icos else 1
    
    subplot_titles = ['개별 분자 스펙트럼']
    if is_oa_icos:
        subplot_titles.append('기본 HITRAN vs OA-ICOS 비교')
    
    fig = make_subplots(rows=rows, cols=1, 
                       subplot_titles=subplot_titles,
                       vertical_spacing=0.15)
    
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    
    # 개별 분자 스펙트럼
    for i, (mol, spec) in enumerate(results.items()):
        if mol in ['combined', 'combined_oa_icos'] or mol.endswith('_oa_icos'):
            continue
        fig.add_trace(
            go.Scatter(x=wl_grid, y=spec['absorbance'],
                      name=get_molecule_label(mol),
                      line=dict(color=colors[i % len(colors)])),
            row=1, col=1
        )
    
    # OA-ICOS 비교 (모드가 선택된 경우)
    if is_oa_icos and 'combined_oa_icos' in results:
        line_shape_used = config.oa_icos.line_shape if config.oa_icos else "Voigt"
        # 기본 vs OA-ICOS 혼합 스펙트럼 비교
        fig.add_trace(
            go.Scatter(x=wl_grid, y=results['combined']['absorbance'],
                      name='기본 HITRAN (혼합)', 
                      line=dict(color='darkblue', width=3, dash='solid')),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=wl_grid, y=results['combined_oa_icos']['absorbance'],
                      name=f'OA-ICOS 향상 (혼합, {line_shape_used})', 
                      line=dict(color='darkred', width=3, dash='solid')),
            row=2, col=1
        )
    
    # 축 레이블 설정
    fig.update_xaxes(title_text="파장 (nm)", row=rows, col=1)
    fig.update_yaxes(title_text="흡광도", row=1, col=1)
    if is_oa_icos:
        fig.update_yaxes(title_text="흡광도 (혼합 스펙트럼)", row=2, col=1)
    
    # 레이아웃 설정
    fig.update_layout(
        height=600 if is_oa_icos else 400, 
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

def plot_concentration_analysis(results: Dict[str, Any], wl_grid: List[float], config: SimulationConfig):
    """농도별 분석 플롯"""
    st.subheader(f"📈 {get_molecule_label(config.molecule) if config.molecule else '분자'} 농도별 분석 결과")
    
    # Line Shape 정보 표시 (OA-ICOS 모드인 경우)
    is_oa_icos = config.spectrometer_mode == "🔬 분광기"
    if is_oa_icos and config.oa_icos:
        line_shape_used = config.oa_icos.line_shape
        st.info(f"🌊 **적용된 Line Shape**: {line_shape_used}")
    
    if is_oa_icos:
        # OA-ICOS 모드: 2x2 레이아웃
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("기본 HITRAN")
            _plot_concentration_spectra(results, wl_grid, is_oa_icos=False)
            _plot_linearity_analysis(results, is_oa_icos=False)
        
        with col2:
            st.subheader(f"OA-ICOS 향상 ({line_shape_used})")
            _plot_concentration_spectra(results, wl_grid, is_oa_icos=True)
            _plot_linearity_analysis(results, is_oa_icos=True)
    
    else:
        # 기본 모드: 기존과 동일한 2열 레이아웃
        col1, col2 = st.columns(2)
        
        with col1:
            _plot_concentration_spectra(results, wl_grid, is_oa_icos=False)
        
        with col2:
            _plot_linearity_analysis(results, is_oa_icos=False)
    
    # 분석 결과 비교 (Line Shape 효과 포함)
    st.subheader("📊 선형성 분석 결과 + Line Shape 효과")
    
    if is_oa_icos and 'oa_icos_analysis' in results:
        _show_comparison_metrics(results, config)
    else:
        # 기본 모드 결과
        if 'analysis' in results:
            _show_basic_metrics(results)

def _plot_concentration_spectra(results: Dict[str, Any], wl_grid: List[float], is_oa_icos: bool):
    """농도별 스펙트럼 플롯"""
    fig = go.Figure()
    colors = ['darkblue', 'blue', 'lightblue', 'green', 'yellow', 'orange', 'red', 'darkred']
    
    if is_oa_icos:
        # OA-ICOS 결과만 필터링
        plot_results = {k: v for k, v in results.items() if k.endswith('_oa_icos')}
        title = "농도별 스펙트럼 (OA-ICOS)"
    else:
        # 기본 결과만 필터링
        plot_results = {k: v for k, v in results.items() 
                       if not k.endswith('_oa_icos') and k not in ['analysis', 'oa_icos_analysis']}
        title = "농도별 스펙트럼 (기본)"
    
    for i, (c, spec) in enumerate(plot_results.items()):
        color_idx = int(i * (len(colors)-1) / (len(plot_results)-1)) if len(plot_results) > 1 else 0
        concentration = c.replace("_oa_icos", "") if is_oa_icos else str(c)
        fig.add_trace(
            go.Scatter(x=wl_grid, y=spec['absorbance'],
                      name=f'{concentration} ppb',
                      line=dict(color=colors[color_idx]))
        )
    
    fig.update_layout(title=title, xaxis_title="파장 (nm)", 
                      yaxis_title="흡광도", height=400)
    st.plotly_chart(fig, use_container_width=True)

def _plot_linearity_analysis(results: Dict[str, Any], is_oa_icos: bool):
    """선형성 분석 플롯"""
    analysis_key = 'oa_icos_analysis' if is_oa_icos else 'analysis'
    
    if analysis_key in results:
        fig = go.Figure()
        analysis = results[analysis_key]
        color = 'red' if is_oa_icos else 'blue'
        
        fig.add_trace(
            go.Scatter(x=analysis['concentrations'], y=analysis['max_absorbances'],
                      mode='markers', name='데이터', 
                      marker=dict(size=10, color=color))
        )
        
        x_fit = np.linspace(analysis['concentrations'][0], analysis['concentrations'][-1], 100)
        y_fit = analysis['slope'] * x_fit + analysis['intercept']
        fig.add_trace(
            go.Scatter(x=x_fit, y=y_fit, mode='lines',
                      name=f"R² = {analysis['r_squared']:.5f}",
                      line=dict(color=color, dash='dash'))
        )
        
        title = f"선형성 ({'OA-ICOS' if is_oa_icos else '기본'})"
        fig.update_layout(title=title, xaxis_title="농도 (ppb)",
                          yaxis_title="최대 흡광도", height=400)
        st.plotly_chart(fig, use_container_width=True)

def _show_comparison_metrics(results: Dict[str, Any], config: SimulationConfig):
    """비교 지표 표시"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🌟 기본 HITRAN**")
        analysis = results['analysis']
        subcol1, subcol2, subcol3, subcol4 = st.columns(4)
        with subcol1:
            st.metric("R²", f"{analysis['r_squared']:.6f}")
        with subcol2:
            st.metric("기울기", f"{analysis['slope']:.2e}")
        with subcol3:
            st.metric("절편", f"{analysis['intercept']:.2e}")
        with subcol4:
            detection_limit = 3 * 0.001 / analysis['slope'] if analysis['slope'] > 0 else 0
            st.metric("검출한계 (3σ)", f"{detection_limit:.1f} ppb")
    
    with col2:
        line_shape_used = config.oa_icos.line_shape if config.oa_icos else "Voigt"
        st.markdown(f"**🔬 OA-ICOS 향상 ({line_shape_used})**")
        oa_analysis = results['oa_icos_analysis']
        subcol1, subcol2, subcol3, subcol4 = st.columns(4)
        with subcol1:
            st.metric("R²", f"{oa_analysis['r_squared']:.6f}")
        with subcol2:
            st.metric("기울기", f"{oa_analysis['slope']:.2e}")
        with subcol3:
            st.metric("절편", f"{oa_analysis['intercept']:.2e}")
        with subcol4:
            oa_detection_limit = 3 * 0.001 / oa_analysis['slope'] if oa_analysis['slope'] > 0 else 0
            st.metric("검출한계 (3σ)", f"{oa_detection_limit:.1f} ppb")
    
    # 향상 효과 요약
    if analysis['slope'] > 0 and oa_analysis['slope'] > 0:
        sensitivity_improvement = oa_analysis['slope'] / analysis['slope']
        detection_limit = 3 * 0.001 / analysis['slope']
        oa_detection_limit = 3 * 0.001 / oa_analysis['slope']
        detection_improvement = detection_limit / oa_detection_limit if oa_detection_limit > 0 else float('inf')
        
        st.markdown("---")
        st.subheader(f"🚀 OA-ICOS + {line_shape_used} 향상 효과")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("감도 향상", f"{sensitivity_improvement:.1f}배")
        with col2:
            st.metric("검출한계 개선", f"{detection_improvement:.1f}배")
        with col3:
            if config.oa_icos:
                enhancement_factor = 1 / (1 - config.oa_icos.mirror_reflectivity)
                st.metric("이론적 향상", f"{enhancement_factor:.0f}배")
            else:
                st.metric("이론적 향상", "N/A")
        with col4:
            st.metric("Line Shape", line_shape_used)

def _show_basic_metrics(results: Dict[str, Any]):
    """기본 지표 표시"""
    analysis = results['analysis']
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

def show_line_shape_comparison():
    """Line Shape 모델 비교 시뮬레이션"""
    st.markdown("---")
    with st.expander("🌊 Line Shape 모델 비교 시뮬레이션"):
        st.markdown("**다양한 Line Shape 모델의 효과를 비교해보세요**")
        
        # 간단한 Line Shape 비교 데모
        demo_x = np.linspace(-2, 2, 1000)
        demo_x0 = 0
        demo_gamma_L = 0.3
        demo_gamma_G = 0.4
        
        from core.line_shape_calculator import LineShapeCalculator
        line_calc = LineShapeCalculator()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Line Shape 파라미터**")
            demo_gamma_L = st.slider("압력 확산 (γₗ)", 0.1, 1.0, 0.3, 0.1)
            demo_gamma_G = st.slider("도플러 확산 (γᵍ)", 0.1, 1.0, 0.4, 0.1)
        
        with col2:
            # Line Shape 비교 그래프
            fig_demo = go.Figure()
            
            shapes = {
                "Voigt": "red",
                "Gaussian": "blue", 
                "Lorentzian": "green",
                "Hartmann-Tran": "orange"
            }
            
            for shape_name, color in shapes.items():
                y_demo = line_calc.calculate_line_shape(demo_x, demo_x0, demo_gamma_L, demo_gamma_G, shape_name)
                fig_demo.add_trace(
                    go.Scatter(x=demo_x, y=y_demo, name=shape_name, line=dict(color=color, width=2))
                )
            
            fig_demo.update_layout(
                title="Line Shape 모델 비교",
                xaxis_title="주파수 오프셋",
                yaxis_title="정규화된 강도",
                height=300
            )
            st.plotly_chart(fig_demo, use_container_width=True, key="line_shape_demo")
        
        st.markdown("""
        **각 모델의 특징:**
        - **Voigt**: 가장 일반적, 도플러+압력 확산 조합
        - **Gaussian**: 저압 조건, 도플러 확산 지배적
        - **Lorentzian**: 고압 조건, 압력 확산 지배적  
        - **Hartmann-Tran**: 최고 정확도, 모든 물리적 효과 포함
        """) 