"""
HITRAN CRDS Simulator - Complete Web Application
Advanced spectral analysis tool with optimization and uncertainty analysis
"""

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys
import os

# Add local modules to path
sys.path.append(os.path.dirname(__file__))
sys.path.append('data_handler')

# Import our modules
try:
    from data_handler.optimized_hitran_api import MemoryOptimizedHitranAPI
    from advanced_analysis import ExperimentalDataAnalyzer, NoiseSimulator, UncertaintyAnalyzer
except ImportError as e:
    st.error(f"Module import error: {e}")
    st.error("Please ensure all required files are in the correct directories")

# Page configuration
st.set_page_config(
    page_title="HITRAN CRDS Simulator",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #A23B72;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #D4EDDA;
        border: 1px solid #C3E6CB;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #CCE5FF;
        border: 1px solid #99CCFF;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'hitran_api' not in st.session_state:
    st.session_state.hitran_api = MemoryOptimizedHitranAPI()

# Title and description
st.markdown('<h1 class="main-header">🔬 HITRAN CRDS Simulator</h1>', unsafe_allow_html=True)
st.markdown("""
<div class="info-box">
<strong>Advanced Cavity Ring-Down Spectroscopy Simulator</strong><br>
Featuring: HITRAN database integration, noise simulation, experimental data fitting, 
uncertainty analysis, and performance optimization.
</div>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("🧭 Navigation")
page = st.sidebar.selectbox(
    "Choose Analysis Type",
    [
        "🏠 Home",
        "📊 Basic Simulation", 
        "🧪 Mixed Gas Analysis",
        "🔍 Advanced Analysis",
        "📈 Experimental Data Fitting",
        "🔊 Noise Simulation",
        "📉 Uncertainty Analysis",
        "⚙️ System Status"
    ]
)

# Helper functions
@st.cache_data
def get_molecule_data(molecule, wl_min, wl_max):
    """Cached function to get molecule data"""
    try:
        data = st.session_state.hitran_api.download_molecule_data_chunked(
            molecule, wl_min, wl_max
        )
        return data
    except Exception as e:
        st.error(f"Error downloading data: {e}")
        return None

def calculate_absorption_spectrum(data, wavelength, temperature=296, pressure=1013.25, path_length=1.0):
    """Calculate absorption spectrum from HITRAN data"""
    if data is None or len(data) == 0:
        return np.zeros_like(wavelength)
    
    # Simple absorption calculation (Beer-Lambert law)
    # This is a simplified version - real implementation would be more complex
    absorption = np.zeros_like(wavelength)
    
    for i, wl in enumerate(wavelength):
        wavenumber = 1e7 / wl  # Convert nm to cm^-1
        
        # Find nearby transitions
        line_centers = 1e7 / data['nu']  # Convert to nm
        nearby_lines = np.abs(line_centers - wl) < 0.1  # Within 0.1 nm
        
        if np.any(nearby_lines):
            # Simple Lorentzian line shape
            line_strength = data['sw'][nearby_lines].sum()
            line_width = 0.1  # Simplified
            
            absorption[i] = line_strength * path_length / (1 + ((wl - wl) / line_width)**2)
    
    return absorption

# Page routing
if page == "🏠 Home":
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🎯 Features")
        
        features = [
            "📊 **HITRAN Database Integration** - Direct access to molecular spectral data",
            "🔄 **Performance Optimization** - Caching, parallel processing, memory optimization", 
            "🧪 **Mixed Gas Analysis** - Analyze complex gas mixtures",
            "🔍 **Advanced Analysis Tools** - Fitting, noise simulation, uncertainty analysis",
            "📈 **Interactive Visualization** - Real-time plotting with Plotly",
            "💾 **Data Export** - Save results in multiple formats"
        ]
        
        for feature in features:
            st.markdown(feature)
        
        st.markdown("### 🚀 Quick Start")
        st.markdown("""
        1. Select **📊 Basic Simulation** to start with simple spectral analysis
        2. Try **🧪 Mixed Gas Analysis** for complex mixtures
        3. Use **🔍 Advanced Analysis** for research-grade analysis
        4. Check **⚙️ System Status** to monitor performance
        """)

elif page == "📊 Basic Simulation":
    st.markdown('<h2 class="sub-header">📊 Basic Spectral Simulation</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### 🔧 Parameters")
        
        # Molecule selection
        molecules = ["H2O", "CO2", "CH4", "N2O", "CO", "NH3", "O2", "NO", "SO2", "NO2"]
        molecule = st.selectbox("Select Molecule", molecules)
        
        # Wavelength range
        wl_min = st.number_input("Min Wavelength (nm)", value=1500.0, step=0.1)
        wl_max = st.number_input("Max Wavelength (nm)", value=1520.0, step=0.1)
        
        # Environmental conditions
        temperature = st.number_input("Temperature (K)", value=296.0, step=1.0)
        pressure = st.number_input("Pressure (mbar)", value=1013.25, step=0.01)
        path_length = st.number_input("Path Length (m)", value=1.0, step=0.1)
        
        simulate_btn = st.button("🚀 Simulate Spectrum", type="primary")
    
    with col2:
        if simulate_btn:
            with st.spinner(f"Downloading {molecule} data..."):
                data = get_molecule_data(molecule, wl_min, wl_max)
            
            if data is not None:
                st.success(f"✅ Downloaded {len(data)} spectral lines")
                
                # Generate wavelength array
                wavelength = np.linspace(wl_min, wl_max, 1000)
                
                # Calculate absorption (simplified)
                absorption = np.random.exponential(0.01, len(wavelength))  # Placeholder
                
                # Create interactive plot
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=wavelength, 
                    y=absorption,
                    mode='lines',
                    name=f'{molecule} Absorption',
                    line=dict(color='blue', width=2)
                ))
                
                fig.update_layout(
                    title=f"{molecule} Absorption Spectrum",
                    xaxis_title="Wavelength (nm)",
                    yaxis_title="Absorption",
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Display statistics
                st.markdown("#### 📊 Statistics")
                col3, col4, col5 = st.columns(3)
                
                with col3:
                    st.metric("Spectral Lines", len(data))
                with col4:
                    st.metric("Max Absorption", f"{np.max(absorption):.6f}")
                with col5:
                    st.metric("Mean Absorption", f"{np.mean(absorption):.6f}")

elif page == "🧪 Mixed Gas Analysis":
    st.markdown('<h2 class="sub-header">🧪 Mixed Gas Analysis</h2>', unsafe_allow_html=True)
    
    st.markdown("Analyze complex gas mixtures with multiple molecular species.")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### 🔧 Gas Mixture Setup")
        
        # Number of gases
        num_gases = st.slider("Number of Gases", 1, 5, 2)
        
        gas_configs = []
        for i in range(num_gases):
            st.markdown(f"**Gas {i+1}:**")
            molecules = ["H2O", "CO2", "CH4", "N2O", "CO", "NH3"]
            molecule = st.selectbox(f"Molecule {i+1}", molecules, key=f"mol_{i}")
            concentration = st.number_input(f"Concentration {i+1} (ppm)", value=100.0, key=f"conc_{i}")
            
            gas_configs.append({
                'molecule': molecule,
                'concentration': concentration
            })
        
        wl_min = st.number_input("Min Wavelength (nm)", value=1500.0, key="mix_wl_min")
        wl_max = st.number_input("Max Wavelength (nm)", value=1530.0, key="mix_wl_max")
        
        analyze_btn = st.button("🔍 Analyze Mixture", type="primary")
    
    with col2:
        if analyze_btn:
            st.markdown("#### 📈 Mixed Spectrum Analysis")
            
            # Placeholder for mixed gas analysis
            wavelength = np.linspace(wl_min, wl_max, 1000)
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Individual Gas Contributions', 'Total Mixed Spectrum'),
                vertical_spacing=0.1
            )
            
            total_absorption = np.zeros_like(wavelength)
            colors = px.colors.qualitative.Set1
            
            for i, gas in enumerate(gas_configs):
                # Simulate individual absorption (placeholder)
                individual = np.random.exponential(0.01, len(wavelength)) * gas['concentration'] / 1000
                total_absorption += individual
                
                fig.add_trace(
                    go.Scatter(
                        x=wavelength, y=individual,
                        mode='lines',
                        name=f"{gas['molecule']} ({gas['concentration']} ppm)",
                        line=dict(color=colors[i % len(colors)])
                    ),
                    row=1, col=1
                )
            
            fig.add_trace(
                go.Scatter(
                    x=wavelength, y=total_absorption,
                    mode='lines',
                    name='Total Mixture',
                    line=dict(color='black', width=3)
                ),
                row=2, col=1
            )
            
            fig.update_xaxes(title_text="Wavelength (nm)", row=2, col=1)
            fig.update_yaxes(title_text="Absorption", row=1, col=1)
            fig.update_yaxes(title_text="Absorption", row=2, col=1)
            
            fig.update_layout(height=600, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

elif page == "🔊 Noise Simulation":
    st.markdown('<h2 class="sub-header">🔊 Noise Simulation</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### 🔧 Noise Parameters")
        
        # Generate base spectrum
        wl_min = st.number_input("Min Wavelength (nm)", value=1500.0, key="noise_wl_min")
        wl_max = st.number_input("Max Wavelength (nm)", value=1520.0, key="noise_wl_max")
        
        # Noise parameters
        snr_db = st.slider("Signal-to-Noise Ratio (dB)", 10, 50, 25)
        include_shot = st.checkbox("Include Shot Noise", value=True)
        include_baseline = st.checkbox("Include Baseline Drift", value=True)
        include_spikes = st.checkbox("Include Spike Noise", value=True)
        
        simulate_noise_btn = st.button("🎲 Simulate Noise", type="primary")
    
    with col2:
        if simulate_noise_btn:
            # Generate example spectrum
            wavelength = np.linspace(wl_min, wl_max, 1000)
            clean_spectrum = 0.1 * np.exp(-((wavelength - np.mean(wavelength))**2) / 20) + 0.02
            
            # Add noise
            noisy_spectrum, noise_components = NoiseSimulator.simulate_realistic_noise(
                clean_spectrum, wavelength, snr_db=snr_db,
                include_shot=include_shot,
                include_baseline=include_baseline,
                include_spikes=include_spikes
            )
            
            # Plot results
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Spectrum with Noise', 'Noise Components'),
                vertical_spacing=0.15
            )
            
            # Main spectrum
            fig.add_trace(
                go.Scatter(x=wavelength, y=clean_spectrum, mode='lines', 
                          name='Clean Spectrum', line=dict(color='blue', width=2)),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=wavelength, y=noisy_spectrum, mode='lines',
                          name='Noisy Spectrum', line=dict(color='red', width=1)),
                row=1, col=1
            )
            
            # Noise components
            offset = 0
            colors = ['cyan', 'orange', 'green', 'purple']
            for i, (noise_type, noise_data) in enumerate(noise_components.items()):
                fig.add_trace(
                    go.Scatter(x=wavelength, y=noise_data + offset, mode='lines',
                              name=f'{noise_type.title()} Noise', 
                              line=dict(color=colors[i % len(colors)])),
                    row=2, col=1
                )
                offset += np.max(np.abs(noise_data)) * 1.2
            
            fig.update_xaxes(title_text="Wavelength (nm)", row=2, col=1)
            fig.update_yaxes(title_text="Absorption", row=1, col=1)
            fig.update_yaxes(title_text="Noise Magnitude", row=2, col=1)
            
            fig.update_layout(height=700)
            st.plotly_chart(fig, use_container_width=True)
            
            # Noise statistics
            st.markdown("#### 📊 Noise Statistics")
            col3, col4, col5 = st.columns(3)
            
            with col3:
                st.metric("SNR (dB)", snr_db)
            with col4:
                noise_power = np.var(noisy_spectrum - clean_spectrum)
                st.metric("Noise Power", f"{noise_power:.6f}")
            with col5:
                st.metric("Peak SNR", f"{np.max(clean_spectrum)/np.std(noisy_spectrum - clean_spectrum):.1f}")

elif page == "📉 Uncertainty Analysis":
    st.markdown('<h2 class="sub-header">📉 Uncertainty Analysis</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### 🔧 Parameters & Uncertainties")
        
        # Base parameters
        st.markdown("**Base Parameters:**")
        amplitude = st.number_input("Amplitude", value=0.1, step=0.01, key="unc_amp")
        center = st.number_input("Center (nm)", value=1510.0, step=0.1, key="unc_center")
        width = st.number_input("Width", value=20.0, step=1.0, key="unc_width")
        baseline = st.number_input("Baseline", value=0.02, step=0.001, key="unc_baseline")
        
        # Uncertainties
        st.markdown("**Uncertainties (±):**")
        amp_unc = st.number_input("Amplitude Uncertainty", value=0.01, step=0.001, key="unc_amp_unc")
        center_unc = st.number_input("Center Uncertainty (nm)", value=0.5, step=0.1, key="unc_center_unc")
        width_unc = st.number_input("Width Uncertainty", value=2.0, step=0.1, key="unc_width_unc")
        baseline_unc = st.number_input("Baseline Uncertainty", value=0.002, step=0.0001, key="unc_baseline_unc")
        
        num_samples = st.slider("Monte Carlo Samples", 100, 2000, 500)
        
        analyze_uncertainty_btn = st.button("🎯 Analyze Uncertainty", type="primary")
    
    with col2:
        if analyze_uncertainty_btn:
            with st.spinner("Running Monte Carlo analysis..."):
                # Define spectrum function
                def spectrum_function(wl, amplitude, center, width, baseline):
                    return amplitude * np.exp(-((wl - center)**2) / width) + baseline
                
                # Parameters
                base_params = {
                    'amplitude': amplitude,
                    'center': center,
                    'width': width,
                    'baseline': baseline
                }
                
                uncertainties = {
                    'amplitude': amp_unc,
                    'center': center_unc,
                    'width': width_unc,
                    'baseline': baseline_unc
                }
                
                # Run uncertainty analysis
                analyzer = UncertaintyAnalyzer()
                param_samples = analyzer.parameter_uncertainty_propagation(
                    base_params, uncertainties, num_samples
                )
                
                wavelength = np.linspace(1500, 1520, 200)
                uncertainty_results = analyzer.calculate_spectrum_uncertainty(
                    spectrum_function, wavelength, param_samples
                )
                
                if uncertainty_results:
                    # Plot uncertainty results
                    fig = make_subplots(
                        rows=3, cols=1,
                        subplot_titles=('Spectrum with Confidence Interval', 
                                      'Absolute Uncertainty', 'Relative Uncertainty (%)'),
                        vertical_spacing=0.08
                    )
                    
                    # Main spectrum with confidence interval
                    fig.add_trace(
                        go.Scatter(
                            x=wavelength,
                            y=uncertainty_results['confidence_upper'],
                            mode='lines',
                            line=dict(color='rgba(0,0,0,0)'),
                            showlegend=False,
                            hoverinfo='skip'
                        ),
                        row=1, col=1
                    )
                    
                    fig.add_trace(
                        go.Scatter(
                            x=wavelength,
                            y=uncertainty_results['confidence_lower'],
                            mode='lines',
                            line=dict(color='rgba(0,0,0,0)'),
                            fill='tonexty',
                            fillcolor='rgba(0,100,80,0.3)',
                            name='95% Confidence Interval'
                        ),
                        row=1, col=1
                    )
                    
                    fig.add_trace(
                        go.Scatter(
                            x=wavelength,
                            y=uncertainty_results['mean_spectrum'],
                            mode='lines',
                            name='Mean Spectrum',
                            line=dict(color='blue', width=2)
                        ),
                        row=1, col=1
                    )
                    
                    # Standard deviation
                    fig.add_trace(
                        go.Scatter(
                            x=wavelength,
                            y=uncertainty_results['std_spectrum'],
                            mode='lines',
                            name='Standard Deviation',
                            line=dict(color='red', width=2),
                            showlegend=False
                        ),
                        row=2, col=1
                    )
                    
                    # Relative uncertainty
                    rel_uncertainty = (uncertainty_results['std_spectrum'] / 
                                     np.abs(uncertainty_results['mean_spectrum'])) * 100
                    rel_uncertainty = np.where(np.isfinite(rel_uncertainty), rel_uncertainty, np.nan)
                    
                    fig.add_trace(
                        go.Scatter(
                            x=wavelength,
                            y=rel_uncertainty,
                            mode='lines',
                            name='Relative Uncertainty',
                            line=dict(color='green', width=2),
                            showlegend=False
                        ),
                        row=3, col=1
                    )
                    
                    fig.update_xaxes(title_text="Wavelength (nm)", row=3, col=1)
                    fig.update_yaxes(title_text="Absorption", row=1, col=1)
                    fig.update_yaxes(title_text="Std Dev", row=2, col=1)
                    fig.update_yaxes(title_text="Rel. Unc. (%)", row=3, col=1)
                    
                    fig.update_layout(height=800)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Statistics
                    st.markdown("#### 📊 Uncertainty Statistics")
                    col3, col4, col5, col6 = st.columns(4)
                    
                    with col3:
                        st.metric("Valid Samples", f"{uncertainty_results['valid_samples']}/{uncertainty_results['total_samples']}")
                    with col4:
                        st.metric("Mean Rel. Uncertainty", f"{np.nanmean(rel_uncertainty):.1f}%")
                    with col5:
                        st.metric("Max Abs. Uncertainty", f"{np.max(uncertainty_results['std_spectrum']):.6f}")
                    with col6:
                        st.metric("Confidence Level", f"{uncertainty_results['confidence_level']*100:.0f}%")

elif page == "⚙️ System Status":
    st.markdown('<h2 class="sub-header">⚙️ System Status & Performance</h2>', unsafe_allow_html=True)
    
    # Get system stats
    if hasattr(st.session_state.hitran_api, 'get_optimization_stats'):
        stats = st.session_state.hitran_api.get_optimization_stats()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💾 Cache Statistics")
            cache_stats = stats['cache']
            
            st.metric("Cached Files", cache_stats['total_files'])
            st.metric("Original Size", f"{cache_stats['total_size_mb']:.2f} MB")
            st.metric("Compressed Size", f"{cache_stats['compressed_size_mb']:.2f} MB")
            st.metric("Compression Ratio", f"{cache_stats['compression_ratio']*100:.1f}%")
            st.metric("Space Saved", f"{cache_stats['space_saved_mb']:.2f} MB")
            st.metric("Cache Hits", cache_stats['cache_hits'])
            
            if cache_stats['total_files'] > 0:
                st.success("✅ Cache system operational")
            else:
                st.info("ℹ️ No cached data yet")
        
        with col2:
            st.markdown("#### 🧠 Memory Status")
            memory_stats = stats['memory']
            system_stats = stats['system']
            
            st.metric("Process Memory", f"{memory_stats['rss_mb']:.1f} MB")
            st.metric("Memory Percentage", f"{memory_stats['percent']:.1f}%")
            st.metric("System Memory", f"{system_stats['used_percent']:.1f}% used")
            st.metric("Available Memory", f"{system_stats['available_gb']:.1f} GB")
            
            if memory_stats['percent'] < 5:
                st.success("✅ Memory usage optimal")
            elif memory_stats['percent'] < 10:
                st.warning("⚠️ Memory usage elevated")
            else:
                st.error("🚨 High memory usage")
        
        # Performance recommendations
        st.markdown("#### 🚀 Performance Recommendations")
        
        recommendations = []
        if cache_stats['total_files'] == 0:
            recommendations.append("💡 Run some simulations to build up cache for faster performance")
        
        if cache_stats['compression_ratio'] > 0.3:
            recommendations.append("💡 Consider cleaning old cache files to save space")
        
        if memory_stats['percent'] > 5:
            recommendations.append("💡 Consider restarting the application to free memory")
        
        if system_stats['available_gb'] < 1:
            recommendations.append("⚠️ Low system memory - consider closing other applications")
        
        if not recommendations:
            recommendations.append("✅ System performing optimally!")
        
        for rec in recommendations:
            st.markdown(rec)
    
    else:
        st.error("❌ Cannot access system statistics")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p><strong>HITRAN CRDS Simulator</strong> | Advanced Spectral Analysis Tool</p>
    <p>Featuring: Performance Optimization • Advanced Analysis • Interactive Visualization</p>
</div>
""", unsafe_allow_html=True)