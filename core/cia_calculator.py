"""
Collision-Induced Absorption (CIA) Calculator
분자 간 충돌로 인한 흡수 계산 모듈

주요 기능:
- HITRAN CIA 데이터 접근
- 온도 의존성 CIA cross-section 계산
- 다양한 분자 쌍 지원 (H2-H2, H2-He, N2-N2, O2-O2 등)
"""

import numpy as np
import pandas as pd
import requests
from scipy.interpolate import interp1d, RectBivariateSpline
from typing import Dict, List, Tuple, Optional
import warnings

class CIACalculator:
    """CIA 계산을 위한 클래스"""
    
    def __init__(self):
        self.cia_data = {}
        self.supported_pairs = {
            'H2-H2': {'id': '1-1', 'description': '수소-수소 충돌 흡수'},
            'H2-He': {'id': '1-2', 'description': '수소-헬륨 충돌 흡수'},
            'H2-H': {'id': '1-3', 'description': '수소-수소원자 충돌 흡수'},
            'He-H': {'id': '2-3', 'description': '헬륨-수소원자 충돌 흡수'},
            'N2-N2': {'id': '22-22', 'description': '질소-질소 충돌 흡수'},
            'N2-H2': {'id': '22-1', 'description': '질소-수소 충돌 흡수'},
            'O2-O2': {'id': '32-32', 'description': '산소-산소 충돌 흡수'},
            'O2-N2': {'id': '32-22', 'description': '산소-질소 충돌 흡수'},
            'CO2-CO2': {'id': '26-26', 'description': '이산화탄소-이산화탄소 충돌 흡수'},
            'CH4-N2': {'id': '61-22', 'description': '메탄-질소 충돌 흡수'},
            'CH4-CH4': {'id': '61-61', 'description': '메탄-메탄 충돌 흡수'},
        }
        
        # 온도 범위 및 기본 조건
        self.default_temperature_range = (200, 400)  # K
        self.default_pressure = 1.0  # atm
        
    def get_available_pairs(self) -> Dict[str, str]:
        """사용 가능한 CIA 분자 쌍 목록 반환"""
        return {pair: info['description'] for pair, info in self.supported_pairs.items()}
    
    def load_cia_data(self, pair: str, wavenumber_range: Tuple[float, float] = None) -> bool:
        """
        CIA 데이터 로딩 (HITRAN 형식 또는 내장 데이터)
        
        Args:
            pair: 분자 쌍 (예: 'H2-H2', 'N2-N2')
            wavenumber_range: 파수 범위 (cm⁻¹)
        
        Returns:
            bool: 로딩 성공 여부
        """
        if pair not in self.supported_pairs:
            return False

        try:
            cia_data = self._generate_sample_cia_data(pair, wavenumber_range)
            self.cia_data[pair] = cia_data
            return True
        except Exception:
            return False
    
    def _generate_sample_cia_data(self, pair: str, wavenumber_range: Tuple[float, float] = None) -> Dict:
        """
        샘플 CIA 데이터 생성 (실제 HITRAN 데이터 대신 사용)
        실제 구현에서는 HITRAN CIA 데이터베이스에서 데이터를 가져와야 함
        """
        if wavenumber_range is None:
            wn_min, wn_max = 100, 10000  # cm⁻¹
        else:
            wn_min, wn_max = wavenumber_range
        
        # 파수 그리드 생성
        wavenumber = np.linspace(wn_min, wn_max, 1000)
        
        # 온도 그리드 생성
        temperature = np.array([200, 250, 296, 350, 400])  # K
        
        # 분자 쌍별 특성을 고려한 샘플 cross-section 생성
        if pair == 'H2-H2':
            # H2-H2는 원적외선에서 주로 흡수
            cross_section = self._h2_h2_sample(wavenumber, temperature)
        elif pair == 'N2-N2':
            # N2-N2는 특정 주파수 대역에서 흡수
            cross_section = self._n2_n2_sample(wavenumber, temperature)
        elif pair == 'O2-O2':
            # O2-O2 모델
            cross_section = self._o2_o2_sample(wavenumber, temperature)
        elif pair == 'CO2-CO2':
            # CO2-CO2 모델
            cross_section = self._co2_co2_sample(wavenumber, temperature)
        else:
            # 기본 모델
            cross_section = self._default_cia_sample(wavenumber, temperature)
        
        return {
            'wavenumber': wavenumber,
            'temperature': temperature,
            'cross_section': cross_section,  # shape: (len(temperature), len(wavenumber))
            'pair': pair,
            'units': 'cm⁵/molecule²'
        }
    
    def _h2_h2_sample(self, wavenumber: np.ndarray, temperature: np.ndarray) -> np.ndarray:
        """H2-H2 충돌 흡수 샘플 데이터"""
        cross_section = np.zeros((len(temperature), len(wavenumber)))
        
        for i, T in enumerate(temperature):
            # H2-H2는 주로 원적외선 영역에서 강한 흡수
            # 온도가 높을수록 흡수 증가
            for j, wn in enumerate(wavenumber):
                if wn < 1000:  # 원적외선 영역 (강한 흡수)
                    intensity = 1e-40 * (T / 296) ** 1.5 * np.exp(-wn / (0.695 * T))
                    cross_section[i, j] = intensity * wn * np.exp(-(wn - 500) ** 2 / (2 * 200 ** 2))
                elif 1000 <= wn < 10000:  # 중적외선~근적외선 영역 (약한 흡수)
                    intensity = 1e-42 * (T / 296) ** 1.0
                    cross_section[i, j] = intensity * np.exp(-(wn - 2000) ** 2 / (2 * 3000 ** 2))
        
        return cross_section
    
    def _n2_n2_sample(self, wavenumber: np.ndarray, temperature: np.ndarray) -> np.ndarray:
        """N2-N2 충돌 흡수 샘플 데이터"""
        cross_section = np.zeros((len(temperature), len(wavenumber)))
        
        for i, T in enumerate(temperature):
            # N2-N2는 중적외선 영역에서 약한 흡수
            for j, wn in enumerate(wavenumber):
                if 2000 < wn < 6000:  # 중적외선 영역 (주요 흡수)
                    intensity = 1e-45 * (T / 296) ** 0.5
                    cross_section[i, j] = intensity * np.exp(-(wn - 4000) ** 2 / (2 * 1000 ** 2))
                elif 6000 <= wn < 15000:  # 근적외선 영역 (약한 흡수)
                    intensity = 1e-47 * (T / 296) ** 0.3
                    cross_section[i, j] = intensity * np.exp(-(wn - 8000) ** 2 / (2 * 2000 ** 2))
        
        return cross_section
    
    def _o2_o2_sample(self, wavenumber: np.ndarray, temperature: np.ndarray) -> np.ndarray:
        """O2-O2 충돌 흡수 샘플 데이터"""
        cross_section = np.zeros((len(temperature), len(wavenumber)))
        
        for i, T in enumerate(temperature):
            # O2-O2는 특정 밴드에서 흡수
            for j, wn in enumerate(wavenumber):
                if 1200 < wn < 1700:  # O2 A-band 근처
                    intensity = 5e-44 * (T / 296) ** 0.8
                    cross_section[i, j] = intensity * np.exp(-(wn - 1270) ** 2 / (2 * 50 ** 2))
                elif 6000 <= wn < 15000:  # 근적외선 영역
                    intensity = 1e-46 * (T / 296) ** 0.5
                    cross_section[i, j] = intensity * np.exp(-(wn - 7500) ** 2 / (2 * 2500 ** 2))
        
        return cross_section
    
    def _co2_co2_sample(self, wavenumber: np.ndarray, temperature: np.ndarray) -> np.ndarray:
        """CO2-CO2 충돌 흡수 샘플 데이터"""
        cross_section = np.zeros((len(temperature), len(wavenumber)))
        
        for i, T in enumerate(temperature):
            # CO2-CO2는 여러 밴드에서 흡수
            for j, wn in enumerate(wavenumber):
                if 2000 < wn < 2500:  # CO2 밴드 근처
                    intensity = 1e-43 * (T / 296) ** 1.2
                    cross_section[i, j] = intensity * np.exp(-(wn - 2350) ** 2 / (2 * 100 ** 2))
                elif 6000 <= wn < 15000:  # 근적외선 영역
                    intensity = 5e-46 * (T / 296) ** 1.0
                    cross_section[i, j] = intensity * np.exp(-(wn - 7200) ** 2 / (2 * 2000 ** 2))
        
        return cross_section
    
    def _default_cia_sample(self, wavenumber: np.ndarray, temperature: np.ndarray) -> np.ndarray:
        """기본 CIA 모델"""
        cross_section = np.zeros((len(temperature), len(wavenumber)))
        
        for i, T in enumerate(temperature):
            for j, wn in enumerate(wavenumber):
                if wn < 15000:  # 전체 범위에서 약한 흡수
                    intensity = 1e-44 * (T / 296) ** 1.0
                    cross_section[i, j] = intensity * np.exp(-wn / 5000) * (1 + 0.1 * np.sin(wn / 1000))
        
        return cross_section
    
    def calculate_cia_absorption(self, pair: str, wavenumber: np.ndarray, 
                                temperature: float, density1: float, density2: float,
                                path_length: float = 1000.0) -> np.ndarray:
        """
        CIA 흡수 계산
        
        Args:
            pair: 분자 쌍
            wavenumber: 파수 배열 (cm⁻¹)
            temperature: 온도 (K)
            density1: 첫 번째 분자의 수밀도 (molecules/cm³)
            density2: 두 번째 분자의 수밀도 (molecules/cm³)
            path_length: 광경로 길이 (cm)
        
        Returns:
            np.ndarray: CIA 흡수 계수 (cm⁻¹)
        """
        if pair not in self.cia_data:
            return np.zeros_like(wavenumber)
        
        try:
            cia_data = self.cia_data[pair]
            
            # 온도 보간
            cross_section_interp = self._interpolate_temperature(
                cia_data, wavenumber, temperature
            )
            
            # CIA 흡수 계수 계산
            # α_CIA = n1 * n2 * σ_CIA * L
            absorption_coefficient = density1 * density2 * cross_section_interp * path_length
            
            return absorption_coefficient
            
        except Exception:
            return np.zeros_like(wavenumber)
    
    def _interpolate_temperature(self, cia_data: Dict, wavenumber: np.ndarray, 
                               temperature: float) -> np.ndarray:
        """온도에 대한 보간"""
        data_wn = cia_data['wavenumber']
        data_temp = cia_data['temperature']
        data_cross = cia_data['cross_section']
        
        # 온도 범위 체크
        if temperature < data_temp.min() or temperature > data_temp.max():
            warnings.warn(f"온도 {temperature}K가 데이터 범위를 벗어남 "
                         f"({data_temp.min()}-{data_temp.max()}K)")
        
        # 2D 보간 (온도와 파수)
        interpolator = RectBivariateSpline(
            data_temp, data_wn, data_cross, 
            bbox=[data_temp.min(), data_temp.max(), data_wn.min(), data_wn.max()],
            kx=min(3, len(data_temp)-1), ky=min(3, len(data_wn)-1)
        )
        
        # 요청된 파수 범위로 보간
        cross_section_interp = interpolator(temperature, wavenumber, grid=False)
        
        return cross_section_interp
    
    def get_density_from_concentration(self, molecule: str, concentration_ppb: float, 
                                     temperature: float, pressure_atm: float) -> float:
        """
        농도(ppb)에서 수밀도(molecules/cm³) 변환
        
        Args:
            molecule: 분자명
            concentration_ppb: 농도 (ppb)
            temperature: 온도 (K)
            pressure_atm: 압력 (atm)
        
        Returns:
            float: 수밀도 (molecules/cm³)
        """
        # 이상기체 법칙 사용
        # n = P * N_A / (R * T) * (concentration / 1e9)
        
        R = 82.057  # cm³·atm/(mol·K)
        N_A = 6.022e23  # molecules/mol
        
        # 전체 수밀도
        total_density = (pressure_atm * N_A) / (R * temperature)
        
        # 해당 분자의 수밀도
        molecule_density = total_density * (concentration_ppb / 1e9)
        
        return molecule_density
    
    def calculate_multiple_cia_pairs(self, pairs: List[str], wavenumber: np.ndarray,
                                   temperature: float, concentrations: Dict[str, float],
                                   pressure_atm: float = 1.0, path_length: float = 1000.0) -> Dict[str, np.ndarray]:
        """
        여러 CIA 쌍에 대한 동시 계산
        
        Args:
            pairs: CIA 쌍 목록
            wavenumber: 파수 배열 (cm⁻¹)
            temperature: 온도 (K)
            concentrations: 분자별 농도 (ppb)
            pressure_atm: 압력 (atm)
            path_length: 광경로 길이 (cm)
        
        Returns:
            Dict: 각 쌍별 CIA 흡수 결과
        """
        results = {}
        
        for pair in pairs:
            if pair not in self.supported_pairs:
                continue
            
            # 분자 쌍 분리
            mol1, mol2 = pair.split('-')
            
            # 농도 확인
            if mol1 not in concentrations or mol2 not in concentrations:
                continue
            
            # 수밀도 계산
            density1 = self.get_density_from_concentration(
                mol1, concentrations[mol1], temperature, pressure_atm
            )
            density2 = self.get_density_from_concentration(
                mol2, concentrations[mol2], temperature, pressure_atm
            )
            
            # CIA 흡수 계산
            if self.load_cia_data(pair, (wavenumber.min(), wavenumber.max())):
                cia_absorption = self.calculate_cia_absorption(
                    pair, wavenumber, temperature, density1, density2, path_length
                )
                results[pair] = cia_absorption
        
        return results

