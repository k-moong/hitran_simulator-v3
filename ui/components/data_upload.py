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
    
    # CSV 데이터 준비
    csv_data = prepare_csv_data(simulation_results, wl_grid)
    
    # PNG 이미지 준비  
    png_data = prepare_png_data(simulation_results, wl_grid, config)
    
    # PDF 리포트 준비
    pdf_data = prepare_pdf_data(simulation_results, wl_grid, config)
    
    with col1:
        if csv_data:
            st.download_button(
                label="📊 CSV 데이터 다운로드",
                data=csv_data,
                file_name=f"hitran_simulation_{config.mode.replace(' ', '_')}_{config.wavelength_min}_{config.wavelength_max}nm.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.error("❌ CSV 데이터 생성 실패")
    
    with col2:
        if png_data:
            st.download_button(
                label="📈 PNG 그래프 다운로드",
                data=png_data,
                file_name=f"hitran_simulation_{config.mode.replace(' ', '_')}_{config.wavelength_min}_{config.wavelength_max}nm.png",
                mime="image/png",
                use_container_width=True
            )
        else:
            st.error("❌ PNG 이미지 생성 실패")
    
    with col3:
        if pdf_data:
            st.download_button(
                label="📄 PDF 리포트 다운로드", 
                data=pdf_data,
                file_name=f"hitran_report_{config.mode.replace(' ', '_')}_{config.wavelength_min}_{config.wavelength_max}nm.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error("❌ PDF 리포트 생성 실패")

def prepare_csv_data(simulation_results: Dict[str, Any], wl_grid: list):
    """CSV 데이터 준비"""
    import pandas as pd
    
    try:
        # 모든 결과를 하나의 DataFrame으로 통합
        data_dict = {'wavelength_nm': wl_grid}
        
        # 데이터 추가
        for key, result in simulation_results.items():
            if isinstance(result, dict) and 'absorbance' in result:
                data_dict[f'{key}_absorbance'] = result['absorbance']
            elif isinstance(result, dict) and 'transmittance' in result:
                data_dict[f'{key}_transmittance'] = result['transmittance']
        
        if len(data_dict) == 1:  # wavelength_nm만 있는 경우
            return None
        
        df = pd.DataFrame(data_dict)
        return df.to_csv(index=False)
        
    except Exception as e:
        return None

def prepare_png_data(simulation_results: Dict[str, Any], wl_grid: list, config):
    """PNG 이미지 데이터 준비"""
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import numpy as np
    import os
    import io
    
    try:
        # 한글 폰트 설정 (Windows 기본 폰트 사용)
        try:
            font_path = 'C:/Windows/Fonts/malgun.ttf'  # 맑은 고딕
            if not os.path.exists(font_path):
                font_path = 'C:/Windows/Fonts/gulim.ttc'  # 굴림
            if os.path.exists(font_path):
                fm.fontManager.addfont(font_path)
                plt.rcParams['font.family'] = ['Malgun Gothic', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False  # 마이너스 부호 깨짐 방지
        except:
            # 폰트 설정 실패시 영문 사용
            plt.rcParams['font.family'] = ['DejaVu Sans']
        
        # matplotlib 사용으로 안정적인 PNG 생성
        plt.figure(figsize=(12, 8))
        
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        for i, (key, result) in enumerate(simulation_results.items()):
            if isinstance(result, dict) and 'absorbance' in result:
                # numpy 배열로 안전하게 변환
                wl_array = np.array(wl_grid)
                abs_array = np.array(result['absorbance'])
                
                plt.plot(wl_array, abs_array, 
                        color=colors[i % len(colors)], 
                        label=key, 
                        linewidth=2)
        
        # 제목에서 한글 문제 방지를 위해 영문 사용
        plt.title("HITRAN Simulation Spectrum", fontsize=16, fontweight='bold')
        plt.xlabel("Wavelength (nm)", fontsize=14)
        plt.ylabel("Absorbance", fontsize=14)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # PNG로 저장
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_bytes = img_buffer.getvalue()
        plt.close()  # 메모리 누수 방지
        
        return img_bytes
        
    except Exception as e:
        return None

def prepare_pdf_data(simulation_results: Dict[str, Any], wl_grid: list, config):
    """PDF 리포트 데이터 준비"""
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.font_manager as fm
    import io
    import pandas as pd
    import numpy as np
    import os
    from datetime import datetime
    
    try:
        # 한글 폰트 설정 (Windows 기본 폰트 사용)
        try:
            font_path = 'C:/Windows/Fonts/malgun.ttf'  # 맑은 고딕
            if not os.path.exists(font_path):
                font_path = 'C:/Windows/Fonts/gulim.ttc'  # 굴림
            if os.path.exists(font_path):
                fm.fontManager.addfont(font_path)
                plt.rcParams['font.family'] = ['Malgun Gothic', 'DejaVu Sans']
        except:
            # 폰트 설정 실패시 기본 폰트 사용 (한글은 영문으로 표시)
            plt.rcParams['font.family'] = ['DejaVu Sans']
        
        # PDF 생성
        pdf_buffer = io.BytesIO()
        
        with PdfPages(pdf_buffer) as pdf:
            # 첫 번째 페이지: 요약 정보
            fig, ax = plt.subplots(figsize=(8.5, 11))
            ax.axis('off')
            
            # 제목
            ax.text(0.5, 0.95, 'HITRAN CRDS Simulation Report', 
                   fontsize=20, fontweight='bold', ha='center', transform=ax.transAxes)
            
            # 생성 일시
            ax.text(0.5, 0.9, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                   fontsize=12, ha='center', transform=ax.transAxes)
            
            # 시뮬레이션 조건
            y_pos = 0.8
            ax.text(0.1, y_pos, 'Simulation Parameters:', fontsize=16, fontweight='bold', transform=ax.transAxes)
            y_pos -= 0.05
            ax.text(0.1, y_pos, f'Mode: {config.mode}', fontsize=12, transform=ax.transAxes)
            y_pos -= 0.04
            ax.text(0.1, y_pos, f'Wavelength Range: {config.wavelength_min} - {config.wavelength_max} nm', 
                   fontsize=12, transform=ax.transAxes)
            y_pos -= 0.04
            
            # 결과 요약
            y_pos -= 0.05
            ax.text(0.1, y_pos, 'Results Summary:', fontsize=16, fontweight='bold', transform=ax.transAxes)
            y_pos -= 0.05
            
            molecule_count = 0
            for key, result in simulation_results.items():
                if isinstance(result, dict) and 'absorbance' in result:
                    molecule_count += 1
                    # numpy 배열 안전하게 처리
                    abs_data = np.array(result['absorbance'])
                    if len(abs_data) > 0:
                        max_abs = np.max(abs_data)
                    else:
                        max_abs = 0.0
                    ax.text(0.1, y_pos, f'{key}: Max Absorbance = {max_abs:.6f}', 
                           fontsize=12, transform=ax.transAxes)
                    y_pos -= 0.04
            
            if molecule_count == 0:
                ax.text(0.1, y_pos, 'No valid simulation data found', fontsize=12, transform=ax.transAxes)
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
            
            # 두 번째 페이지: 스펙트럼 그래프
            if molecule_count > 0:
                fig, ax = plt.subplots(figsize=(10, 6))
                
                colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
                
                for i, (key, result) in enumerate(simulation_results.items()):
                    if isinstance(result, dict) and 'absorbance' in result:
                        # numpy 배열로 안전하게 변환
                        wl_array = np.array(wl_grid)
                        abs_array = np.array(result['absorbance'])
                        
                        ax.plot(wl_array, abs_array, 
                               color=colors[i % len(colors)], 
                               label=key, 
                               linewidth=2)
                
                ax.set_title("HITRAN Simulation Spectrum", fontsize=14, fontweight='bold')
                ax.set_xlabel("Wavelength (nm)", fontsize=12)
                ax.set_ylabel("Absorbance", fontsize=12)
                ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                ax.grid(True, alpha=0.3)
                
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
        
        return pdf_buffer.getvalue()
        
    except Exception as e:
        return None

def export_to_csv(simulation_results: Dict[str, Any], wl_grid: list, config) -> None:
    """CSV 데이터 내보내기"""
    import pandas as pd
    
    try:
        # 모든 결과를 하나의 DataFrame으로 통합
        data_dict = {'wavelength_nm': wl_grid}
        
        # 데이터 추가
        for key, result in simulation_results.items():
            if isinstance(result, dict) and 'absorbance' in result:
                data_dict[f'{key}_absorbance'] = result['absorbance']
            elif isinstance(result, dict) and 'transmittance' in result:
                data_dict[f'{key}_transmittance'] = result['transmittance']
        
        if len(data_dict) == 1:  # wavelength_nm만 있는 경우
            st.error("❌ 내보낼 시뮬레이션 데이터가 없습니다.")
            return
        
        df = pd.DataFrame(data_dict)
        
        # CSV 다운로드
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 CSV 파일 다운로드",
            data=csv,
            file_name=f"hitran_simulation_{config.mode.replace(' ', '_')}_{config.wavelength_min}_{config.wavelength_max}nm.csv",
            mime="text/csv"
        )
        st.success("✅ CSV 파일 준비 완료!")
        
    except Exception as e:
        st.error(f"❌ CSV 생성 중 오류가 발생했습니다: {str(e)}")
        st.info("시뮬레이션을 다시 실행해 주세요.")

def export_to_png(simulation_results: Dict[str, Any], wl_grid: list, config) -> None:
    """PNG 그래프 내보내기"""
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import numpy as np
    import os
    import io
    
    try:
        # 한글 폰트 설정 (Windows 기본 폰트 사용)
        try:
            font_path = 'C:/Windows/Fonts/malgun.ttf'  # 맑은 고딕
            if not os.path.exists(font_path):
                font_path = 'C:/Windows/Fonts/gulim.ttc'  # 굴림
            if os.path.exists(font_path):
                fm.fontManager.addfont(font_path)
                plt.rcParams['font.family'] = ['Malgun Gothic', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False  # 마이너스 부호 깨짐 방지
        except:
            # 폰트 설정 실패시 영문 사용
            plt.rcParams['font.family'] = ['DejaVu Sans']
        
        # matplotlib 사용으로 안정적인 PNG 생성
        plt.figure(figsize=(12, 8))
        
        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        for i, (key, result) in enumerate(simulation_results.items()):
            if isinstance(result, dict) and 'absorbance' in result:
                # numpy 배열로 안전하게 변환
                wl_array = np.array(wl_grid)
                abs_array = np.array(result['absorbance'])
                
                plt.plot(wl_array, abs_array, 
                        color=colors[i % len(colors)], 
                        label=key, 
                        linewidth=2)
        
        # 제목에서 한글 문제 방지를 위해 영문 사용
        plt.title("HITRAN Simulation Spectrum", fontsize=16, fontweight='bold')
        plt.xlabel("Wavelength (nm)", fontsize=14)
        plt.ylabel("Absorbance", fontsize=14)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # PNG로 저장
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_bytes = img_buffer.getvalue()
        plt.close()  # 메모리 누수 방지
        
        st.download_button(
            label="📥 PNG File Download",
            data=img_bytes,
            file_name=f"hitran_simulation_{config.mode.replace(' ', '_')}_{config.wavelength_min}_{config.wavelength_max}nm.png",
            mime="image/png"
        )
        st.success("✅ PNG File Ready!")
        
    except Exception as e:
        st.error(f"❌ PNG generation error: {str(e)}")
        st.info("📊 Please use CSV download instead.")
        
        # 디버그 정보 추가
        with st.expander("🔍 Debug Information"):
            st.write(f"Error details: {type(e).__name__}: {str(e)}")
            st.write(f"Simulation results keys: {list(simulation_results.keys())}")
            st.write(f"Wavelength grid length: {len(wl_grid) if wl_grid else 0}")

def export_to_pdf(simulation_results: Dict[str, Any], wl_grid: list, config) -> None:
    """PDF 리포트 내보내기"""
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.font_manager as fm
    import io
    import pandas as pd
    import numpy as np
    import os
    from datetime import datetime
    
    try:
        # 한글 폰트 설정 (Windows 기본 폰트 사용)
        try:
            font_path = 'C:/Windows/Fonts/malgun.ttf'  # 맑은 고딕
            if not os.path.exists(font_path):
                font_path = 'C:/Windows/Fonts/gulim.ttc'  # 굴림
            if os.path.exists(font_path):
                fm.fontManager.addfont(font_path)
                plt.rcParams['font.family'] = ['Malgun Gothic', 'DejaVu Sans']
        except:
            # 폰트 설정 실패시 기본 폰트 사용 (한글은 영문으로 표시)
            plt.rcParams['font.family'] = ['DejaVu Sans']
        
        # PDF 생성
        pdf_buffer = io.BytesIO()
        
        with PdfPages(pdf_buffer) as pdf:
            # 첫 번째 페이지: 요약 정보
            fig, ax = plt.subplots(figsize=(8.5, 11))
            ax.axis('off')
            
            # 제목
            ax.text(0.5, 0.95, 'HITRAN CRDS Simulation Report', 
                   fontsize=20, fontweight='bold', ha='center', transform=ax.transAxes)
            
            # 생성 일시
            ax.text(0.5, 0.9, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                   fontsize=12, ha='center', transform=ax.transAxes)
            
            # 시뮬레이션 조건
            y_pos = 0.8
            ax.text(0.1, y_pos, 'Simulation Parameters:', fontsize=16, fontweight='bold', transform=ax.transAxes)
            y_pos -= 0.05
            ax.text(0.1, y_pos, f'Mode: {config.mode}', fontsize=12, transform=ax.transAxes)
            y_pos -= 0.04
            ax.text(0.1, y_pos, f'Wavelength Range: {config.wavelength_min} - {config.wavelength_max} nm', 
                   fontsize=12, transform=ax.transAxes)
            y_pos -= 0.04
            
            # 결과 요약
            y_pos -= 0.05
            ax.text(0.1, y_pos, 'Results Summary:', fontsize=16, fontweight='bold', transform=ax.transAxes)
            y_pos -= 0.05
            
            molecule_count = 0
            for key, result in simulation_results.items():
                if isinstance(result, dict) and 'absorbance' in result:
                    molecule_count += 1
                    # numpy 배열 안전하게 처리
                    abs_data = np.array(result['absorbance'])
                    if len(abs_data) > 0:
                        max_abs = np.max(abs_data)
                    else:
                        max_abs = 0.0
                    ax.text(0.1, y_pos, f'{key}: Max Absorbance = {max_abs:.6f}', 
                           fontsize=12, transform=ax.transAxes)
                    y_pos -= 0.04
            
            if molecule_count == 0:
                ax.text(0.1, y_pos, 'No valid simulation data found', fontsize=12, transform=ax.transAxes)
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
            
            # 두 번째 페이지: 스펙트럼 그래프
            if molecule_count > 0:
                fig, ax = plt.subplots(figsize=(10, 6))
                
                colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
                
                for i, (key, result) in enumerate(simulation_results.items()):
                    if isinstance(result, dict) and 'absorbance' in result:
                        # numpy 배열로 안전하게 변환
                        wl_array = np.array(wl_grid)
                        abs_array = np.array(result['absorbance'])
                        
                        ax.plot(wl_array, abs_array, 
                               color=colors[i % len(colors)], 
                               label=key, 
                               linewidth=2)
                
                ax.set_title("HITRAN Simulation Spectrum", fontsize=14, fontweight='bold')
                ax.set_xlabel("Wavelength (nm)", fontsize=12)
                ax.set_ylabel("Absorbance", fontsize=12)
                ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                ax.grid(True, alpha=0.3)
                
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
        
        pdf_bytes = pdf_buffer.getvalue()
        
        st.download_button(
            label="📥 PDF Report Download",
            data=pdf_bytes,
            file_name=f"hitran_report_{config.mode.replace(' ', '_')}_{config.wavelength_min}_{config.wavelength_max}nm.pdf",
            mime="application/pdf"
        )
        st.success("✅ PDF Report Ready!")
        
    except Exception as e:
        st.error(f"❌ PDF generation error: {str(e)}")
        st.info("📊 Please use CSV or PNG download instead.")
        
        # 디버그 정보 추가
        with st.expander("🔍 Debug Information"):
            st.write(f"Error details: {type(e).__name__}: {str(e)}")
            st.write(f"Simulation results keys: {list(simulation_results.keys())}")
            st.write(f"Wavelength grid length: {len(wl_grid) if wl_grid else 0}") 