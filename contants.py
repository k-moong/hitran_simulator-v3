# constants.py
"""HITRAN 분자 정의 및 상수"""

# HITRAN 전체 분자 목록 (분자 ID와 함께)
HITRAN_MOLECULES = {
    # 주요 대기 성분
    "H2O": {"id": 1, "name": "물", "category": "주요 대기 성분", "common": True},
    "CO2": {"id": 2, "name": "이산화탄소", "category": "주요 대기 성분", "common": True},
    "O3": {"id": 3, "name": "오존", "category": "주요 대기 성분", "common": True},
    "N2O": {"id": 4, "name": "아산화질소", "category": "주요 대기 성분", "common": True},
    "CO": {"id": 5, "name": "일산화탄소", "category": "주요 대기 성분", "common": True},
    "CH4": {"id": 6, "name": "메탄", "category": "주요 대기 성분", "common": True},
    "O2": {"id": 7, "name": "산소", "category": "주요 대기 성분", "common": True},
    "NO": {"id": 8, "name": "일산화질소", "category": "질소 화합물", "common": True},
    "SO2": {"id": 9, "name": "이산화황", "category": "황 화합물", "common": True},
    "NO2": {"id": 10, "name": "이산화질소", "category": "질소 화합물", "common": True},
    "NH3": {"id": 11, "name": "암모니아", "category": "질소 화합물", "common": True},
    "HNO3": {"id": 12, "name": "질산", "category": "질소 화합물", "common": True},
    
    # 할로겐 화합물
    "OH": {"id": 13, "name": "하이드록실", "category": "라디칼", "common": False},
    "HF": {"id": 14, "name": "플루오르화수소", "category": "할로겐 화합물", "common": False},
    "HCl": {"id": 15, "name": "염화수소", "category": "할로겐 화합물", "common": False},
    "HBr": {"id": 16, "name": "브롬화수소", "category": "할로겐 화합물", "common": False},
    "HI": {"id": 17, "name": "요오드화수소", "category": "할로겐 화합물", "common": False},
    "ClO": {"id": 18, "name": "염소 산화물", "category": "할로겐 화합물", "common": False},
    "OCS": {"id": 19, "name": "황화카르보닐", "category": "황 화합물", "common": False},
    "H2CO": {"id": 20, "name": "포름알데히드", "category": "유기 화합물", "common": False},
    "HOCl": {"id": 21, "name": "차아염소산", "category": "할로겐 화합물", "common": False},
    "N2": {"id": 22, "name": "질소", "category": "주요 대기 성분", "common": False},
    "HCN": {"id": 23, "name": "시안화수소", "category": "유기 화합물", "common": False},
    "CH3Cl": {"id": 24, "name": "염화메틸", "category": "할로겐 화합물", "common": False},
    "H2O2": {"id": 25, "name": "과산화수소", "category": "산소 화합물", "common": False},
    "C2H2": {"id": 26, "name": "아세틸렌", "category": "유기 화합물", "common": False},
    "C2H6": {"id": 27, "name": "에탄", "category": "유기 화합물", "common": False},
    "PH3": {"id": 28, "name": "포스핀", "category": "인 화합물", "common": False},
    
    # CFC 및 HCFC
    "COF2": {"id": 29, "name": "플루오르화카르보닐", "category": "할로겐 화합물", "common": False},
    "SF6": {"id": 30, "name": "육플루오르화황", "category": "황 화합물", "common": False},
    "H2S": {"id": 31, "name": "황화수소", "category": "황 화합물", "common": False},
    "HCOOH": {"id": 32, "name": "개미산", "category": "유기 화합물", "common": False},
    "HO2": {"id": 33, "name": "하이드로퍼옥실", "category": "라디칼", "common": False},
    "O": {"id": 34, "name": "산소 원자", "category": "라디칼", "common": False},
    "ClONO2": {"id": 35, "name": "염소질산", "category": "할로겐 화합물", "common": False},
    "NO+": {"id": 36, "name": "질산 이온", "category": "이온", "common": False},
    "HOBr": {"id": 37, "name": "차아브롬산", "category": "할로겐 화합물", "common": False},
    "C2H4": {"id": 38, "name": "에틸렌", "category": "유기 화합물", "common": False},
    "CH3OH": {"id": 39, "name": "메탄올", "category": "유기 화합물", "common": False},
    "CH3Br": {"id": 40, "name": "브롬화메틸", "category": "할로겐 화합물", "common": False},
    "CH3CN": {"id": 41, "name": "아세토니트릴", "category": "유기 화합물", "common": False},
    "CF4": {"id": 42, "name": "사플루오르화탄소", "category": "할로겐 화합물", "common": False},
    "C4H2": {"id": 43, "name": "다이아세틸렌", "category": "유기 화합물", "common": False},
    "HC3N": {"id": 44, "name": "시아노아세틸렌", "category": "유기 화합물", "common": False},
    "H2": {"id": 45, "name": "수소", "category": "주요 대기 성분", "common": False},
    "CS": {"id": 46, "name": "황화탄소", "category": "황 화합물", "common": False},
    "SO3": {"id": 47, "name": "삼산화황", "category": "황 화합물", "common": False},
    "C2N2": {"id": 48, "name": "시안겐", "category": "유기 화합물", "common": False},
    "COCl2": {"id": 49, "name": "포스겐", "category": "할로겐 화합물", "common": False},
    "SO": {"id": 50, "name": "황 산화물", "category": "황 화합물", "common": False},
}

