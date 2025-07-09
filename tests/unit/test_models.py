"""
데이터 모델 단위 테스트
"""
import pytest
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.models.config import MatrixGasConfig, OAICOSConfig, SimulationConfig, SimulationResult

class TestMatrixGasConfig:
    """Matrix Gas 설정 테스트 클래스"""
    
    def test_matrix_gas_config_creation(self):
        """Matrix Gas 설정 생성 테스트"""
        config = MatrixGasConfig(
            gas_type="CDA",
            total_pressure_torr=760.0,
            broadening_factor=0.96,
            broadening_enhancement=1.0,
            enable_pressure_broadening=True,
            enable_line_shifting=False,
            line_shift_coeff=0.0,
            molar_mass=28.97,
            humidity="< 1 ppm H2O",
            composition="N2 (78%) + O2 (21%) only"
        )
        
        assert config.gas_type == "CDA"
        assert config.total_pressure_torr == 760.0
        assert config.broadening_factor == 0.96
        assert config.enable_pressure_broadening is True
        assert config.enable_line_shifting is False
    
    def test_matrix_gas_config_defaults(self):
        """Matrix Gas 설정 기본값 테스트"""
        config = MatrixGasConfig(
            gas_type="Air",
            total_pressure_torr=760.0,
            broadening_factor=1.0,
            broadening_enhancement=1.0,
            enable_pressure_broadening=True,
            enable_line_shifting=False,
            line_shift_coeff=0.0,
            molar_mass=28.97,
            humidity="자연습도",
            composition="N2 + O2 + H2O + trace gases"
        )
        
        assert config.gas_type == "Air"
        assert config.total_pressure_torr == 760.0

class TestOAICOSConfig:
    """OA-ICOS 설정 테스트 클래스"""
    
    def test_oa_icos_config_creation(self):
        """OA-ICOS 설정 생성 테스트"""
        config = OAICOSConfig(
            mirror_reflectivity=0.99990,
            cavity_length=50.0,
            mirror_loss=0.00001,
            detector_noise=0.00075,
            baseline_drift=0.0001,
            line_shape="Voigt"
        )
        
        assert config.mirror_reflectivity == 0.99990
        assert config.cavity_length == 50.0
        assert config.line_shape == "Voigt"
    
    def test_oa_icos_config_validation(self):
        """OA-ICOS 설정 유효성 검증 테스트"""
        # 미러 반사율 범위 검증
        with pytest.raises(ValueError):
            OAICOSConfig(
                mirror_reflectivity=1.1,  # 범위 초과
                cavity_length=50.0,
                mirror_loss=0.00001,
                detector_noise=0.00075,
                baseline_drift=0.0001,
                line_shape="Voigt"
            )

class TestSimulationConfig:
    """시뮬레이션 설정 테스트 클래스"""
    
    def test_simulation_config_creation(self):
        """시뮬레이션 설정 생성 테스트"""
        matrix_gas = MatrixGasConfig(
            gas_type="CDA",
            total_pressure_torr=760.0,
            broadening_factor=0.96,
            broadening_enhancement=1.0,
            enable_pressure_broadening=True,
            enable_line_shifting=False,
            line_shift_coeff=0.0,
            molar_mass=28.97,
            humidity="< 1 ppm H2O",
            composition="N2 (78%) + O2 (21%) only"
        )
        
        oa_icos = OAICOSConfig(
            mirror_reflectivity=0.99990,
            cavity_length=50.0,
            mirror_loss=0.00001,
            detector_noise=0.00075,
            baseline_drift=0.0001,
            line_shape="Voigt"
        )
        
        config = SimulationConfig(
            spectrometer_mode="🔬 분광기",
            mode="🧪 혼합 스펙트럼",
            temperature=296.15,
            wavelength_min=1390.0,
            wavelength_max=1395.0,
            path_length=1000.0,
            num_points=10000,
            matrix_gas=matrix_gas,
            oa_icos=oa_icos,
            molecules=["H2O161", "CO2-626"],
            molecule=None,
            concentration_min=None,
            concentration_max=None,
            concentration_steps=None,
            molecule_concentrations={"H2O161": 1000.0, "CO2-626": 400.0}
        )
        
        assert config.spectrometer_mode == "🔬 분광기"
        assert config.mode == "🧪 혼합 스펙트럼"
        assert config.temperature == 296.15
        assert config.wavelength_min == 1390.0
        assert config.wavelength_max == 1395.0
        assert config.num_points == 10000
        assert config.molecules == ["H2O161", "CO2-626"]
        assert config.oa_icos is not None
        assert config.matrix_gas is not None
    
    def test_simulation_config_basic_mode(self):
        """기본 HITRAN 모드 설정 테스트"""
        matrix_gas = MatrixGasConfig(
            gas_type="Air",
            total_pressure_torr=760.0,
            broadening_factor=1.0,
            broadening_enhancement=1.0,
            enable_pressure_broadening=True,
            enable_line_shifting=False,
            line_shift_coeff=0.0,
            molar_mass=28.97,
            humidity="자연습도",
            composition="N2 + O2 + H2O + trace gases"
        )
        
        config = SimulationConfig(
            spectrometer_mode="🌟 기본 HITRAN",
            mode="📈 농도별 분석",
            temperature=296.15,
            wavelength_min=1390.0,
            wavelength_max=1395.0,
            path_length=1000.0,
            num_points=10000,
            matrix_gas=matrix_gas,
            oa_icos=None,
            molecules=None,
            molecule="H2O161",
            concentration_min=10.0,
            concentration_max=5000.0,
            concentration_steps=10,
            molecule_concentrations=None
        )
        
        assert config.spectrometer_mode == "🌟 기본 HITRAN"
        assert config.mode == "📈 농도별 분석"
        assert config.oa_icos is None
        assert config.molecule == "H2O161"
        assert config.concentration_min == 10.0
        assert config.concentration_max == 5000.0

class TestSimulationResult:
    """시뮬레이션 결과 테스트 클래스"""
    
    def test_simulation_result_creation(self):
        """시뮬레이션 결과 생성 테스트"""
        matrix_gas = MatrixGasConfig(
            gas_type="CDA",
            total_pressure_torr=760.0,
            broadening_factor=0.96,
            broadening_enhancement=1.0,
            enable_pressure_broadening=True,
            enable_line_shifting=False,
            line_shift_coeff=0.0,
            molar_mass=28.97,
            humidity="< 1 ppm H2O",
            composition="N2 (78%) + O2 (21%) only"
        )
        
        config = SimulationConfig(
            spectrometer_mode="🌟 기본 HITRAN",
            mode="🧪 혼합 스펙트럼",
            temperature=296.15,
            wavelength_min=1390.0,
            wavelength_max=1395.0,
            path_length=1000.0,
            num_points=10000,
            matrix_gas=matrix_gas,
            oa_icos=None,
            molecules=["H2O161"],
            molecule=None,
            concentration_min=None,
            concentration_max=None,
            concentration_steps=None,
            molecule_concentrations=None
        )
        
        results = {"H2O161": {"absorbance": [0.1, 0.2, 0.3]}}
        wavelength_grid = [1390.0, 1392.5, 1395.0]
        
        result = SimulationResult(
            results=results,
            wavelength_grid=wavelength_grid,
            config=config
        )
        
        assert result.config == config
        assert result.results == results
        assert result.wavelength_grid == wavelength_grid
        assert len(result.wavelength_grid) == 3

if __name__ == "__main__":
    pytest.main([__file__]) 