"""
Advanced Analysis Tools
- Experimental data comparison and fitting
- Noise simulation
- Uncertainty analysis
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import optimize, stats
from scipy.interpolate import interp1d
import warnings
warnings.filterwarnings('ignore')

class ExperimentalDataAnalyzer:
    """Experimental data analysis and comparison"""
    
    def __init__(self):
        self.experimental_data = None
        self.simulated_data = None
        self.fitted_params = None
    
    def load_experimental_data(self, file_path=None, wavelength=None, absorption=None):
        """
        Load experimental data
        
        Args:
            file_path: CSV file path (wavelength, absorption columns)
            wavelength: wavelength array (nm)
            absorption: absorption array
        """
        if file_path:
            try:
                data = pd.read_csv(file_path)
                # Flexible column name handling
                wavelength_col = None
                absorption_col = None
                
                for col in data.columns:
                    col_lower = col.lower()
                    if 'wave' in col_lower or 'nm' in col_lower or 'lambda' in col_lower:
                        wavelength_col = col
                    elif 'abs' in col_lower or 'intensity' in col_lower or 'trans' in col_lower:
                        absorption_col = col
                
                if wavelength_col and absorption_col:
                    self.experimental_data = {
                        'wavelength': data[wavelength_col].values,
                        'absorption': data[absorption_col].values
                    }
                    print(f"✅ Experimental data loaded: {len(self.experimental_data['wavelength'])} points")
                    return True
                else:
                    print("❌ Could not find wavelength/absorption columns")
                    return False
                    
            except Exception as e:
                print(f"❌ File loading failed: {e}")
                return False
        
        elif wavelength is not None and absorption is not None:
            self.experimental_data = {
                'wavelength': np.array(wavelength),
                'absorption': np.array(absorption)
            }
            print(f"✅ Experimental data set: {len(wavelength)} points")
            return True
        
        else:
            print("❌ Please provide file path or data arrays")
            return False
    
    def interpolate_simulated_data(self, sim_wavelength, sim_absorption, experimental_wavelength):
        """Interpolate simulation data to match experimental wavelength"""
        try:
            # Find overlapping wavelength range
            min_wl = max(sim_wavelength.min(), experimental_wavelength.min())
            max_wl = min(sim_wavelength.max(), experimental_wavelength.max())
            
            # Extract overlapping region
            exp_mask = (experimental_wavelength >= min_wl) & (experimental_wavelength <= max_wl)
            exp_wl_overlap = experimental_wavelength[exp_mask]
            
            if len(exp_wl_overlap) < 5:
                print("❌ Overlapping wavelength range too small")
                return None, None
            
            # Interpolate simulation data
            interp_func = interp1d(sim_wavelength, sim_absorption, kind='linear', 
                                 bounds_error=False, fill_value='extrapolate')
            sim_interpolated = interp_func(exp_wl_overlap)
            
            print(f"✅ Data interpolation complete: {len(exp_wl_overlap)} points for comparison")
            return exp_wl_overlap, sim_interpolated
            
        except Exception as e:
            print(f"❌ Data interpolation failed: {e}")
            return None, None
    
    def fit_scaling_factor(self, sim_wavelength, sim_absorption):
        """Fit scaling factor to match experimental data"""
        if self.experimental_data is None:
            print("❌ No experimental data available")
            return None
        
        # Data interpolation
        exp_wl, sim_interp = self.interpolate_simulated_data(
            sim_wavelength, sim_absorption, self.experimental_data['wavelength']
        )
        
        if exp_wl is None:
            return None
        
        # Extract experimental data (overlapping region)
        exp_mask = (self.experimental_data['wavelength'] >= exp_wl.min()) & \
                   (self.experimental_data['wavelength'] <= exp_wl.max())
        exp_abs = self.experimental_data['absorption'][exp_mask]
        
        # Fit scaling factor (y = a*x + b)
        def fit_function(params, sim_data, exp_data):
            scale, offset = params
            fitted = scale * sim_data + offset
            return np.sum((fitted - exp_data)**2)
        
        # Initial estimates
        initial_scale = np.mean(exp_abs) / np.mean(sim_interp) if np.mean(sim_interp) != 0 else 1.0
        initial_offset = np.mean(exp_abs) - initial_scale * np.mean(sim_interp)
        
        # Optimization
        result = optimize.minimize(
            fit_function, 
            [initial_scale, initial_offset],
            args=(sim_interp, exp_abs),
            method='Nelder-Mead'
        )
        
        if result.success:
            scale, offset = result.x
            fitted_absorption = scale * sim_interp + offset
            
            # Calculate R²
            ss_res = np.sum((exp_abs - fitted_absorption)**2)
            ss_tot = np.sum((exp_abs - np.mean(exp_abs))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            # RMS error
            rmse = np.sqrt(np.mean((exp_abs - fitted_absorption)**2))
            
            self.fitted_params = {
                'scale': scale,
                'offset': offset,
                'r_squared': r_squared,
                'rmse': rmse,
                'wavelength': exp_wl,
                'experimental': exp_abs,
                'fitted': fitted_absorption
            }
            
            print(f"✅ Fitting complete!")
            print(f"   Scaling factor: {scale:.4f}")
            print(f"   Offset: {offset:.6f}")
            print(f"   R²: {r_squared:.4f}")
            print(f"   RMSE: {rmse:.6f}")
            
            return self.fitted_params
        else:
            print("❌ Fitting failed")
            return None
    
    def plot_comparison(self, save_path=None):
        """Plot comparison between experimental data and fitting results"""
        if self.fitted_params is None:
            print("❌ No fitting data available")
            return
        
        plt.figure(figsize=(12, 8))
        
        # Full experimental data
        plt.subplot(2, 1, 1)
        plt.plot(self.experimental_data['wavelength'], self.experimental_data['absorption'], 
                'b-', label='Experimental Data', alpha=0.7)
        plt.plot(self.fitted_params['wavelength'], self.fitted_params['fitted'], 
                'r-', label=f'Fitted Result (R²={self.fitted_params["r_squared"]:.3f})', linewidth=2)
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Absorption')
        plt.title('Experimental Data vs Simulation Fitting Result')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Residual plot
        plt.subplot(2, 1, 2)
        residuals = self.fitted_params['experimental'] - self.fitted_params['fitted']
        plt.plot(self.fitted_params['wavelength'], residuals, 'g-', alpha=0.7)
        plt.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Residuals')
        plt.title(f'Residual Analysis (RMSE: {self.fitted_params["rmse"]:.6f})')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"💾 Plot saved: {save_path}")
        
        plt.show()

class NoiseSimulator:
    """Noise simulation"""
    
    @staticmethod
    def add_gaussian_noise(spectrum, snr_db):
        """Add Gaussian noise"""
        signal_power = np.mean(spectrum**2)
        snr_linear = 10**(snr_db/10)
        noise_power = signal_power / snr_linear
        noise = np.random.normal(0, np.sqrt(noise_power), len(spectrum))
        return spectrum + noise, noise
    
    @staticmethod
    def add_shot_noise(spectrum, photon_count_factor=1000):
        """Add shot noise (Poisson noise)"""
        # Convert spectrum to photon counts
        photon_counts = spectrum * photon_count_factor
        # Apply Poisson noise
        noisy_counts = np.random.poisson(np.maximum(photon_counts, 0))
        # Convert back to spectrum
        noisy_spectrum = noisy_counts / photon_count_factor
        noise = noisy_spectrum - spectrum
        return noisy_spectrum, noise
    
    @staticmethod
    def add_baseline_drift(spectrum, wavelength, drift_amplitude=0.01, drift_frequency=1):
        """Add baseline drift"""
        baseline = drift_amplitude * np.sin(2 * np.pi * drift_frequency * 
                                          (wavelength - wavelength.min()) / 
                                          (wavelength.max() - wavelength.min()))
        return spectrum + baseline, baseline
    
    @staticmethod
    def add_spikes(spectrum, wavelength, num_spikes=5, spike_amplitude=0.1):
        """Add spike noise"""
        noisy_spectrum = spectrum.copy()
        spike_positions = np.random.randint(0, len(spectrum), num_spikes)
        spike_values = np.random.normal(0, spike_amplitude, num_spikes)
        
        spikes = np.zeros_like(spectrum)
        for pos, val in zip(spike_positions, spike_values):
            noisy_spectrum[pos] += val
            spikes[pos] = val
        
        return noisy_spectrum, spikes
    
    @staticmethod
    def simulate_realistic_noise(spectrum, wavelength, snr_db=30, include_shot=True, 
                                include_baseline=True, include_spikes=True):
        """Realistic composite noise simulation"""
        noisy_spectrum = spectrum.copy()
        noise_components = {}
        
        # Gaussian noise
        noisy_spectrum, gaussian_noise = NoiseSimulator.add_gaussian_noise(noisy_spectrum, snr_db)
        noise_components['gaussian'] = gaussian_noise
        
        # Shot noise
        if include_shot:
            noisy_spectrum, shot_noise = NoiseSimulator.add_shot_noise(noisy_spectrum)
            noise_components['shot'] = shot_noise
        
        # Baseline drift
        if include_baseline:
            noisy_spectrum, baseline_drift = NoiseSimulator.add_baseline_drift(
                noisy_spectrum, wavelength, drift_amplitude=np.max(spectrum)*0.02
            )
            noise_components['baseline'] = baseline_drift
        
        # Spikes
        if include_spikes:
            noisy_spectrum, spikes = NoiseSimulator.add_spikes(
                noisy_spectrum, wavelength, num_spikes=3, 
                spike_amplitude=np.max(spectrum)*0.05
            )
            noise_components['spikes'] = spikes
        
        return noisy_spectrum, noise_components

class UncertaintyAnalyzer:
    """Uncertainty analysis"""
    
    def __init__(self):
        self.monte_carlo_results = None
    
    def parameter_uncertainty_propagation(self, base_params, uncertainties, num_samples=1000):
        """
        Parameter uncertainty propagation analysis
        
        Args:
            base_params: base parameter dictionary
            uncertainties: uncertainty for each parameter (standard deviation)
            num_samples: number of Monte Carlo samples
        """
        results = []
        param_samples = {}
        
        # Normal distribution sampling for each parameter
        for param, base_value in base_params.items():
            if param in uncertainties:
                uncertainty = uncertainties[param]
                samples = np.random.normal(base_value, uncertainty, num_samples)
                param_samples[param] = samples
            else:
                param_samples[param] = np.full(num_samples, base_value)
        
        print(f"🎲 Monte Carlo simulation started: {num_samples} samples")
        
        self.monte_carlo_results = {
            'param_samples': param_samples,
            'base_params': base_params,
            'uncertainties': uncertainties,
            'num_samples': num_samples
        }
        
        return param_samples
    
    def calculate_spectrum_uncertainty(self, spectrum_function, wavelength, param_samples):
        """
        Calculate spectrum uncertainty
        
        Args:
            spectrum_function: spectrum calculation function
            wavelength: wavelength array
            param_samples: parameter samples
        """
        num_samples = len(list(param_samples.values())[0])
        spectra = np.zeros((num_samples, len(wavelength)))
        
        print("📊 Calculating spectrum uncertainty...")
        
        # Calculate spectrum for each sample
        for i in range(num_samples):
            if i % (num_samples // 10) == 0:
                print(f"   Progress: {i/num_samples*100:.0f}%")
            
            # Current sample parameters
            current_params = {param: samples[i] for param, samples in param_samples.items()}
            
            try:
                # Calculate spectrum
                spectrum = spectrum_function(wavelength, **current_params)
                spectra[i] = spectrum
            except Exception as e:
                print(f"   Sample {i} calculation failed: {e}")
                spectra[i] = np.nan
        
        # Statistical calculation
        valid_spectra = spectra[~np.isnan(spectra).any(axis=1)]
        
        if len(valid_spectra) == 0:
            print("❌ No valid spectra available")
            return None
        
        mean_spectrum = np.mean(valid_spectra, axis=0)
        std_spectrum = np.std(valid_spectra, axis=0)
        
        # Confidence interval calculation (95%)
        confidence_level = 0.95
        alpha = 1 - confidence_level
        lower_percentile = (alpha/2) * 100
        upper_percentile = (1 - alpha/2) * 100
        
        confidence_lower = np.percentile(valid_spectra, lower_percentile, axis=0)
        confidence_upper = np.percentile(valid_spectra, upper_percentile, axis=0)
        
        uncertainty_results = {
            'wavelength': wavelength,
            'mean_spectrum': mean_spectrum,
            'std_spectrum': std_spectrum,
            'confidence_lower': confidence_lower,
            'confidence_upper': confidence_upper,
            'confidence_level': confidence_level,
            'valid_samples': len(valid_spectra),
            'total_samples': num_samples
        }
        
        print(f"✅ Uncertainty analysis complete: {len(valid_spectra)}/{num_samples} valid samples")
        
        return uncertainty_results
    
    def plot_uncertainty_analysis(self, uncertainty_results, save_path=None):
        """Plot uncertainty analysis results"""
        if uncertainty_results is None:
            print("❌ No uncertainty analysis results available")
            return
        
        wavelength = uncertainty_results['wavelength']
        mean_spectrum = uncertainty_results['mean_spectrum']
        std_spectrum = uncertainty_results['std_spectrum']
        conf_lower = uncertainty_results['confidence_lower']
        conf_upper = uncertainty_results['confidence_upper']
        conf_level = uncertainty_results['confidence_level']
        
        plt.figure(figsize=(12, 10))
        
        # Main spectrum and uncertainty
        plt.subplot(3, 1, 1)
        plt.plot(wavelength, mean_spectrum, 'b-', label='Mean Spectrum', linewidth=2)
        plt.fill_between(wavelength, conf_lower, conf_upper, alpha=0.3, 
                        label=f'{conf_level*100:.0f}% Confidence Interval')
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Absorption')
        plt.title('Spectrum Uncertainty Analysis')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Standard deviation
        plt.subplot(3, 1, 2)
        plt.plot(wavelength, std_spectrum, 'r-', linewidth=2)
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Standard Deviation')
        plt.title('Uncertainty by Wavelength (Standard Deviation)')
        plt.grid(True, alpha=0.3)
        
        # Relative uncertainty (%)
        plt.subplot(3, 1, 3)
        relative_uncertainty = (std_spectrum / np.abs(mean_spectrum)) * 100
        # Remove infinite values
        relative_uncertainty = np.where(np.isfinite(relative_uncertainty), 
                                      relative_uncertainty, np.nan)
        plt.plot(wavelength, relative_uncertainty, 'g-', linewidth=2)
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Relative Uncertainty (%)')
        plt.title('Relative Uncertainty')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"💾 Uncertainty plot saved: {save_path}")
        
        plt.show()

# Test and examples
if __name__ == "__main__":
    print("=== Advanced Analysis Tools Test ===")
    
    # Generate example data
    wavelength = np.linspace(1500, 1520, 1000)
    true_spectrum = 0.1 * np.exp(-((wavelength - 1510)**2) / 20) + 0.02
    
    print("\n1️⃣ Noise Simulation Test")
    
    # Add noise
    noisy_spectrum, noise_components = NoiseSimulator.simulate_realistic_noise(
        true_spectrum, wavelength, snr_db=25
    )
    
    # Plot
    plt.figure(figsize=(12, 8))
    plt.subplot(2, 1, 1)
    plt.plot(wavelength, true_spectrum, 'b-', label='Original Spectrum', linewidth=2)
    plt.plot(wavelength, noisy_spectrum, 'r-', alpha=0.7, label='With Noise')
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Absorption')
    plt.title('Noise Simulation Results')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Noise components
    plt.subplot(2, 1, 2)
    offset = 0
    for noise_type, noise_data in noise_components.items():
        plt.plot(wavelength, noise_data + offset, label=f'{noise_type} noise')
        offset += np.max(np.abs(noise_data)) * 1.5
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Noise Magnitude')
    plt.title('Noise Component Analysis')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    print("\n2️⃣ Experimental Data Analysis Test")
    
    # Generate mock experimental data (noise + scaling)
    exp_spectrum = 1.2 * true_spectrum + 0.01 + np.random.normal(0, 0.005, len(true_spectrum))
    
    analyzer = ExperimentalDataAnalyzer()
    analyzer.load_experimental_data(wavelength=wavelength, absorption=exp_spectrum)
    
    # Fitting
    fit_result = analyzer.fit_scaling_factor(wavelength, true_spectrum)
    
    if fit_result:
        analyzer.plot_comparison()
    
    print("\n3️⃣ Uncertainty Analysis Test")
    
    # Define simple spectrum function
    def simple_spectrum_function(wl, amplitude=0.1, center=1510, width=20, baseline=0.02):
        return amplitude * np.exp(-((wl - center)**2) / width) + baseline
    
    # Define parameters and uncertainties
    base_params = {
        'amplitude': 0.1,
        'center': 1510,
        'width': 20,
        'baseline': 0.02
    }
    
    uncertainties = {
        'amplitude': 0.01,  # 10% uncertainty
        'center': 0.5,      # 0.5 nm uncertainty
        'width': 2,         # 2 nm uncertainty
        'baseline': 0.002   # 10% uncertainty
    }
    
    uncertainty_analyzer = UncertaintyAnalyzer()
    
    # Parameter sampling
    param_samples = uncertainty_analyzer.parameter_uncertainty_propagation(
        base_params, uncertainties, num_samples=500
    )
    
    # Calculate spectrum uncertainty
    uncertainty_results = uncertainty_analyzer.calculate_spectrum_uncertainty(
        simple_spectrum_function, wavelength, param_samples
    )
    
    # Uncertainty plot
    if uncertainty_results:
        uncertainty_analyzer.plot_uncertainty_analysis(uncertainty_results)
    
    print("✅ All advanced analysis tool tests complete!")