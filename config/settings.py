"""
HITRAN CRDS Simulator 기본 설정
"""

# 기본 물리 상수
SPEED_OF_LIGHT = 2.99792458e8  # m/s
BOLTZMANN = 1.380649e-23       # J/K
AVOGADRO = 6.02214076e23       # mol^-1

# 기본 측정 단위
DEFAULT_TEMPERATURE = 296.15    # K (23°C)
DEFAULT_PRESSURE = 1.0          # atm
DEFAULT_PATH_LENGTH = 1.0       # km
DEFAULT_RESOLUTION = 0.0001     # cm^-1 (고분해능)

# 파장 범위 설정
MIN_WAVELENGTH = 0.1           # nm
MAX_WAVELENGTH = 10000.0       # nm

# HITRAN 데이터베이스 설정
HITRAN_CACHE_DIR = "cache/"
HITRAN_DATA_DIR = "data/"
OUTPUT_DIR = "output/"

# 지원하는 농도 단위
CONCENTRATION_UNITS = ["ppm", "ppb", "percent", "molecules/cm3"]

# 시각화 설정
PLOT_DPI = 300
PLOT_FIGSIZE = (12, 8)
PLOT_STYLE = "seaborn-v0_8"

print("HITRAN CRDS 시뮬레이터 설정이 로드되었습니다.")