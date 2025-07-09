"""
프리셋 관리 모듈
"""

import json
import os
import pandas as pd
from datetime import datetime

class PresetManager:
    def __init__(self, preset_file="presets/user_presets.json"):
        self.preset_file = preset_file
        self.preset_dir = os.path.dirname(preset_file)
        
        # 프리셋 폴더 생성
        if not os.path.exists(self.preset_dir):
            os.makedirs(self.preset_dir)
        
        # 기본 프리셋 생성
        self.create_default_presets()
    
    def create_default_presets(self):
        """기본 프리셋들 생성"""
        default_presets = {
            "대기_측정_표준": {
                "name": "대기 측정 표준 조건",
                "description": "일반적인 대기 측정 조건",
                "molecules": ["H2O", "CO2", "CH4"],
                "concentrations": {"H2O": 10000, "CO2": 400000, "CH4": 1800},
                "temperature": 296.15,
                "pressure_torr": 760.0,
                "path_length_m": 1000.0,
                "wavelength_min": 1500,
                "wavelength_max": 1600,
                "created_date": "2024-01-01 00:00:00",
                "category": "기본"
            },
            "고압_실험": {
                "name": "고압 실험 조건",
                "description": "고압 챔버 실험 조건",
                "molecules": ["H2O"],
                "concentrations": {"H2O": 5000},
                "temperature": 300.0,
                "pressure_torr": 5000.0,
                "path_length_m": 100.0,
                "wavelength_min": 1500,
                "wavelength_max": 1520,
                "created_date": "2024-01-01 00:00:00",
                "category": "실험"
            },
            "저농도_검출": {
                "name": "저농도 검출 조건",
                "description": "극저농도 가스 검출",
                "molecules": ["CH4"],
                "concentrations": {"CH4": 100},
                "temperature": 296.15,
                "pressure_torr": 760.0,
                "path_length_m": 10000.0,
                "wavelength_min": 1640,
                "wavelength_max": 1680,
                "created_date": "2024-01-01 00:00:00",
                "category": "검출"
            },
            "NIR_수증기": {
                "name": "NIR 수증기 분석",
                "description": "근적외선 수증기 흡수선 분석",
                "molecules": ["H2O"],
                "concentrations": {"H2O": 20000},
                "temperature": 296.15,
                "pressure_torr": 760.0,
                "path_length_m": 1000.0,
                "wavelength_min": 1350,
                "wavelength_max": 1400,
                "created_date": "2024-01-01 00:00:00",
                "category": "분석"
            },
            "CRDS_최적화": {
                "name": "CRDS 최적화 조건",
                "description": "CRDS 감도 최적화",
                "molecules": ["H2O", "CH4"],
                "concentrations": {"H2O": 1000, "CH4": 2000},
                "temperature": 296.15,
                "pressure_torr": 100.0,
                "path_length_m": 30000.0,
                "wavelength_min": 1650,
                "wavelength_max": 1670,
                "created_date": "2024-01-01 00:00:00",
                "category": "CRDS"
            }
        }
        
        # 파일이 없으면 기본 프리셋으로 생성
        if not os.path.exists(self.preset_file):
            self.save_presets(default_presets)
    
    def load_presets(self):
        """프리셋 불러오기"""
        try:
            with open(self.preset_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_presets(self, presets):
        """프리셋 저장하기"""
        with open(self.preset_file, 'w', encoding='utf-8') as f:
            json.dump(presets, f, ensure_ascii=False, indent=2)
    
    def add_preset(self, preset_id, preset_data):
        """새 프리셋 추가"""
        presets = self.load_presets()
        preset_data['created_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        presets[preset_id] = preset_data
        self.save_presets(presets)
    
    def delete_preset(self, preset_id):
        """프리셋 삭제"""
        presets = self.load_presets()
        if preset_id in presets:
            del presets[preset_id]
            self.save_presets(presets)
            return True
        return False
    
    def get_preset(self, preset_id):
        """특정 프리셋 가져오기"""
        presets = self.load_presets()
        return presets.get(preset_id)
    
    def get_presets_by_category(self, category=None):
        """카테고리별 프리셋 가져오기"""
        presets = self.load_presets()
        if category:
            return {k: v for k, v in presets.items() if v.get('category') == category}
        return presets
    
    def export_presets(self):
        """프리셋 내보내기 (CSV)"""
        presets = self.load_presets()
        preset_list = []
        
        for preset_id, preset_data in presets.items():
            row = {
                'ID': preset_id,
                'Name': preset_data.get('name', ''),
                'Description': preset_data.get('description', ''),
                'Molecules': ', '.join(preset_data.get('molecules', [])),
                'Temperature_K': preset_data.get('temperature', 0),
                'Pressure_torr': preset_data.get('pressure_torr', 0),
                'Path_length_m': preset_data.get('path_length_m', 0),
                'Wavelength_range': f"{preset_data.get('wavelength_min', 0)}-{preset_data.get('wavelength_max', 0)}nm",
                'Category': preset_data.get('category', ''),
                'Created_date': preset_data.get('created_date', '')
            }
            
            # 농도 정보 추가
            concentrations = preset_data.get('concentrations', {})
            for mol, conc in concentrations.items():
                row[f'{mol}_ppb'] = conc
            
            preset_list.append(row)
        
        return pd.DataFrame(preset_list)

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
    "MIR_N2O": {"min": 4400, "max": 4600, "description": "N2O ν3 대역"}
}

def get_wavelength_shortcuts():
    """파장 대역 바로가기 정보 반환"""
    return WAVELENGTH_SHORTCUTS