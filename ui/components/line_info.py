"""
스펙트럼 라인 정보 툴팁 기능
"""
import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_interactive_spectrum_with_tooltips(wl_grid: list, simulation_results: Dict, 
                                            line_data: Dict, molecule_info: Dict) -> go.Figure:
    """인터랙티브 스펙트럼과 라인 정보 툴팁 생성"""
    
    fig = go.Figure()
    
    # 기본 스펙트럼 플롯
    for key, result in simulation_results.items():
        if isinstance(result, dict) and 'absorbance' in result:
            fig.add_trace(
                go.Scatter(
                    x=wl_grid,
                    y=result['absorbance'],
                    name=key,
                    mode='lines',
                    hovertemplate=create_hover_template(key, result, line_data, molecule_info),
                    customdata=np.column_stack([
                        wl_grid,
                        result['absorbance'],
                        [key] * len(wl_grid)
                    ])
                )
            )
    
    # 라인 마커 추가 (피크 위치에)
    if line_data and len(line_data) > 0:
        add_line_markers(fig, line_data, molecule_info)
    
    fig.update_layout(
        title="인터랙티브 스펙트럼 (마우스 오버로 라인 정보 확인)",
        xaxis_title="파장 (nm)",
        yaxis_title="흡광도",
        height=600,
        hovermode='closest'
    )
    
    return fig

def create_hover_template(key: str, result: Dict, line_data: Dict, molecule_info: Dict) -> str:
    """호버 템플릿 생성"""
    template = f"""
    <b>{key}</b><br>
    파장: %{{x:.4f}} nm<br>
    흡광도: %{{y:.6f}}<br>
    주파수: %{{customdata[0]:.2f}} cm⁻¹<br>
    """
    
    # 라인 정보 추가
    if line_data:
        template += "<br><b>라인 정보:</b><br>"
        template += "%{customdata[1]}"
    
    return template

def add_line_markers(fig: go.Figure, line_data: Dict, molecule_info: Dict) -> None:
    """라인 마커 추가"""
    # 피크 위치 찾기
    for key, result in line_data.items():
        if isinstance(result, dict) and 'wavelength' in result and 'absorbance' in result:
            wl = result['wavelength']
            abs_data = result['absorbance']
            
            # 피크 찾기 (간단한 방법)
            peaks = find_peaks(wl, abs_data)
            
            for peak_idx in peaks:
                peak_wl = wl[peak_idx]
                peak_abs = abs_data[peak_idx]
                
                # 해당 파장의 라인 정보 찾기
                line_info = find_line_info_at_wavelength(peak_wl, molecule_info)
                
                fig.add_trace(
                    go.Scatter(
                        x=[peak_wl],
                        y=[peak_abs],
                        mode='markers',
                        marker=dict(
                            size=8,
                            color='red',
                            symbol='diamond'
                        ),
                        name=f'라인 피크 ({key})',
                        hovertemplate=f"""
                        <b>라인 피크</b><br>
                        파장: {peak_wl:.4f} nm<br>
                        흡광도: {peak_abs:.6f}<br>
                        {line_info}
                        """,
                        showlegend=False
                    )
                )

def find_peaks(wavelengths: list, absorbance: list, threshold: float = 0.1) -> List[int]:
    """피크 위치 찾기"""
    peaks = []
    for i in range(1, len(absorbance) - 1):
        if (absorbance[i] > absorbance[i-1] and 
            absorbance[i] > absorbance[i+1] and 
            absorbance[i] > threshold):
            peaks.append(i)
    return peaks

def find_line_info_at_wavelength(wavelength: float, molecule_info: Dict) -> str:
    """특정 파장의 라인 정보 찾기"""
    # 실제 구현에서는 HITRAN 라인 데이터에서 해당 파장의 정보를 찾아야 함
    # 여기서는 예시 정보 반환
    return f"분자: {molecule_info.get('name', 'Unknown')}<br>온도: {molecule_info.get('temperature', 'N/A')}K"

def show_line_details_panel(line_data: Dict, molecule_info: Dict) -> None:
    """라인 상세 정보 패널"""
    st.subheader("📋 라인 상세 정보")
    
    if not line_data:
        st.info("라인 데이터가 없습니다.")
        return
    
    # 라인 정보 테이블
    line_info_df = create_line_info_dataframe(line_data, molecule_info)
    
    if line_info_df is not None and len(line_info_df) > 0:
        st.dataframe(line_info_df, use_container_width=True)
        
        # 라인 통계
        show_line_statistics(line_info_df)
        
        # 라인 분포 히스토그램
        show_line_distribution(line_info_df)