# 분자 카테고리 정의
MOLECULE_CATEGORIES = {
    "주요 대기 성분": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "주요 대기 성분"],
    "유기 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "유기 화합물"],
    "할로겐 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "할로겐 화합물"],
    "질소 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "질소 화합물"],
    "황 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "황 화합물"],
    "라디칼": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "라디칼"],
    "인 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "인 화합물"],
    "산소 화합물": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "산소 화합물"],
    "이온": [mol for mol, info in HITRAN_MOLECULES.items() if info["category"] == "이온"],
}

# 파장 대역 바로가기 정보
WAVELENGTH_SHORTCUTS = {
    "NIR_H2O_1": {"min": 1350, "max": 1400, "description": "H2O 1차 배음대"},
    "NIR_H2O_2": {"min": 1500, "max": 1600, "description": "H2O 2차 배음대"},  
    "NIR_H2O_3": {"min": 1850, "max": 1950, "description": "H2O 3차 배음대"},
    "NIR_CH4": {"min": 1630, "max": 1680, "description": "CH4 2ν3 대역"},
    "NIR_CO2": {"min": 2000, "max": 2100, "description": "CO2 조합대역"},
    "NIR_NH3": {"min": 1500, "max": 1600, "description": "NH3 2ν1 대역"},
    "MIR_H2O": {"min": 2500, "max": 3000, "description": "H2O 기본 진동"},
    "MIR_CO2": {"min": 4200, "max": 4400, "description": "CO2 ν3 대역"},
    "MIR_CH4": {"min": 3200, "max": 3400, "description": "CH4 ν3 대역"},
    "MIR_N2O": {"min": 4400, "max": 4600, "description": "N2O ν3 대역"},
    "MIR_HCl": {"min": 2800, "max": 3000, "description": "HCl 기본 진동"},
    "MIR_HF": {"min": 3900, "max": 4100, "description": "HF 기본 진동"},
    "MIR_CO": {"min": 2100, "max": 2200, "description": "CO 기본 진동"},
    "MIR_NO": {"min": 1800, "max": 2000, "description": "NO 기본 진동"},
    "MIR_SO2": {"min": 1100, "max": 1400, "description": "SO2 ν1,ν3 대역"},
}

# 기본 농도 설정 (ppb)
DEFAULT_CONCENTRATIONS = {
    "H2O": 10000.0,
    "CO2": 400000.0,
    "CH4": 1800.0,
    "N2O": 330.0,
    "CO": 100.0,
    "O3": 50.0,
    "NH3": 10.0,
    "SO2": 1.0,
    "NO2": 20.0,
    "HCl": 0.5,
    "HF": 0.1,
}