"""
HITRAN 데이터 캐시 관리 모듈
"""

import os
import pickle
import hashlib
import pandas as pd
from datetime import datetime, timedelta

class HitranCache:
    def __init__(self, cache_dir="cache/hitran_cache"):
        self.cache_dir = cache_dir
        
        # 캐시 폴더 생성
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        # 캐시 메타데이터 파일
        self.metadata_file = os.path.join(cache_dir, "cache_metadata.json")
        self.load_metadata()
    
    def load_metadata(self):
        """캐시 메타데이터 로드"""
        if os.path.exists(self.metadata_file):
            try:
                self.metadata = pd.read_json(self.metadata_file)
            except:
                self.metadata = pd.DataFrame(columns=['cache_key', 'file_path', 'created_time', 'access_count', 'file_size'])
        else:
            self.metadata = pd.DataFrame(columns=['cache_key', 'file_path', 'created_time', 'access_count', 'file_size'])
    
    def save_metadata(self):
        """캐시 메타데이터 저장"""
        self.metadata.to_json(self.metadata_file, orient='records', date_format='iso')
    
    def generate_cache_key(self, molecule, wavelength_min, wavelength_max):
        """캐시 키 생성"""
        key_string = f"{molecule}_{wavelength_min}_{wavelength_max}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_cache_path(self, cache_key):
        """캐시 파일 경로 생성"""
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")
    
    def is_cached(self, molecule, wavelength_min, wavelength_max):
        """캐시 존재 여부 확인"""
        cache_key = self.generate_cache_key(molecule, wavelength_min, wavelength_max)
        cache_path = self.get_cache_path(cache_key)
        return os.path.exists(cache_path)
    
    def save_to_cache(self, molecule, wavelength_min, wavelength_max, data):
        """데이터를 캐시에 저장"""
        cache_key = self.generate_cache_key(molecule, wavelength_min, wavelength_max)
        cache_path = self.get_cache_path(cache_key)
        
        try:
            # 데이터 저장
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            # 메타데이터 업데이트
            file_size = os.path.getsize(cache_path)
            new_entry = pd.DataFrame({
                'cache_key': [cache_key],
                'file_path': [cache_path],
                'created_time': [datetime.now().isoformat()],
                'access_count': [1],
                'file_size': [file_size],
                'molecule': [molecule],
                'wavelength_min': [wavelength_min],
                'wavelength_max': [wavelength_max]
            })
            
            # 기존 항목 제거 후 추가
            self.metadata = self.metadata[self.metadata['cache_key'] != cache_key]
            self.metadata = pd.concat([self.metadata, new_entry], ignore_index=True)
            self.save_metadata()
            
            return True
        except Exception as e:
            print(f"캐시 저장 실패: {e}")
            return False
    
    def load_from_cache(self, molecule, wavelength_min, wavelength_max):
        """캐시에서 데이터 로드"""
        cache_key = self.generate_cache_key(molecule, wavelength_min, wavelength_max)
        cache_path = self.get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            # 접근 횟수 증가
            mask = self.metadata['cache_key'] == cache_key
            if mask.any():
                self.metadata.loc[mask, 'access_count'] += 1
                self.save_metadata()
            
            return data
        except Exception as e:
            print(f"캐시 로드 실패: {e}")
            return None
    
    def clean_cache(self, max_age_days=30, max_size_mb=1000):
        """캐시 정리"""
        current_time = datetime.now()
        total_size = 0
        files_to_remove = []
        
        for _, row in self.metadata.iterrows():
            cache_path = row['file_path']
            created_time = datetime.fromisoformat(row['created_time'])
            file_size = row['file_size']
            
            # 오래된 파일 확인
            age = (current_time - created_time).days
            if age > max_age_days:
                files_to_remove.append(row['cache_key'])
                continue
            
            total_size += file_size
        
        # 용량 초과 시 오래된 파일부터 삭제
        if total_size > max_size_mb * 1024 * 1024:
            # 접근 횟수가 적고 오래된 순으로 정렬
            sorted_metadata = self.metadata.sort_values(['access_count', 'created_time'])
            
            for _, row in sorted_metadata.iterrows():
                if total_size <= max_size_mb * 1024 * 1024:
                    break
                
                files_to_remove.append(row['cache_key'])
                total_size -= row['file_size']
        
        # 파일 삭제
        removed_count = 0
        for cache_key in files_to_remove:
            cache_path = self.get_cache_path(cache_key)
            try:
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                    removed_count += 1
            except:
                pass
        
        # 메타데이터에서 제거
        self.metadata = self.metadata[~self.metadata['cache_key'].isin(files_to_remove)]
        self.save_metadata()
        
        return removed_count
    
    def get_cache_stats(self):
        """캐시 통계 정보"""
        if len(self.metadata) == 0:
            return {
                'total_files': 0,
                'total_size_mb': 0,
                'most_accessed': None,
                'oldest_file': None
            }
        
        total_size = self.metadata['file_size'].sum()
        most_accessed = self.metadata.loc[self.metadata['access_count'].idxmax()]
        oldest_file = self.metadata.loc[self.metadata['created_time'].idxmin()]
        
        return {
            'total_files': len(self.metadata),
            'total_size_mb': total_size / (1024 * 1024),
            'most_accessed': f"{most_accessed['molecule']} ({most_accessed['access_count']}회)",
            'oldest_file': oldest_file['created_time'],
            'cache_hits': self.metadata['access_count'].sum()
        }