def create_line_info_dataframe(line_data: Dict, molecule_info: Dict) -> Optional[pd.DataFrame]:
    """라인 정보 데이터프레임 생성"""
    try:
        lines = []
        
        for key, result in line_data.items():
            if isinstance(result, dict) and 'wavelength' in result:
                wl = result['wavelength']
                abs_data = result['absorbance']
                
                # 피크 찾기
                peaks = find_peaks(wl, abs_data)
                
                for peak_idx in peaks:
                    peak_wl = wl[peak_idx]
                    peak_abs = abs_data[peak_idx]
                    peak_freq = 1e7 / peak_wl  # cm⁻¹
                    
                    lines.append({
                        '분자': molecule_info.get('name', key),
                        '파장 (nm)': f"{peak_wl:.4f}",
                        '주파수 (cm⁻¹)': f"{peak_freq:.2f}",
                        '흡광도': f"{peak_abs:.6f}",
                        '강도': f"{peak_abs:.2e}",
                        '라인 ID': f"{key}_{peak_idx}"
                    })
        
        if lines:
            return pd.DataFrame(lines)
        else:
            return None
            
    except Exception as e:
        st.error(f"라인 정보 데이터프레임 생성 오류: {str(e)}")
        return None

def show_line_statistics(line_info_df: pd.DataFrame) -> None:
    """라인 통계 정보"""
    st.subheader("📊 라인 통계")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 라인 수", len(line_info_df))
    
    with col2:
        if '파장 (nm)' in line_info_df.columns:
            wavelengths = pd.to_numeric(line_info_df['파장 (nm)'])
            st.metric("평균 파장", f"{wavelengths.mean():.2f} nm")
    
    with col3:
        if '흡광도' in line_info_df.columns:
            absorbances = pd.to_numeric(line_info_df['흡광도'])
            st.metric("최대 흡광도", f"{absorbances.max():.6f}")
    
    with col4:
        if '주파수 (cm⁻¹)' in line_info_df.columns:
            frequencies = pd.to_numeric(line_info_df['주파수 (cm⁻¹)'])
            st.metric("주파수 범위", f"{frequencies.max() - frequencies.min():.1f} cm⁻¹")

def show_line_distribution(line_info_df: pd.DataFrame) -> None:
    """라인 분포 히스토그램"""
    st.subheader("📈 라인 분포")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if '파장 (nm)' in line_info_df.columns:
            wavelengths = pd.to_numeric(line_info_df['파장 (nm)'])
            
            fig_wl = go.Figure()
            fig_wl.add_trace(
                go.Histogram(
                    x=wavelengths,
                    nbinsx=20,
                    name="파장 분포"
                )
            )
            fig_wl.update_layout(
                title="파장 분포",
                xaxis_title="파장 (nm)",
                yaxis_title="라인 수",
                height=300
            )
            st.plotly_chart(fig_wl, use_container_width=True)
    
    with col2:
        if '주파수 (cm⁻¹)' in line_info_df.columns:
            frequencies = pd.to_numeric(line_info_df['주파수 (cm⁻¹)'])
            
            fig_freq = go.Figure()
            fig_freq.add_trace(
                go.Histogram(
                    x=frequencies,
                    nbinsx=20,
                    name="주파수 분포"
                )
            )
            fig_freq.update_layout(
                title="주파수 분포",
                xaxis_title="주파수 (cm⁻¹)",
                yaxis_title="라인 수",
                height=300
            )
            st.plotly_chart(fig_freq, use_container_width=True)

def create_advanced_line_analysis(simulation_results: Dict, wl_grid: list, 
                                line_data: Dict, molecule_info: Dict) -> None:
    """고급 라인 분석 기능"""
    st.subheader("🔬 고급 라인 분석")
    
    # 분석 옵션
    analysis_type = st.selectbox(
        "분석 유형",
        ["라인 피크 분석", "스펙트럼 피팅", "라인 강도 비교", "온도 의존성"]
    )
    
    if analysis_type == "라인 피크 분석":
        perform_peak_analysis(simulation_results, wl_grid)
    elif analysis_type == "스펙트럼 피팅":
        perform_spectrum_fitting(simulation_results, wl_grid)
    elif analysis_type == "라인 강도 비교":
        perform_intensity_comparison(simulation_results, wl_grid)
    elif analysis_type == "온도 의존성":
        perform_temperature_dependence(simulation_results, wl_grid)

