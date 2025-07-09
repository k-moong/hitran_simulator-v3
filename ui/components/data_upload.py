"""
실험 데이터 업로드 및 오버레이 기능
"""
import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Any
import io

def upload_experimental_data() -> Optional[pd.DataFrame]:
    """실험 데이터 업로드"""
    st.subheader("📁 실험 데이터 업로드")
    
    uploaded_file = st.file_uploader(
        "실험 데이터 파일 선택 (CSV, TXT)",
        type=['csv', 'txt'],
        help="파장(nm)과 흡광도/투과도 데이터가 포함된 파일을 업로드하세요"
    )
    
    if uploaded_file is not None:
        try:
            # 파일 확장자에 따른 읽기
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file, sep='\t')
            
            # 데이터 미리보기
            st.write("**데이터 미리보기:**")
            st.dataframe(df.head(), use_container_width=True)
            
            # 컬럼 선택
            st.write("**데이터 컬럼 매핑:**")
            col1, col2 = st.columns(2)
            
            with col1:
                wavelength_col = st.selectbox(
                    "파장 컬럼 선택",
                    df.columns.tolist(),
                    index=0 if 'wavelength' in df.columns else 0
                )
            
            with col2:
                intensity_col = st.selectbox(
                    "흡광도/투과도 컬럼 선택",
                    df.columns.tolist(),
                    index=1 if len(df.columns) > 1 else 0
                )
            
            # 데이터 타입 선택
            data_type = st.radio(
                "데이터 타입",
                ["흡광도 (Absorbance)", "투과도 (Transmittance)", "투과율 (%)"],
                horizontal=True
            )
            
            # 데이터 전처리
            processed_df = preprocess_experimental_data(df, wavelength_col, intensity_col, data_type)
            
            if processed_df is not None:
                st.success(f"✅ 실험 데이터 로드 완료: {len(processed_df)}개 포인트")
                return processed_df
            
        except Exception as e:
            st.error(f"❌ 파일 읽기 오류: {str(e)}")
            return None
    
    return None

def preprocess_experimental_data(df: pd.DataFrame, wavelength_col: str, intensity_col: str, data_type: str) -> Optional[pd.DataFrame]:
    """실험 데이터 전처리"""
    try:
        # 필요한 컬럼만 선택
        processed_df = df[[wavelength_col, intensity_col]].copy()
        processed_df.columns = ['wavelength', 'intensity']
        
        # NaN 값 제거
        processed_df = processed_df.dropna()
        
        # 파장 순으로 정렬
        processed_df = processed_df.sort_values('wavelength')
        
        # 데이터 타입에 따른 변환
        if data_type == "투과도 (Transmittance)":
            # 투과도를 흡광도로 변환 (A = -log10(T))
            processed_df['absorbance'] = -np.log10(processed_df['intensity'])
        elif data_type == "투과율 (%)":
            # 투과율을 투과도로 변환 후 흡광도로 변환
            processed_df['absorbance'] = -np.log10(processed_df['intensity'] / 100)
        else:
            # 이미 흡광도인 경우
            processed_df['absorbance'] = processed_df['intensity']
        
        # 파장 범위 필터링 (100nm ~ 1,000,000nm)
        processed_df = processed_df[
            (processed_df['wavelength'] >= 100) & 
            (processed_df['wavelength'] <= 1000000)
        ]
        
        return processed_df[['wavelength', 'absorbance']]
        
    except Exception as e:
        st.error(f"❌ 데이터 전처리 오류: {str(e)}")
        return None

