"""
온도/압력 스윕 기능
"""
import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

def show_parameter_sweep_panel() -> Dict:
    """파라미터 스윕 설정 패널"""
    st.subheader("🌡️ 온도/압력 스윕 분석")
    
    # 스윕 타입 선택
    sweep_type = st.radio(
        "스윕 타입",
        ["🌡️ 온도 스윕", "🌬️ 압력 스윕", "🌡️🌬️ 온도+압력 스윕"],
        horizontal=True
    )
    
    sweep_config = {}
    
    if sweep_type == "🌡️ 온도 스윕":
        sweep_config = setup_temperature_sweep()
    elif sweep_type == "🌬️ 압력 스윕":
        sweep_config = setup_pressure_sweep()
    elif sweep_type == "🌡️🌬️ 온도+압력 스윕":
        sweep_config = setup_temperature_pressure_sweep()
    
    return sweep_config

def setup_temperature_sweep() -> Dict:
    """온도 스윕 설정"""
    st.write("**온도 스윕 설정:**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        temp_min = st.number_input("최소 온도 (K)", value=200.0, min_value=100.0, max_value=500.0)
    with col2:
        temp_max = st.number_input("최대 온도 (K)", value=400.0, min_value=100.0, max_value=500.0)
    with col3:
        temp_steps = st.slider("온도 단계 수", 5, 20, 10)
    
    # 고정 압력 설정
    st.write("**고정 압력 설정:**")
    pressure = st.number_input("압력 (torr)", value=760.0, min_value=1.0, max_value=15000.0)
    
    return {
        'type': 'temperature',
        'temp_min': temp_min,
        'temp_max': temp_max,
        'temp_steps': temp_steps,
        'pressure': pressure,
        'temperatures': np.linspace(temp_min, temp_max, temp_steps)
    }

def setup_pressure_sweep() -> Dict:
    """압력 스윕 설정"""
    st.write("**압력 스윕 설정:**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pressure_min = st.number_input("최소 압력 (torr)", value=100.0, min_value=1.0, max_value=1000.0)
    with col2:
        pressure_max = st.number_input("최대 압력 (torr)", value=1500.0, min_value=1.0, max_value=15000.0)
    with col3:
        pressure_steps = st.slider("압력 단계 수", 5, 20, 10)
    
    # 고정 온도 설정
    st.write("**고정 온도 설정:**")
    temperature = st.number_input("온도 (K)", value=296.15, min_value=200.0, max_value=400.0)
    
    return {
        'type': 'pressure',
        'pressure_min': pressure_min,
        'pressure_max': pressure_max,
        'pressure_steps': pressure_steps,
        'temperature': temperature,
        'pressures': np.linspace(pressure_min, pressure_max, pressure_steps)
    }

def setup_temperature_pressure_sweep() -> Dict:
    """온도+압력 스윕 설정"""
    st.write("**온도+압력 스윕 설정:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**온도 범위:**")
        temp_min = st.number_input("최소 온도 (K)", value=250.0, min_value=100.0, max_value=500.0, key="temp_min_2d")
        temp_max = st.number_input("최대 온도 (K)", value=350.0, min_value=100.0, max_value=500.0, key="temp_max_2d")
        temp_steps = st.slider("온도 단계 수", 5, 15, 8, key="temp_steps_2d")
    
    with col2:
        st.write("**압력 범위:**")
        pressure_min = st.number_input("최소 압력 (torr)", value=200.0, min_value=1.0, max_value=1000.0, key="pressure_min_2d")
        pressure_max = st.number_input("최대 압력 (torr)", value=1200.0, min_value=1.0, max_value=15000.0, key="pressure_max_2d")
        pressure_steps = st.slider("압력 단계 수", 5, 15, 8, key="pressure_steps_2d")
    
    return {
        'type': 'temperature_pressure',
        'temp_min': temp_min,
        'temp_max': temp_max,
        'temp_steps': temp_steps,
        'pressure_min': pressure_min,
        'pressure_max': pressure_max,
        'pressure_steps': pressure_steps,
        'temperatures': np.linspace(temp_min, temp_max, temp_steps),
        'pressures': np.linspace(pressure_min, pressure_max, pressure_steps)
    }

def run_parameter_sweep(sweep_config: Dict, molecule: str, wl_min: float, wl_max: float, 
                       path: float, num_points: int, api, calc) -> Dict:
    """파라미터 스윕 실행"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = {}
    
    if sweep_config['type'] == 'temperature':
        results = run_temperature_sweep(sweep_config, molecule, wl_min, wl_max, path, num_points, api, calc, progress_bar, status_text)
    elif sweep_config['type'] == 'pressure':
        results = run_pressure_sweep(sweep_config, molecule, wl_min, wl_max, path, num_points, api, calc, progress_bar, status_text)
    elif sweep_config['type'] == 'temperature_pressure':
        results = run_temperature_pressure_sweep(sweep_config, molecule, wl_min, wl_max, path, num_points, api, calc, progress_bar, status_text)
    
    progress_bar.empty()
    status_text.empty()
    
    return results

def run_temperature_sweep(sweep_config: Dict, molecule: str, wl_min: float, wl_max: float, 
                         path: float, num_points: int, api, calc, progress_bar, status_text) -> Dict:
    """온도 스윕 실행"""
    
    temperatures = sweep_config['temperatures']
    pressure = sweep_config['pressure'] / 760.0  # torr to atm
    
    # HITRAN 데이터 다운로드 (한 번만)
    data = api.download_molecule_data(molecule, wl_min, wl_max)
    if data is None or (hasattr(data, 'empty') and data.empty):
        st.error(f"❌ {molecule}: 해당 파장 범위에 데이터가 없습니다.")
        return {}
    
    freq_min = 1e7 / wl_max
    freq_max = 1e7 / wl_min
    freq_grid = np.linspace(freq_min, freq_max, num_points)
    wl_grid = 1e7 / freq_grid
    
    results = {
        'temperatures': temperatures,
        'wavelength_grid': wl_grid,
        'spectra': {},
        'max_absorbances': [],
        'peak_positions': []
    }
    
    total_steps = len(temperatures)
    
    for i, temp in enumerate(temperatures):
        status_text.text(f"온도 {temp:.1f}K 계산 중... ({i+1}/{total_steps})")
        
        # 농도는 기본값 사용 (1000 ppb)
        concentration = 1000e-9
        
        spec = calc.calculate_absorption_spectrum(
            data, freq_grid, temp, pressure, concentration, path, molecule
        )
        
        spec['wavelength'] = wl_grid
        results['spectra'][f"{temp:.1f}K"] = spec
        
        # 최대 흡광도와 피크 위치 기록
        max_abs = np.max(spec['absorbance'])
        results['max_absorbances'].append(max_abs)
        
        # 피크 위치 찾기
        peak_idx = np.argmax(spec['absorbance'])
        peak_wl = wl_grid[peak_idx]
        results['peak_positions'].append(peak_wl)
        
        progress_bar.progress((i + 1) / total_steps)
    
    return results

def run_pressure_sweep(sweep_config: Dict, molecule: str, wl_min: float, wl_max: float, 
                      path: float, num_points: int, api, calc, progress_bar, status_text) -> Dict:
    """압력 스윕 실행"""
    
    pressures = sweep_config['pressures']
    temperature = sweep_config['temperature']
    
    # HITRAN 데이터 다운로드 (한 번만)
    data = api.download_molecule_data(molecule, wl_min, wl_max)
    if data is None or (hasattr(data, 'empty') and data.empty):
        st.error(f"❌ {molecule}: 해당 파장 범위에 데이터가 없습니다.")
        return {}
    
    freq_min = 1e7 / wl_max
    freq_max = 1e7 / wl_min
    freq_grid = np.linspace(freq_min, freq_max, num_points)
    wl_grid = 1e7 / freq_grid
    
    results = {
        'pressures': pressures,
        'wavelength_grid': wl_grid,
        'spectra': {},
        'max_absorbances': [],
        'peak_positions': []
    }
    
    total_steps = len(pressures)
    
    for i, pressure_torr in enumerate(pressures):
        status_text.text(f"압력 {pressure_torr:.1f} torr 계산 중... ({i+1}/{total_steps})")
        
        pressure_atm = pressure_torr / 760.0
        concentration = 1000e-9  # 1000 ppb
        
        spec = calc.calculate_absorption_spectrum(
            data, freq_grid, temperature, pressure_atm, concentration, path, molecule
        )
        
        spec['wavelength'] = wl_grid
        results['spectra'][f"{pressure_torr:.1f}torr"] = spec
        
        # 최대 흡광도와 피크 위치 기록
        max_abs = np.max(spec['absorbance'])
        results['max_absorbances'].append(max_abs)
        
        # 피크 위치 찾기
        peak_idx = np.argmax(spec['absorbance'])
        peak_wl = wl_grid[peak_idx]
        results['peak_positions'].append(peak_wl)
        
        progress_bar.progress((i + 1) / total_steps)
    
    return results

def run_temperature_pressure_sweep(sweep_config: Dict, molecule: str, wl_min: float, wl_max: float, 
                                 path: float, num_points: int, api, calc, progress_bar, status_text) -> Dict:
    """온도+압력 스윕 실행"""
    
    temperatures = sweep_config['temperatures']
    pressures = sweep_config['pressures']
    
    # HITRAN 데이터 다운로드 (한 번만)
    data = api.download_molecule_data(molecule, wl_min, wl_max)
    if data is None or (hasattr(data, 'empty') and data.empty):
        st.error(f"❌ {molecule}: 해당 파장 범위에 데이터가 없습니다.")
        return {}
    
    freq_min = 1e7 / wl_max
    freq_max = 1e7 / wl_min
    freq_grid = np.linspace(freq_min, freq_max, num_points)
    wl_grid = 1e7 / freq_grid
    
    results = {
        'temperatures': temperatures,
        'pressures': pressures,
        'wavelength_grid': wl_grid,
        'spectra': {},
        'max_absorbances_2d': np.zeros((len(temperatures), len(pressures)))
    }
    
    total_steps = len(temperatures) * len(pressures)
    step_count = 0
    
    for i, temp in enumerate(temperatures):
        for j, pressure_torr in enumerate(pressures):
            status_text.text(f"온도 {temp:.1f}K, 압력 {pressure_torr:.1f} torr 계산 중... ({step_count+1}/{total_steps})")
            
            pressure_atm = pressure_torr / 760.0
            concentration = 1000e-9  # 1000 ppb
            
            spec = calc.calculate_absorption_spectrum(
                data, freq_grid, temp, pressure_atm, concentration, path, molecule
            )
            
            spec['wavelength'] = wl_grid
            results['spectra'][f"{temp:.1f}K_{pressure_torr:.1f}torr"] = spec
            
            # 2D 배열에 최대 흡광도 저장
            max_abs = np.max(spec['absorbance'])
            results['max_absorbances_2d'][i, j] = max_abs
            
            step_count += 1
            progress_bar.progress(step_count / total_steps)
    
    return results

def visualize_sweep_results(sweep_results: Dict, sweep_config: Dict, molecule: str) -> None:
    """스윕 결과 시각화"""
    
    if not sweep_results:
        st.warning("스윕 결과가 없습니다.")
        return
    
    st.subheader("📊 스윕 분석 결과")
    
    if sweep_config['type'] == 'temperature':
        visualize_temperature_sweep(sweep_results, molecule)
    elif sweep_config['type'] == 'pressure':
        visualize_pressure_sweep(sweep_results, molecule)
    elif sweep_config['type'] == 'temperature_pressure':
        visualize_temperature_pressure_sweep(sweep_results, molecule)

def visualize_temperature_sweep(sweep_results: Dict, molecule: str) -> None:
    """온도 스윕 시각화"""
    
    temperatures = sweep_results['temperatures']
    wl_grid = sweep_results['wavelength_grid']
    
    # 1. 스펙트럼 오버레이
    fig1 = go.Figure()
    
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'cyan', 'magenta']
    
    for i, temp in enumerate(temperatures):
        if f"{temp:.1f}K" in sweep_results['spectra']:
            spec = sweep_results['spectra'][f"{temp:.1f}K"]
            color_idx = int(i * (len(colors)-1) / (len(temperatures)-1))
            fig1.add_trace(
                go.Scatter(
                    x=wl_grid,
                    y=spec['absorbance'],
                    name=f'{temp:.1f}K',
                    line=dict(color=colors[color_idx])
                )
            )
    
    fig1.update_layout(
        title=f"{molecule} 온도 스윕 스펙트럼",
        xaxis_title="파장 (nm)",
        yaxis_title="흡광도",
        height=500
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # 2. 온도 의존성 분석
    col1, col2 = st.columns(2)
    
    with col1:
        # 최대 흡광도 vs 온도
        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=temperatures,
                y=sweep_results['max_absorbances'],
                mode='lines+markers',
                name='최대 흡광도'
            )
        )
        fig2.update_layout(
            title="최대 흡광도 vs 온도",
            xaxis_title="온도 (K)",
            yaxis_title="최대 흡광도",
            height=400
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with col2:
        # 피크 위치 vs 온도
        fig3 = go.Figure()
        fig3.add_trace(
            go.Scatter(
                x=temperatures,
                y=sweep_results['peak_positions'],
                mode='lines+markers',
                name='피크 위치'
            )
        )
        fig3.update_layout(
            title="피크 위치 vs 온도",
            xaxis_title="온도 (K)",
            yaxis_title="피크 파장 (nm)",
            height=400
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    # 3. 통계 분석
    st.subheader("📈 온도 의존성 분석")
    
    if len(temperatures) > 2:
        # 선형 회귀 분석
        slope, intercept, r_value, p_value, std_err = stats.linregress(temperatures, sweep_results['max_absorbances'])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("상관계수", f"{r_value:.4f}")
        with col2:
            st.metric("기울기", f"{slope:.2e}")
        with col3:
            st.metric("p-값", f"{p_value:.4f}")
        with col4:
            st.metric("온도 민감도", f"{slope:.2e} K⁻¹")

def visualize_pressure_sweep(sweep_results: Dict, molecule: str) -> None:
    """압력 스윕 시각화"""
    
    pressures = sweep_results['pressures']
    wl_grid = sweep_results['wavelength_grid']
    
    # 1. 스펙트럼 오버레이
    fig1 = go.Figure()
    
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'cyan', 'magenta']
    
    for i, pressure in enumerate(pressures):
        if f"{pressure:.1f}torr" in sweep_results['spectra']:
            spec = sweep_results['spectra'][f"{pressure:.1f}torr"]
            color_idx = int(i * (len(colors)-1) / (len(pressures)-1))
            fig1.add_trace(
                go.Scatter(
                    x=wl_grid,
                    y=spec['absorbance'],
                    name=f'{pressure:.1f} torr',
                    line=dict(color=colors[color_idx])
                )
            )
    
    fig1.update_layout(
        title=f"{molecule} 압력 스윕 스펙트럼",
        xaxis_title="파장 (nm)",
        yaxis_title="흡광도",
        height=500
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # 2. 압력 의존성 분석
    col1, col2 = st.columns(2)
    
    with col1:
        # 최대 흡광도 vs 압력
        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=pressures,
                y=sweep_results['max_absorbances'],
                mode='lines+markers',
                name='최대 흡광도'
            )
        )
        fig2.update_layout(
            title="최대 흡광도 vs 압력",
            xaxis_title="압력 (torr)",
            yaxis_title="최대 흡광도",
            height=400
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with col2:
        # 피크 위치 vs 압력
        fig3 = go.Figure()
        fig3.add_trace(
            go.Scatter(
                x=pressures,
                y=sweep_results['peak_positions'],
                mode='lines+markers',
                name='피크 위치'
            )
        )
        fig3.update_layout(
            title="피크 위치 vs 압력",
            xaxis_title="압력 (torr)",
            yaxis_title="피크 파장 (nm)",
            height=400
        )
        st.plotly_chart(fig3, use_container_width=True)

def visualize_temperature_pressure_sweep(sweep_results: Dict, molecule: str) -> None:
    """온도+압력 스윕 시각화"""
    
    temperatures = sweep_results['temperatures']
    pressures = sweep_results['pressures']
    max_abs_2d = sweep_results['max_absorbances_2d']
    
    # 2D 히트맵
    fig = go.Figure(data=go.Heatmap(
        z=max_abs_2d,
        x=pressures,
        y=temperatures,
        colorscale='Viridis',
        colorbar=dict(title="최대 흡광도")
    ))
    
    fig.update_layout(
        title=f"{molecule} 온도-압력 의존성 히트맵",
        xaxis_title="압력 (torr)",
        yaxis_title="온도 (K)",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 3D 서피스 플롯
    fig_3d = go.Figure(data=go.Surface(
        z=max_abs_2d,
        x=pressures,
        y=temperatures,
        colorscale='Viridis'
    ))
    
    fig_3d.update_layout(
        title=f"{molecule} 온도-압력 의존성 3D 서피스",
        scene=dict(
            xaxis_title="압력 (torr)",
            yaxis_title="온도 (K)",
            zaxis_title="최대 흡광도"
        ),
        height=600
    )
    
    st.plotly_chart(fig_3d, use_container_width=True)
    
    # 최적 조건 찾기
    optimal_idx = np.unravel_index(np.argmax(max_abs_2d), max_abs_2d.shape)
    optimal_temp = temperatures[optimal_idx[0]]
    optimal_pressure = pressures[optimal_idx[1]]
    optimal_absorbance = max_abs_2d[optimal_idx]
    
    st.subheader("🎯 최적 조건")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("최적 온도", f"{optimal_temp:.1f} K")
    with col2:
        st.metric("최적 압력", f"{optimal_pressure:.1f} torr")
    with col3:
        st.metric("최대 흡광도", f"{optimal_absorbance:.6f}") 