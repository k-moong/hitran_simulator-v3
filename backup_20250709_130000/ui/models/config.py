"""
설정 데이터 모델들
"""
from dataclasses import dataclass
from typing import Optional, Dict, List, Any

@dataclass
class MatrixGasConfig:
    """Matrix Gas 설정"""
    gas_type: str
    total_pressure_torr: float
    broadening_factor: float
    broadening_enhancement: float
    enable_pressure_broadening: bool
    enable_line_shifting: bool
    line_shift_coeff: float
    molar_mass: float
    humidity: str
    composition: str

@dataclass
class OAICOSConfig:
    """OA-ICOS 분광기 설정"""
    mirror_reflectivity: float
    cavity_length: float
    mirror_loss: float
    detector_noise: float
    baseline_drift: float
    line_shape: str

@dataclass
class SimulationConfig:
    """시뮬레이션 설정"""
    spectrometer_mode: str
    mode: str
    temperature: float
    wavelength_min: float
    wavelength_max: float
    path_length: float
    num_points: int
    matrix_gas: MatrixGasConfig
    oa_icos: Optional[OAICOSConfig] = None
    molecules: Optional[List[str]] = None
    molecule: Optional[str] = None
    concentration_min: Optional[float] = None
    concentration_max: Optional[float] = None
    concentration_steps: Optional[int] = None
    molecule_concentrations: Optional[Dict[str, float]] = None

@dataclass
class SimulationResult:
    """시뮬레이션 결과"""
    results: Dict[str, Any]
    wavelength_grid: List[float]
    config: SimulationConfig 