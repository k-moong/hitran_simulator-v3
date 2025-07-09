"""
시뮬레이션 엔진
"""
import streamlit as st
import numpy as np
from scipy import stats
from typing import Dict, Any, List, Tuple

from core.oa_icos_simulator import OAICOSSimulator
from data_handler.hitran_api import HitranAPI
from spectrum_calc.absorption import SpectrumCalculator
from ui.models.config import SimulationConfig, SimulationResult
from ui.utils.helpers import get_molecule_label

class SimulationEngine:
    """시뮬레이션 엔진 클래스"""
    
    def __init__(self):
        self.api = HitranAPI()
        self.calc = SpectrumCalculator()
        self.oa_icos_sim = None
    
    def run_simulation(self, config: SimulationConfig) -> SimulationResult:
        """시뮬레이션 실행"""
        # OA-ICOS 시뮬레이터 초기화
        if config.spectrometer_mode == "🔬 분광기":
            self.oa_icos_sim = OAICOSSimulator()
        
        results = {}
        freq_min = 1e7 / config.wavelength_max
        freq_max = 1e7 / config.wavelength_min
        freq_grid = np.linspace(freq_min, freq_max, config.num_points)
        wl_grid = 1e7 / freq_grid
        
        # Matrix Gas 압력 적용
        pressure_atm = config.matrix_gas.total_pressure_torr / 760.0
        
        if config.mode == "🧪 혼합 스펙트럼" and config.molecules is not None:
            results = self._run_mixed_spectrum_simulation(config, freq_grid, wl_grid, pressure_atm)
        elif config.mode == "📈 농도별 분석" and config.molecule is not None:
            results = self._run_concentration_analysis_simulation(config, freq_grid, wl_grid, pressure_atm)
        
        return SimulationResult(
            results=results,
            wavelength_grid=wl_grid.tolist(),
            config=config
        )
    
    def _run_mixed_spectrum_simulation(self, config: SimulationConfig, freq_grid: np.ndarray, 
                                     wl_grid: np.ndarray, pressure_atm: float) -> Dict[str, Any]:
        """혼합 스펙트럼 시뮬레이션"""
        # 성능 경고 메시지
        if config.molecules and len(config.molecules) > 5:
            st.warning(f"⚠️ **성능 주의**: {len(config.molecules)}개의 분자를 선택했습니다. 계산 시간이 오래 걸릴 수 있습니다.")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        combined_abs = np.zeros_like(freq_grid)
        results = {}
        
        if config.molecules:
            for mol in config.molecules:
                molecule_label = get_molecule_label(mol)
                data = self.api.download_molecule_data(mol, int(config.wavelength_min), int(config.wavelength_max))
            
            if data is None or (hasattr(data, 'empty') and data.empty) or (hasattr(data, '__len__') and len(data) == 0):
                st.warning(f"⚠️ {molecule_label} : 해당 파장 범위에 스펙트럼 데이터가 없습니다.")
                continue
            
            # 농도 처리
            if config.molecule_concentrations and mol in config.molecule_concentrations:
                concentration = config.molecule_concentrations[mol] / 1e9  # ppb to mole fraction
            else:
                concentration = 1000e-9  # 기본값 1000 ppb
            
            spec = self.calc.calculate_absorption_spectrum(
                data, freq_grid, config.temperature, pressure_atm, concentration, 
                config.path_length, mol,
                progress_bar=progress_bar, status_text=status_text, molecule_label=molecule_label
            )
            spec['wavelength'] = wl_grid
            results[mol] = spec
            combined_abs += spec['absorption_coeff']
            
            # OA-ICOS 시뮬레이션
            if self.oa_icos_sim and config.oa_icos:
                oa_icos_result = self._run_oa_icos_simulation(spec, config.oa_icos)
                results[f"{mol}_oa_icos"] = oa_icos_result
        
        progress_bar.empty()
        status_text.empty()
        
        # 기본 혼합 스펙트럼
        results['combined'] = {
            'transmittance': np.exp(-combined_abs * config.path_length),
            'absorbance': -np.log10(np.exp(-combined_abs * config.path_length))
        }
        
        # OA-ICOS 혼합 스펙트럼
        if self.oa_icos_sim and config.oa_icos:
            combined_spectrum = {
                'absorption_coeff': combined_abs,
                'wavelength': wl_grid
            }
            oa_icos_combined = self._run_oa_icos_simulation(combined_spectrum, config.oa_icos)
            results['combined_oa_icos'] = oa_icos_combined
        
        return results
    
    def _run_concentration_analysis_simulation(self, config: SimulationConfig, freq_grid: np.ndarray,
                                             wl_grid: np.ndarray, pressure_atm: float) -> Dict[str, Any]:
        """농도별 분석 시뮬레이션"""
        progress_bar = st.progress(0)
        status_text = st.empty()
        concs_array = np.linspace(config.concentration_min, config.concentration_max, config.concentration_steps)
        molecule_label = get_molecule_label(config.molecule)
        
        data = self.api.download_molecule_data(config.molecule, config.wavelength_min, config.wavelength_max)
        if data is None or (hasattr(data, 'empty') and data.empty) or (hasattr(data, '__len__') and len(data) == 0):
            st.warning(f"⚠️ {molecule_label} : 해당 파장 범위에 스펙트럼 데이터가 없습니다.")
            return {}
        
        max_abs = []
        oa_icos_max_abs = []
        results = {}
        
        for idx, c in enumerate(concs_array):
            spec = self.calc.calculate_absorption_spectrum(
                data, freq_grid, config.temperature, pressure_atm, c/1e9, 
                config.path_length, config.molecule,
                progress_bar=progress_bar, status_text=status_text, molecule_label=molecule_label
            )
            spec['wavelength'] = wl_grid
            results[c] = spec
            max_abs.append(np.max(spec['absorbance']))
            
            # OA-ICOS 시뮬레이션
            if self.oa_icos_sim and config.oa_icos:
                oa_icos_result = self._run_oa_icos_simulation(spec, config.oa_icos)
                results[f"{c}_oa_icos"] = oa_icos_result
                oa_icos_max_abs.append(np.max(oa_icos_result['oa_icos_signal']))
        
        progress_bar.empty()
        status_text.empty()
        
        # 선형성 분석
        if len(max_abs) > 1:
            linreg_result = stats.linregress(concs_array, max_abs)
            results['analysis'] = {
                'concentrations': concs_array.tolist(),
                'max_absorbances': max_abs,
                'r_squared': float(linreg_result.rvalue**2),
                'slope': float(linreg_result.slope),
                'intercept': float(linreg_result.intercept)
            }
        
        # OA-ICOS 선형성 분석
        if self.oa_icos_sim and config.oa_icos and len(oa_icos_max_abs) > 1:
            linreg_oa_result = stats.linregress(concs_array, oa_icos_max_abs)
            results['oa_icos_analysis'] = {
                'concentrations': concs_array.tolist(),
                'max_absorbances': oa_icos_max_abs,
                'r_squared': float(linreg_oa_result.rvalue**2),
                'slope': float(linreg_oa_result.slope),
                'intercept': float(linreg_oa_result.intercept)
            }
        
        return results
    
    def _run_oa_icos_simulation(self, spec: Dict[str, Any], oa_icos_config) -> Dict[str, Any]:
        """OA-ICOS 시뮬레이션 실행"""
        return self.oa_icos_sim.simulate_oa_icos_spectrum(
            spec['wavelength'], spec['absorption_coeff'],
            oa_icos_config.mirror_reflectivity, oa_icos_config.cavity_length,
            oa_icos_config.mirror_loss, oa_icos_config.detector_noise,
            oa_icos_config.baseline_drift, oa_icos_config.line_shape
        ) 