def overlay_experimental_data(simulation_results: Dict[str, Any], experimental_data: pd.DataFrame, 
                            wl_grid: list, config) -> None:
    """실험 데이터와 시뮬레이션 결과 오버레이"""
    if experimental_data is None or len(experimental_data) == 0:
        return
    
    st.subheader("🔍 실험 vs 시뮬레이션 비교")
    
    # 오버레이 옵션
    col1, col2 = st.columns(2)
    with col1:
        show_experimental = st.checkbox("실험 데이터 표시", value=True)
    with col2:
        normalize_data = st.checkbox("데이터 정규화", value=False, 
                                   help="최대값을 1로 정규화하여 비교")
    
    # 파장 범위 필터링
    wl_min, wl_max = config.wavelength_min, config.wavelength_max
    exp_filtered = experimental_data[
        (experimental_data['wavelength'] >= wl_min) & 
        (experimental_data['wavelength'] <= wl_max)
    ]
    
    if len(exp_filtered) == 0:
        st.warning("⚠️ 선택된 파장 범위에 실험 데이터가 없습니다.")
        return
    
    # 시뮬레이션 결과 선택
    sim_key = None
    if config.mode == "🧪 혼합 스펙트럼":
        if 'combined' in simulation_results:
            sim_key = 'combined'
        elif 'combined_oa_icos' in simulation_results:
            sim_key = 'combined_oa_icos'
    else:
        # 농도별 분석에서 첫 번째 농도 선택
        for key in simulation_results.keys():
            if not key.endswith('_oa_icos') and key not in ['analysis', 'oa_icos_analysis']:
                sim_key = key
                break
    
    if sim_key is None:
        st.warning("⚠️ 비교할 시뮬레이션 결과가 없습니다.")
        return
    
    # 데이터 정규화
    sim_absorbance = np.array(simulation_results[sim_key]['absorbance'])
    exp_absorbance = np.array(exp_filtered['absorbance'])
    
    if normalize_data:
        sim_max = np.max(sim_absorbance) if np.max(sim_absorbance) > 0 else 1
        exp_max = np.max(exp_absorbance) if np.max(exp_absorbance) > 0 else 1
        sim_absorbance = sim_absorbance / sim_max
        exp_absorbance = exp_absorbance / exp_max
    
    # 오버레이 플롯
    import plotly.graph_objects as go
    
    fig = go.Figure()
    
    # 시뮬레이션 데이터
    fig.add_trace(
        go.Scatter(
            x=wl_grid,
            y=sim_absorbance,
            name=f'시뮬레이션 ({sim_key})',
            line=dict(color='blue', width=2),
            mode='lines'
        )
    )
    
    # 실험 데이터
    if show_experimental:
        fig.add_trace(
            go.Scatter(
                x=exp_filtered['wavelength'],
                y=exp_absorbance,
                name='실험 데이터',
                line=dict(color='red', width=2),
                mode='lines+markers',
                marker=dict(size=4)
            )
        )
    
    fig.update_layout(
        title="실험 vs 시뮬레이션 비교",
        xaxis_title="파장 (nm)",
        yaxis_title="흡광도" + (" (정규화)" if normalize_data else ""),
        height=500,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 통계 정보
    if show_experimental and len(exp_filtered) > 0:
        st.subheader("📊 비교 통계")
        
        # 상관계수 계산 (인터폴레이션 필요)
        from scipy.interpolate import interp1d
        
        try:
            # 실험 데이터를 시뮬레이션 파장 그리드에 인터폴레이션
            f_interp = interp1d(exp_filtered['wavelength'], exp_absorbance, 
                               bounds_error=False, fill_value=np.nan)
            exp_interpolated = f_interp(wl_grid)
            
            # NaN 제거
            valid_mask = ~np.isnan(exp_interpolated)
            if np.sum(valid_mask) > 10:  # 최소 10개 포인트
                sim_valid = sim_absorbance[valid_mask]
                exp_valid = exp_interpolated[valid_mask]
                
                # 상관계수
                correlation = np.corrcoef(sim_valid, exp_valid)[0, 1]
                
                # RMS 오차
                rms_error = np.sqrt(np.mean((sim_valid - exp_valid) ** 2))
                
                # 평균 절대 오차
                mae = np.mean(np.abs(sim_valid - exp_valid))
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("상관계수", f"{correlation:.4f}")
                with col2:
                    st.metric("RMS 오차", f"{rms_error:.4f}")
                with col3:
                    st.metric("평균 절대 오차", f"{mae:.4f}")
        
        except Exception as e:
            st.warning(f"⚠️ 통계 계산 오류: {str(e)}")

def export_results(simulation_results: Dict[str, Any], wl_grid: list, config) -> None:
    """결과 내보내기 기능"""
    st.subheader("💾 결과 내보내기")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 CSV 데이터 다운로드"):
            export_to_csv(simulation_results, wl_grid, config)
    
    with col2:
        if st.button("📈 PNG 그래프 다운로드"):
            export_to_png(simulation_results, wl_grid, config)
    
    with col3:
        if st.button("📄 PDF 리포트 다운로드"):
            export_to_pdf(simulation_results, wl_grid, config)

def export_to_csv(simulation_results: Dict[str, Any], wl_grid: list, config) -> None:
    """CSV 데이터 내보내기"""
    import pandas as pd
    
    # 모든 결과를 하나의 DataFrame으로 통합
    data_dict = {'wavelength_nm': wl_grid}
    
    for key, result in simulation_results.items():
        if isinstance(result, dict) and 'absorbance' in result:
            data_dict[f'{key}_absorbance'] = result['absorbance']
    
    df = pd.DataFrame(data_dict)
    
    # CSV 다운로드
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 CSV 파일 다운로드",
        data=csv,
        file_name=f"hitran_simulation_{config.mode.replace(' ', '_')}_{config.wavelength_min}_{config.wavelength_max}nm.csv",
        mime="text/csv"
    )

def export_to_png(simulation_results: Dict[str, Any], wl_grid: list, config) -> None:
    """PNG 그래프 내보내기"""
    import plotly.graph_objects as go
    import plotly.io as pio
    
    # 현재 시각화를 PNG로 변환
    fig = go.Figure()
    
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    
    for i, (key, result) in enumerate(simulation_results.items()):
        if isinstance(result, dict) and 'absorbance' in result:
            fig.add_trace(
                go.Scatter(
                    x=wl_grid,
                    y=result['absorbance'],
                    name=key,
                    line=dict(color=colors[i % len(colors)])
                )
            )
    
    fig.update_layout(
        title=f"HITRAN Simulation - {config.mode}",
        xaxis_title="파장 (nm)",
        yaxis_title="흡광도",
        height=600
    )
    
    # PNG 다운로드
    img_bytes = pio.to_image(fig, format="png")
    st.download_button(
        label="📥 PNG 파일 다운로드",
        data=img_bytes,
        file_name=f"hitran_simulation_{config.mode.replace(' ', '_')}_{config.wavelength_min}_{config.wavelength_max}nm.png",
        mime="image/png"
    )

def export_to_pdf(simulation_results: Dict[str, Any], wl_grid: list, config) -> None:
    """PDF 리포트 내보내기"""
    st.info("📄 PDF 리포트 기능은 향후 업데이트 예정입니다.")
    st.write("현재는 CSV와 PNG 다운로드를 이용해주세요.") 