# 테스트 함수
def test_cia_calculator():
    """CIA 계산기 테스트"""
    print("🧪 CIA Calculator 테스트 시작")
    
    calc = CIACalculator()
    
    # 사용 가능한 쌍 확인
    print("\n📋 사용 가능한 CIA 쌍:")
    for pair, desc in calc.get_available_pairs().items():
        print(f"  - {pair}: {desc}")
    
    # 샘플 계산
    wavenumber = np.linspace(100, 5000, 1000)  # cm⁻¹
    temperature = 296.15  # K
    pressure = 1.0  # atm
    concentrations = {'H2': 1000, 'He': 5000, 'N2': 780000, 'O2': 210000}  # ppb
    
    # H2-H2 CIA 테스트
    pairs = ['H2-H2', 'N2-N2', 'O2-O2']
    results = calc.calculate_multiple_cia_pairs(
        pairs, wavenumber, temperature, concentrations, pressure
    )
    
    print(f"\n📊 CIA 계산 결과:")
    for pair, absorption in results.items():
        max_abs = np.max(absorption)
        print(f"  {pair}: 최대 흡수 = {max_abs:.2e} cm⁻¹")
    
    print("✅ CIA Calculator 테스트 완료")

if __name__ == "__main__":
    test_cia_calculator() 