def perform_peak_analysis(simulation_results: Dict, wl_grid: list) -> None:
    """피크 분석"""
    st.write("**피크 분석 결과:**")
    
    for key, result in simulation_results.items():
        if isinstance(result, dict) and 'absorbance' in result:
            abs_data = result['absorbance']
            peaks = find_peaks(wl_grid, abs_data)
            
            if peaks:
                st.write(f"**{key}**: {len(peaks)}개 피크 발견")
                
                # 피크 정보 테이블
                peak_info = []
                for i, peak_idx in enumerate(peaks[:10]):  # 상위 10개만
                    peak_info.append({
                        '피크 #': i+1,
                        '파장 (nm)': f"{wl_grid[peak_idx]:.4f}",
                        '흡광도': f"{abs_data[peak_idx]:.6f}",
                        '주파수 (cm⁻¹)': f"{1e7/wl_grid[peak_idx]:.2f}"
                    })
                
                if peak_info:
                    st.dataframe(pd.DataFrame(peak_info), use_container_width=True)

def perform_spectrum_fitting(simulation_results: Dict, wl_grid: list) -> None:
    """스펙트럼 피팅"""
    st.write("**스펙트럼 피팅 기능:**")
    st.info("이 기능은 향후 업데이트 예정입니다.")
    
    # 간단한 피팅 예시
    if 'combined' in simulation_results:
        abs_data = simulation_results['combined']['absorbance']
        
        # 가우시안 피팅 (간단한 예시)
        from scipy.optimize import curve_fit
        
        def gaussian(x, amplitude, center, sigma):
            return amplitude * np.exp(-(x - center)**2 / (2 * sigma**2))
        
        # 피팅 시도
        try:
            # 피크 찾기
            peaks = find_peaks(wl_grid, abs_data)
            if peaks:
                peak_idx = peaks[0]  # 첫 번째 피크
                peak_wl = wl_grid[peak_idx]
                peak_abs = abs_data[peak_idx]
                
                # 피팅 범위 설정
                fit_range = 10  # 포인트
                start_idx = max(0, peak_idx - fit_range)
                end_idx = min(len(wl_grid), peak_idx + fit_range)
                
                x_fit = wl_grid[start_idx:end_idx]
                y_fit = abs_data[start_idx:end_idx]
                
                # 초기 추정값
                p0 = [peak_abs, peak_wl, 0.1]
                
                # 피팅
                popt, pcov = curve_fit(gaussian, x_fit, y_fit, p0=p0)
                
                st.write(f"**피팅 결과 (첫 번째 피크):**")
                st.write(f"진폭: {popt[0]:.6f}")
                st.write(f"중심 파장: {popt[1]:.4f} nm")
                st.write(f"표준편차: {popt[2]:.4f} nm")
                
        except Exception as e:
            st.warning(f"피팅 오류: {str(e)}")

def perform_intensity_comparison(simulation_results: Dict, wl_grid: list) -> None:
    """라인 강도 비교"""
    st.write("**라인 강도 비교:**")
    
    # 여러 분자의 강도 비교
    intensity_data = {}
    
    for key, result in simulation_results.items():
        if isinstance(result, dict) and 'absorbance' in result:
            abs_data = result['absorbance']
            max_intensity = np.max(abs_data)
            intensity_data[key] = max_intensity
    
    if intensity_data:
        # 강도 비교 차트
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=list(intensity_data.keys()),
                y=list(intensity_data.values()),
                name="최대 강도"
            )
        )
        fig.update_layout(
            title="분자별 최대 흡광도 비교",
            xaxis_title="분자",
            yaxis_title="최대 흡광도",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

def perform_temperature_dependence(simulation_results: Dict, wl_grid: list) -> None:
    """온도 의존성 분석"""
    st.write("**온도 의존성 분석:**")
    st.info("이 기능은 향후 업데이트 예정입니다.")
    st.write("여러 온도에서의 스펙트럼 변화를 분석할 수 있습니다.") 