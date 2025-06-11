"""
Flask web dashboard for the Octopus Tariff Tracker.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime, date
import json
import os
from .timeline_manager import TimelineManager
from .models import TariffType, FlowDirection
from .logging_config import get_logger, setup_logging

app = Flask(__name__)
app.secret_key = 'octopus-tracker-secret-key'

# Initialize logging
setup_logging(log_level="INFO")
logger = get_logger('web_dashboard')

# Global timeline manager
manager = None

def get_manager():
    """Get or create timeline manager."""
    global manager
    if manager is None:
        manager = TimelineManager()
    return manager

@app.route('/')
def index():
    """Main dashboard page."""
    mgr = get_manager()
    summary = mgr.get_timeline_summary()
    validation = summary['validation']
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Octopus Tariff Tracker</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/"><i class="fas fa-bolt me-2"></i>Octopus Tariff Tracker</a>
                <div class="navbar-nav">
                    <a class="nav-link" href="/periods">Periods</a>
                    <a class="nav-link" href="/add-period">Add Period</a>
                    <a class="nav-link" href="/rate-lookup">Rate Lookup</a>
                </div>
            </div>
        </nav>
        
        <div class="container mt-4">
            <h1>Dashboard</h1>
            
            <div class="row">
                <div class="col-md-3">
                    <div class="card bg-primary text-white">
                        <div class="card-body">
                            <h5>Import Periods</h5>
                            <h2>{summary['import_periods']}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white">
                        <div class="card-body">
                            <h5>Export Periods</h5>
                            <h2>{summary['export_periods']}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-info text-white">
                        <div class="card-body">
                            <h5>Active Import</h5>
                            <h6>{summary['import_active'] or 'None'}</h6>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body">
                            <h5>Active Export</h5>
                            <h6>{summary['export_active'] or 'None'}</h6>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>Import Timeline Validation</h5>
                        </div>
                        <div class="card-body">
                            {'<div class="alert alert-success"><i class="fas fa-check"></i> No issues found</div>' 
                             if not any(validation['import'].values()) 
                             else '<div class="alert alert-warning"><i class="fas fa-exclamation-triangle"></i> Issues found</div>'}
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>Export Timeline Validation</h5>
                        </div>
                        <div class="card-body">
                            {'<div class="alert alert-success"><i class="fas fa-check"></i> No issues found</div>' 
                             if not any(validation['export'].values()) 
                             else '<div class="alert alert-warning"><i class="fas fa-exclamation-triangle"></i> Issues found</div>'}
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mt-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h5>Quick Actions</h5>
                        </div>
                        <div class="card-body">
                            <a href="/add-period" class="btn btn-primary me-2"><i class="fas fa-plus"></i> Add Period</a>
                            <a href="/periods" class="btn btn-secondary me-2"><i class="fas fa-list"></i> View Periods</a>
                            <a href="/rate-lookup" class="btn btn-info me-2"><i class="fas fa-search"></i> Rate Lookup</a>
                            <form style="display:inline" method="POST" action="/refresh-rates">
                                <button type="submit" class="btn btn-warning" onclick="return confirm('Refresh all rates?')">
                                    <i class="fas fa-sync"></i> Refresh Rates
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

@app.route('/periods')
def periods():
    """View all tariff periods."""
    mgr = get_manager()
    
    import_html = ""
    for idx, period in enumerate(mgr.config.import_timeline.periods):
        end_str = period.end_date.strftime('%Y-%m-%d') if period.end_date else 'Ongoing'
        import_html += f"""
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title">{period.display_name}</h5>
                    </div>
                    <button class="btn btn-outline-danger btn-sm" onclick="deletePeriod('import', {idx})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <p><strong>Period:</strong> {period.start_date} - {end_str}</p>
                <p><strong>Type:</strong> {period.tariff_type.value.title()}</p>
                <p><strong>Product:</strong> {period.product_code}</p>
                <p><strong>Rates:</strong> {len(period.rates)} loaded</p>
                <p><strong>Last Updated:</strong> {period.last_updated.strftime('%Y-%m-%d %H:%M') if period.last_updated else 'Never'}</p>
                {f'<p><small class="text-muted">{period.notes}</small></p>' if period.notes else ''}
            </div>
        </div>
        """
    
    export_html = ""
    for idx, period in enumerate(mgr.config.export_timeline.periods):
        end_str = period.end_date.strftime('%Y-%m-%d') if period.end_date else 'Ongoing'
        export_html += f"""
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title">{period.display_name}</h5>
                    </div>
                    <button class="btn btn-outline-danger btn-sm" onclick="deletePeriod('export', {idx})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <p><strong>Period:</strong> {period.start_date} - {end_str}</p>
                <p><strong>Type:</strong> {period.tariff_type.value.title()}</p>
                <p><strong>Product:</strong> {period.product_code}</p>
                <p><strong>Rates:</strong> {len(period.rates)} loaded</p>
                <p><strong>Last Updated:</strong> {period.last_updated.strftime('%Y-%m-%d %H:%M') if period.last_updated else 'Never'}</p>
                {f'<p><small class="text-muted">{period.notes}</small></p>' if period.notes else ''}
            </div>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tariff Periods - Octopus Tariff Tracker</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/"><i class="fas fa-bolt me-2"></i>Octopus Tariff Tracker</a>
                <div class="navbar-nav">
                    <a class="nav-link active" href="/periods">Periods</a>
                    <a class="nav-link" href="/add-period">Add Period</a>
                    <a class="nav-link" href="/rate-lookup">Rate Lookup</a>
                </div>
            </div>
        </nav>
        
        <div class="container mt-4">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1><i class="fas fa-clock me-2"></i>Tariff Periods</h1>
                <div>
                    <button class="btn btn-success me-2" onclick="refreshAllRates()">
                        <i class="fas fa-sync-alt me-2"></i>Refresh All Rates
                    </button>
                    <a href="/add-period" class="btn btn-primary"><i class="fas fa-plus me-2"></i>Add Period</a>
                </div>
            </div>
            
            <div class="row">
                <div class="col-lg-6">
                    <h3>Import Periods</h3>
                    {import_html if import_html else '<p>No import periods configured.</p>'}
                </div>
                <div class="col-lg-6">
                    <h3>Export Periods</h3>
                    {export_html if export_html else '<p>No export periods configured.</p>'}
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
        function refreshAllRates() {{
            if (confirm('This will refresh rates for all periods. This may take some time. Continue?')) {{
                const button = event.target;
                const originalText = button.innerHTML;
                button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Refreshing...';
                button.disabled = true;
                
                fetch('/api/refresh-rates', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }}
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        alert('All rates refreshed successfully!');
                        location.reload();
                    }} else {{
                        alert('Error refreshing rates: ' + data.message);
                        button.innerHTML = originalText;
                        button.disabled = false;
                    }}
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    alert('Error refreshing rates: ' + error.message);
                    button.innerHTML = originalText;
                    button.disabled = false;
                }});
            }}
        }}
        
        function deletePeriod(flowDirection, periodIndex) {{
            if (confirm('Are you sure you want to delete this period? This action cannot be undone.')) {{
                fetch('/api/delete-period', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        flow_direction: flowDirection,
                        period_index: periodIndex
                    }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        alert('Period deleted successfully!');
                        location.reload();
                    }} else {{
                        alert('Error deleting period: ' + data.message);
                    }}
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    alert('Error deleting period: ' + error.message);
                }});
            }}
        }}
        </script>
    </body>
    </html>
    """

@app.route('/add-period')
def add_period_form():
    """Show form to add a new period."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Add Period - Octopus Tariff Tracker</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/"><i class="fas fa-bolt me-2"></i>Octopus Tariff Tracker</a>
                <div class="navbar-nav">
                    <a class="nav-link" href="/periods">Periods</a>
                    <a class="nav-link active" href="/add-period">Add Period</a>
                    <a class="nav-link" href="/rate-lookup">Rate Lookup</a>
                </div>
            </div>
        </nav>
        
        <div class="container mt-4">
            <h1><i class="fas fa-plus me-2"></i>Add Tariff Period</h1>
            
            <form method="POST">
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="flow_direction" class="form-label">Flow Direction</label>
                            <select class="form-select" id="flow_direction" name="flow_direction" required onchange="loadTariffs()">
                                <option value="import">Import</option>
                                <option value="export">Export</option>
                            </select>
                        </div>
                        
                        <div class="mb-3">
                            <label for="tariff_type" class="form-label">Tariff Type</label>
                            <select class="form-select" id="tariff_type" name="tariff_type" required onchange="filterByTariffType()">
                                <option value="">All types</option>
                                <option value="fixed">Fixed</option>
                                <option value="variable">Variable</option>
                                <option value="agile">Agile</option>
                                <option value="economy7">Economy 7 (Manual Entry)</option>
                                <option value="go">Octopus Go</option>
                            </select>
                            <div class="form-text">Filter available tariffs by type. Economy 7 requires manual rate entry.</div>
                        </div>
                        
                        <div class="mb-3">
                            <label for="available_tariffs" class="form-label">Available Tariffs</label>
                            <select class="form-select" id="available_tariffs" onchange="selectTariff()">
                                <option value="">Loading tariffs...</option>
                            </select>
                            <div class="form-text">Select from available Octopus Energy tariffs</div>
                        </div>
                        
                        <div class="mb-3">
                            <label for="display_name" class="form-label">Display Name</label>
                            <input type="text" class="form-control" id="display_name" name="display_name" required>
                        </div>
                        
                        <div class="mb-3">
                            <label for="product_code" class="form-label">Product Code</label>
                            <input type="text" class="form-control" id="product_code" name="product_code" required>
                            <div class="form-text">Auto-filled from tariff selection, or enter manually</div>
                        </div>
                        
                        <!-- Manual Economy 7 Rate Entry (hidden by default) -->
                        <div id="economy7_manual_rates" style="display: none;">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                <strong id="manual_entry_title">Economy 7 Manual Entry:</strong> <span id="manual_entry_text">Since historical Economy 7 data is not available via API, please enter the day and night rates manually.</span>
                            </div>
                            
                            <div class="row" id="vat_controls_row">
                                <div class="col-md-4">
                                    <div class="mb-3">
                                        <label for="vat_rate" class="form-label">VAT Rate (%)</label>
                                        <input type="number" step="0.1" class="form-control" id="vat_rate" name="vat_rate" value="20" onchange="calculateVAT()">
                                        <div class="form-text">UK standard VAT is 20%</div>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="mb-3">
                                        <label for="rate_basis" class="form-label">Rates Include VAT?</label>
                                        <select class="form-select" id="rate_basis" name="rate_basis" onchange="calculateVAT()">
                                            <option value="inc_vat">Yes - inc VAT</option>
                                            <option value="exc_vat">No - exc VAT</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label for="day_rate_input" class="form-label">Day Rate (p/kWh)</label>
                                        <input type="number" step="0.001" class="form-control" id="day_rate_input" name="day_rate_input" onchange="calculateVAT()">
                                        <div class="form-text">
                                            <span id="day_rate_calculated"></span>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label for="night_rate_input" class="form-label">Night Rate (p/kWh)</label>
                                        <input type="number" step="0.001" class="form-control" id="night_rate_input" name="night_rate_input" onchange="calculateVAT()">
                                        <div class="form-text">
                                            <span id="night_rate_calculated"></span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label for="standing_charge_input" class="form-label">Standing Charge (p/day)</label>
                                        <input type="number" step="0.001" class="form-control" id="standing_charge_input" name="standing_charge_input" onchange="calculateVAT()">
                                        <div class="form-text">
                                            <span id="standing_charge_calculated"></span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Hidden fields for calculated values -->
                            <input type="hidden" id="day_rate_exc_vat" name="day_rate_exc_vat">
                            <input type="hidden" id="day_rate_inc_vat" name="day_rate_inc_vat">
                            <input type="hidden" id="night_rate_exc_vat" name="night_rate_exc_vat">
                            <input type="hidden" id="night_rate_inc_vat" name="night_rate_inc_vat">
                            <input type="hidden" id="standing_charge_exc_vat" name="standing_charge_exc_vat">
                            <input type="hidden" id="standing_charge_inc_vat" name="standing_charge_inc_vat">
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="start_date" class="form-label">Start Date</label>
                            <input type="date" class="form-control" id="start_date" name="start_date" required>
                        </div>
                        
                        <div class="mb-3">
                            <label for="end_date" class="form-label">End Date (Optional)</label>
                            <input type="date" class="form-control" id="end_date" name="end_date">
                            <div class="form-text">Leave blank for ongoing periods</div>
                        </div>
                        
                        <div class="mb-3">
                            <label for="region" class="form-label">Region</label>
                            <select class="form-select" id="region" name="region">
                                <option value="A">Eastern England (A)</option>
                                <option value="B">East Midlands (B)</option>
                                <option value="C" selected>London (C)</option>
                                <option value="D">Merseyside and North Wales (D)</option>
                                <option value="E">West Midlands (E)</option>
                                <option value="F">North East England (F)</option>
                                <option value="G">North West England (G)</option>
                                <option value="H">Southern England (H)</option>
                                <option value="J">South East England (J)</option>
                                <option value="K">South Wales (K)</option>
                                <option value="L">South West England (L)</option>
                                <option value="M">Yorkshire (M)</option>
                                <option value="N">South Scotland (N)</option>
                                <option value="P">North Scotland (P)</option>
                            </select>
                        </div>
                        
                        <div class="mb-3">
                            <label for="notes" class="form-label">Notes</label>
                            <textarea class="form-control" id="notes" name="notes" rows="3"></textarea>
                        </div>
                    </div>
                </div>
                
                <div class="mb-3">
                    <button type="submit" class="btn btn-primary" id="addPeriodBtn">Add Period</button>
                    <a href="/periods" class="btn btn-secondary">Cancel</a>
                </div>
            </form>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
        let availableProducts = [];
        
        // Load tariffs when page loads
        document.addEventListener('DOMContentLoaded', function() {
            loadTariffs();
        });
        
        function loadTariffs() {
            const flowDirection = document.getElementById('flow_direction').value;
            const tariffSelect = document.getElementById('available_tariffs');
            
            // Show loading
            tariffSelect.innerHTML = '<option value="">Loading tariffs...</option>';
            
            fetch('/api/available-tariffs?flow=' + flowDirection)
                .then(response => response.json())
                .then(data => {
                    availableProducts = data.products;
                    populateTariffDropdown(data.products);
                })
                .catch(error => {
                    console.error('Error loading tariffs:', error);
                    tariffSelect.innerHTML = '<option value="">Error loading tariffs</option>';
                });
        }
        
        function populateTariffDropdown(products) {
            const tariffSelect = document.getElementById('available_tariffs');
            const selectedTariffType = document.getElementById('tariff_type').value;
            
            tariffSelect.innerHTML = '<option value="">Select a tariff...</option>';
            
            // Filter products based on selected tariff type
            let filteredProducts = products;
            if (selectedTariffType) {
                filteredProducts = products.filter(product => 
                    product.detected_tariff_type === selectedTariffType
                );
            }
            
            if (filteredProducts.length === 0 && selectedTariffType) {
                tariffSelect.innerHTML = '<option value="">No tariffs available for selected type</option>';
                return;
            }
            
            filteredProducts.forEach(product => {
                const option = document.createElement('option');
                option.value = product.code;
                option.textContent = `${product.display_name} (${product.code}) [${product.detected_tariff_type}]`;
                option.dataset.fullName = product.full_name;
                option.dataset.direction = product.direction;
                option.dataset.brand = product.brand;
                option.dataset.detectedType = product.detected_tariff_type;
                tariffSelect.appendChild(option);
            });
        }
        
        function selectTariff() {
            const tariffSelect = document.getElementById('available_tariffs');
            const selectedOption = tariffSelect.options[tariffSelect.selectedIndex];
            
            if (selectedOption.value) {
                // Auto-fill product code
                document.getElementById('product_code').value = selectedOption.value;
                
                // Auto-fill display name if empty
                const displayNameField = document.getElementById('display_name');
                if (!displayNameField.value) {
                    displayNameField.value = selectedOption.dataset.fullName || selectedOption.textContent.split(' (')[0];
                }
                
                // Auto-set tariff type based on detected type
                const detectedType = selectedOption.dataset.detectedType;
                if (detectedType) {
                    document.getElementById('tariff_type').value = detectedType;
                }
            }
        }
        
        function filterByTariffType() {
            const selectedType = document.getElementById('tariff_type').value;
            const flowDirection = document.getElementById('flow_direction').value;
            const manualRatesDiv = document.getElementById('economy7_manual_rates');
            const availableTariffsDiv = document.querySelector('.mb-3:has(#available_tariffs)');
            
            // Check if manual entry is needed
            const needsManualEntry = selectedType === 'economy7' || flowDirection === 'export';
            
            if (needsManualEntry) {
                // Show manual entry fields
                manualRatesDiv.style.display = 'block';
                // Hide available tariffs dropdown since manual entry is required
                availableTariffsDiv.style.display = 'none';
                // Clear and disable tariff selection
                document.getElementById('available_tariffs').value = '';
                
                // Make manual entry fields required
                document.getElementById('day_rate_input').required = true;
                document.getElementById('standing_charge_input').required = true;
                
                // Update UI text based on reason for manual entry
                if (selectedType === 'economy7') {
                    document.getElementById('manual_entry_title').textContent = 'Economy 7 Manual Entry:';
                    document.getElementById('manual_entry_text').textContent = 'Since historical Economy 7 data is not available via API, please enter the day and night rates manually.';
                    document.getElementById('product_code').value = 'MANUAL-ECONOMY7-' + new Date().toISOString().split('T')[0];
                    // Show night rate field for Economy 7
                    document.querySelector('label[for="night_rate_input"]').parentElement.parentElement.style.display = 'block';
                    document.getElementById('night_rate_input').required = true;
                } else if (flowDirection === 'export') {
                    document.getElementById('manual_entry_title').textContent = 'Export Tariff Manual Entry:';
                    document.getElementById('manual_entry_text').textContent = 'Export tariff rates are not available via the public API. Please enter rates manually if known, or leave blank to add rates later.';
                    document.getElementById('product_code').value = 'MANUAL-EXPORT-' + new Date().toISOString().split('T')[0];
                    // Hide night rate field for export (single rate)
                    document.querySelector('label[for="night_rate_input"]').parentElement.parentElement.style.display = 'none';
                    document.getElementById('night_rate_input').required = false;
                    
                    // Hide standing charge field for export (no standing charges)
                    document.querySelector('label[for="standing_charge_input"]').parentElement.style.display = 'none';
                    document.getElementById('standing_charge_input').required = false;
                    
                    // Hide VAT controls for exports (VAT doesn't apply to exports)
                    document.getElementById('vat_controls_row').style.display = 'none';
                    // Set defaults for exports
                    document.getElementById('vat_rate').value = '0';
                    document.getElementById('rate_basis').value = 'exc_vat';
                }
                
                document.getElementById('product_code').readOnly = true;
                // Initialize VAT calculations
                calculateVAT();
            } else {
                // Hide manual entry fields
                manualRatesDiv.style.display = 'none';
                // Show available tariffs dropdown
                availableTariffsDiv.style.display = 'block';
                // Re-enable product code field
                document.getElementById('product_code').readOnly = false;
                // Show night rate field for normal cases
                document.querySelector('label[for="night_rate_input"]').parentElement.parentElement.style.display = 'block';
                
                // Show standing charge field for non-export tariffs
                document.querySelector('label[for="standing_charge_input"]').parentElement.style.display = 'block';
                
                // Show VAT controls for non-export tariffs
                document.getElementById('vat_controls_row').style.display = 'flex';
                // Restore VAT defaults
                document.getElementById('vat_rate').value = '20';
                document.getElementById('rate_basis').value = 'inc_vat';
                
                // Remove required from manual entry fields when hidden
                document.getElementById('day_rate_input').required = false;
                document.getElementById('night_rate_input').required = false;
                document.getElementById('standing_charge_input').required = false;
                
                // Re-populate dropdown when tariff type changes
                populateTariffDropdown(availableProducts);
            }
        }
        
        // Also trigger when flow direction changes
        document.getElementById('flow_direction').addEventListener('change', filterByTariffType);
        
        function calculateVAT() {
            const flowDirection = document.getElementById('flow_direction').value;
            const vatRate = parseFloat(document.getElementById('vat_rate').value) || 20;
            const rateBasis = document.getElementById('rate_basis').value;
            const vatMultiplier = vatRate / 100;
            
            const dayRateInput = parseFloat(document.getElementById('day_rate_input').value) || 0;
            const nightRateInput = parseFloat(document.getElementById('night_rate_input').value) || 0;
            const standingChargeInput = parseFloat(document.getElementById('standing_charge_input').value) || 0;
            
            let dayRateExcVat, dayRateIncVat, nightRateExcVat, nightRateIncVat;
            let standingChargeExcVat, standingChargeIncVat;
            
            // For export rates, no VAT applies (they are sales, not purchases)
            if (flowDirection === 'export') {
                dayRateExcVat = dayRateInput;
                dayRateIncVat = dayRateInput;  // Same value since no VAT
                nightRateExcVat = nightRateInput;
                nightRateIncVat = nightRateInput;
                // Export tariffs don't have standing charges
                standingChargeExcVat = 0;
                standingChargeIncVat = 0;
            } else {
            
                if (rateBasis === 'inc_vat') {
                    // User entered inc VAT values, calculate exc VAT
                    dayRateExcVat = dayRateInput / (1 + vatMultiplier);
                    dayRateIncVat = dayRateInput;
                    nightRateExcVat = nightRateInput / (1 + vatMultiplier);
                    nightRateIncVat = nightRateInput;
                    standingChargeExcVat = standingChargeInput / (1 + vatMultiplier);
                    standingChargeIncVat = standingChargeInput;
                } else {
                    // User entered exc VAT values, calculate inc VAT
                    dayRateExcVat = dayRateInput;
                    dayRateIncVat = dayRateInput * (1 + vatMultiplier);
                    nightRateExcVat = nightRateInput;
                    nightRateIncVat = nightRateInput * (1 + vatMultiplier);
                    standingChargeExcVat = standingChargeInput;
                    standingChargeIncVat = standingChargeInput * (1 + vatMultiplier);
                }
            }
            
            // Update hidden fields
            document.getElementById('day_rate_exc_vat').value = dayRateExcVat.toFixed(3);
            document.getElementById('day_rate_inc_vat').value = dayRateIncVat.toFixed(3);
            document.getElementById('night_rate_exc_vat').value = nightRateExcVat.toFixed(3);
            document.getElementById('night_rate_inc_vat').value = nightRateIncVat.toFixed(3);
            document.getElementById('standing_charge_exc_vat').value = standingChargeExcVat.toFixed(3);
            document.getElementById('standing_charge_inc_vat').value = standingChargeIncVat.toFixed(3);
            
            // Update display text
            if (flowDirection === 'export') {
                // For exports, don't show VAT calculations and no standing charges
                document.getElementById('day_rate_calculated').textContent = `(No VAT applies to exports)`;
                document.getElementById('night_rate_calculated').textContent = `(No VAT applies to exports)`;
                // Don't update standing charge text for exports since field is hidden
            } else if (rateBasis === 'inc_vat') {
                document.getElementById('day_rate_calculated').textContent = `Exc VAT: ${dayRateExcVat.toFixed(3)}p`;
                document.getElementById('night_rate_calculated').textContent = `Exc VAT: ${nightRateExcVat.toFixed(3)}p`;
                document.getElementById('standing_charge_calculated').textContent = `Exc VAT: ${standingChargeExcVat.toFixed(3)}p`;
            } else {
                document.getElementById('day_rate_calculated').textContent = `Inc VAT: ${dayRateIncVat.toFixed(3)}p`;
                document.getElementById('night_rate_calculated').textContent = `Inc VAT: ${nightRateIncVat.toFixed(3)}p`;
                document.getElementById('standing_charge_calculated').textContent = `Inc VAT: ${standingChargeIncVat.toFixed(3)}p`;
            }
        }
        
        // Add form submission debugging
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.querySelector('form');
            const addButton = document.getElementById('addPeriodBtn');
            
            if (form && addButton) {
                // Debug form submission
                form.addEventListener('submit', function(e) {
                    console.log('Form submission attempted');
                    
                    // Check for validation issues
                    const requiredFields = form.querySelectorAll('[required]');
                    let hasErrors = false;
                    
                    requiredFields.forEach(field => {
                        if (!field.value.trim()) {
                            console.log('Missing required field:', field.name || field.id);
                            field.style.border = '2px solid red';
                            hasErrors = true;
                        } else {
                            field.style.border = '';
                        }
                    });
                    
                    if (hasErrors) {
                        e.preventDefault();
                        alert('Please fill in all required fields');
                        return false;
                    }
                    
                    // Log form data being submitted
                    const formData = new FormData(form);
                    console.log('Form data being submitted:');
                    for (let [key, value] of formData.entries()) {
                        console.log(key + ':', value);
                    }
                    
                    // Disable button to prevent double submission
                    addButton.disabled = true;
                    addButton.textContent = 'Adding...';
                });
                
                // Re-enable button if user navigates back
                window.addEventListener('pageshow', function() {
                    addButton.disabled = false;
                    addButton.textContent = 'Add Period';
                });
            }
        });
        </script>
    </body>
    </html>
    """

@app.route('/add-period', methods=['POST'])
def add_period():
    """Add a new tariff period."""
    try:
        mgr = get_manager()
        
        # Log the received form data for debugging
        logger.info(f"Add period form data: {dict(request.form)}")
        
        flow_direction = request.form['flow_direction']
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form['end_date'] else None
        product_code = request.form['product_code']
        display_name = request.form['display_name']
        tariff_type = TariffType(request.form['tariff_type'])
        region = request.form.get('region', 'C')
        notes = request.form.get('notes', '')
        
        logger.info(f"Creating {flow_direction} period: {display_name} ({tariff_type.value}) for product {product_code}")
        
        if flow_direction == 'import':
            period = mgr.add_import_period(
                start_date, end_date, product_code, display_name,
                tariff_type, region, notes
            )
        else:
            period = mgr.add_export_period(
                start_date, end_date, product_code, display_name,
                tariff_type, region, notes
            )
        
        # Handle rate fetching based on tariff type and flow direction
        if tariff_type == TariffType.ECONOMY7:
            # Handle manual Economy 7 rate entry (already in pence)
            try:
                manual_rates = {
                    'day_rate_exc_vat': float(request.form.get('day_rate_exc_vat', 0)),  # Already in pence
                    'day_rate_inc_vat': float(request.form.get('day_rate_inc_vat', 0)),
                    'night_rate_exc_vat': float(request.form.get('night_rate_exc_vat', 0)),
                    'night_rate_inc_vat': float(request.form.get('night_rate_inc_vat', 0)),
                    'standing_charge_exc_vat': float(request.form.get('standing_charge_exc_vat', 0)),
                    'standing_charge_inc_vat': float(request.form.get('standing_charge_inc_vat', 0)),
                }
                
                # Store manual Economy 7 rates
                mgr.store_manual_economy7_rates(period, manual_rates)
                logger.info(f"Successfully stored manual Economy 7 rates for {display_name}")
                
            except ValueError as e:
                logger.error(f"Invalid manual rate values: {e}")
                return f"Error: Invalid rate values provided", 400
        elif flow_direction == 'export':
            # Export tariffs require manual entry (not available via API)
            if request.form.get('day_rate_exc_vat'):  # Check if manual rates were provided
                try:
                    # Store in pence to match API rate units
                    export_rate = float(request.form.get('day_rate_exc_vat', 0))
                    
                    manual_rates = {
                        'day_rate_exc_vat': export_rate,  # Reuse day_rate as export_rate
                        'day_rate_inc_vat': export_rate,  # Same as exc_vat since no VAT on exports
                        # No standing charges for export tariffs
                    }
                    
                    # Store manual export rates
                    mgr.store_manual_export_rates(period, manual_rates)
                    logger.info(f"Successfully stored manual export rates for {display_name}")
                    
                except ValueError as e:
                    logger.error(f"Invalid manual export rate values: {e}")
                    return f"Error: Invalid rate values provided", 400
            else:
                # No manual rates provided for export - just create period without rates
                logger.info(f"Export period created without rates (manual entry required): {display_name}")
        else:
            # Use API for import tariff types (except Economy 7)
            try:
                mgr.fetch_rates_for_period(period)
                logger.info(f"Successfully fetched API rates for {display_name}")
            except Exception as e:
                logger.error(f"Failed to fetch API rates for {display_name}: {e}")
                # Continue anyway - period will be created without rates
                # User can manually add rates or try refreshing later
        
        mgr.save_config()
        return redirect('/periods')
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error adding period: {e}\nFull traceback:\n{error_details}")
        
        # Create a proper error page instead of just returning text
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - Octopus Tariff Tracker</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-4">
                <div class="alert alert-danger">
                    <h4>Error Adding Period</h4>
                    <p><strong>Error:</strong> {str(e)}</p>
                    <p><a href="/add-period" class="btn btn-primary">Try Again</a></p>
                </div>
            </div>
        </body>
        </html>
        """, 400

@app.route('/rate-lookup')
def rate_lookup_form():
    """Show rate lookup form."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rate Lookup - Octopus Tariff Tracker</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/"><i class="fas fa-bolt me-2"></i>Octopus Tariff Tracker</a>
                <div class="navbar-nav">
                    <a class="nav-link" href="/periods">Periods</a>
                    <a class="nav-link" href="/add-period">Add Period</a>
                    <a class="nav-link active" href="/rate-lookup">Rate Lookup</a>
                </div>
            </div>
        </nav>
        
        <div class="container mt-4">
            <h1><i class="fas fa-search me-2"></i>Rate Lookup</h1>
            
            <div class="row">
                <div class="col-md-6">
                    <form id="rateLookupForm">
                        <div class="mb-3">
                            <label for="datetime" class="form-label">Date & Time</label>
                            <input type="datetime-local" class="form-control" id="datetime" name="datetime" required>
                        </div>
                        
                        <div class="mb-3">
                            <label for="flow_direction" class="form-label">Flow Direction</label>
                            <select class="form-select" id="flow_direction" name="flow_direction">
                                <option value="import">Import</option>
                                <option value="export">Export</option>
                            </select>
                        </div>
                        
                        <div class="mb-3">
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                <strong>Smart Rate Detection:</strong> The system automatically determines the correct rate type (standard/day/night) based on the time and active tariff.
                            </div>
                        </div>
                        
                        <button type="submit" class="btn btn-primary">Lookup Rate</button>
                    </form>
                </div>
                
                <div class="col-md-6">
                    <div id="result" class="card" style="display: none;">
                        <div class="card-body">
                            <h5 class="card-title">Rate Result</h5>
                            <div id="resultContent"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
        document.getElementById('rateLookupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                datetime: document.getElementById('datetime').value,
                flow_direction: document.getElementById('flow_direction').value
            };
            
            fetch('/api/rate-lookup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                const resultDiv = document.getElementById('result');
                const contentDiv = document.getElementById('resultContent');
                
                if (data.success) {
                    let rateHtml = '';
                    if (data.rate.is_export) {
                        // Export rates don't have VAT
                        rateHtml = `<p><strong>Rate:</strong> ${data.rate.value}p/kWh</p>`;
                    } else {
                        // Import rates show both inc and exc VAT
                        rateHtml = `
                            <p><strong>Rate:</strong> ${data.rate.value_inc_vat}p/kWh (inc VAT)</p>
                            <p><strong>Rate:</strong> ${data.rate.value_exc_vat}p/kWh (exc VAT)</p>
                        `;
                    }
                    
                    contentDiv.innerHTML = `
                        ${rateHtml}
                        <p><strong>Valid From:</strong> ${new Date(data.rate.valid_from).toLocaleString()}</p>
                        <p><strong>Valid To:</strong> ${data.rate.valid_to ? new Date(data.rate.valid_to).toLocaleString() : 'Ongoing'}</p>
                        <p><strong>Rate Type:</strong> ${data.rate.rate_type}</p>
                    `;
                    resultDiv.className = 'card border-success';
                } else {
                    contentDiv.innerHTML = `<p class="text-danger">${data.message}</p>`;
                    resultDiv.className = 'card border-danger';
                }
                
                resultDiv.style.display = 'block';
            })
            .catch(error => {
                console.error('Error:', error);
                const resultDiv = document.getElementById('result');
                const contentDiv = document.getElementById('resultContent');
                contentDiv.innerHTML = '<p class="text-danger">Error performing lookup</p>';
                resultDiv.className = 'card border-danger';
                resultDiv.style.display = 'block';
            });
        });
        </script>
    </body>
    </html>
    """

@app.route('/api/rate-lookup', methods=['POST'])
def api_rate_lookup():
    """API endpoint for rate lookup."""
    try:
        from zoneinfo import ZoneInfo
        
        mgr = get_manager()
        
        datetime_str = request.json['datetime']
        flow_direction = FlowDirection(request.json['flow_direction'])
        
        # Parse the datetime string as UK local time first
        dt = datetime.fromisoformat(datetime_str)
        
        # If the datetime is naive (no timezone), assume it's UK local time
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo('Europe/London'))
        
        rate = mgr.get_rate_at_datetime(dt, flow_direction)  # Auto-detect rate type
        
        if rate:
            # For export rates, VAT doesn't apply (no VAT on energy sales)
            if flow_direction == FlowDirection.EXPORT:
                return jsonify({
                    'success': True,
                    'rate': {
                        'value': rate.value_exc_vat,  # Already in pence from API
                        'valid_from': rate.valid_from.isoformat(),
                        'valid_to': rate.valid_to.isoformat() if rate.valid_to else None,
                        'rate_type': rate.rate_type,
                        'is_export': True
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'rate': {
                        'value_inc_vat': rate.value_inc_vat,  # Already in pence from API
                        'value_exc_vat': rate.value_exc_vat,  # Already in pence from API
                        'valid_from': rate.valid_from.isoformat(),
                        'valid_to': rate.valid_to.isoformat() if rate.valid_to else None,
                        'rate_type': rate.rate_type,
                        'is_export': False
                    }
                })
        else:
            return jsonify({
                'success': False,
                'message': 'No rate found for the specified datetime'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@app.route('/api/available-tariffs')
def api_available_tariffs():
    """API endpoint for fetching available tariffs."""
    try:
        mgr = get_manager()
        flow_direction = request.args.get('flow', 'import')
        
        # Get all products from Octopus API
        products_response = mgr.api_client.get_products()
        all_products = products_response.get('results', [])
        
        # Filter products based on flow direction and detect tariff types
        filtered_products = []
        
        for product in all_products:
            product_code = product['code'].lower()
            display_name = product['display_name']
            
            # Determine if this is an import or export product
            is_export = any(keyword in product_code for keyword in ['outgoing', 'export', 'feed-in', 'flux-export'])
            is_import = not is_export
            
            # Filter based on requested flow direction
            if (flow_direction == 'import' and is_import) or (flow_direction == 'export' and is_export):
                # Only include products that are available to new customers or don't have availability restriction
                available_to = product.get('available_to')
                if available_to is None or available_to > datetime.now().isoformat():
                    # Detect tariff type for this product
                    try:
                        detected_type = mgr.api_client.detect_tariff_type(product['code'])
                    except Exception as e:
                        logger.warning(f"Could not detect tariff type for {product['code']}: {e}")
                        # Fallback to pattern matching
                        code_lower = product['code'].lower()
                        if "agile" in code_lower:
                            detected_type = "agile"
                        elif "go" in code_lower:
                            detected_type = "go"
                        elif "fix" in code_lower:
                            detected_type = "fixed"
                        else:
                            detected_type = "variable"
                    
                    filtered_products.append({
                        'code': product['code'],
                        'display_name': display_name,
                        'full_name': product['full_name'],
                        'direction': 'export' if is_export else 'import',
                        'brand': product.get('brand', 'octopus'),
                        'available_from': product.get('available_from'),
                        'available_to': available_to,
                        'detected_tariff_type': detected_type
                    })
        
        # Sort by display name for better UX
        filtered_products.sort(key=lambda x: x['display_name'])
        
        return jsonify({
            'success': True,
            'products': filtered_products,
            'count': len(filtered_products)
        })
        
    except Exception as e:
        logger.error(f"Error fetching available tariffs: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'products': []
        }), 400

@app.route('/api/refresh-rates', methods=['POST'])
def api_refresh_rates():
    """API endpoint to refresh rates for all periods."""
    try:
        mgr = get_manager()
        mgr.refresh_all_rates()
        return jsonify({'success': True, 'message': 'All rates refreshed successfully'})
    except Exception as e:
        logger.error(f"Error refreshing rates: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/delete-period', methods=['POST'])
def api_delete_period():
    """API endpoint to delete a specific period."""
    try:
        mgr = get_manager()
        data = request.get_json()
        flow_direction = FlowDirection(data['flow_direction'])
        period_index = int(data['period_index'])
        
        success = mgr.delete_period(flow_direction, period_index)
        
        if success:
            return jsonify({'success': True, 'message': 'Period deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete period - invalid index'}), 400
            
    except Exception as e:
        logger.error(f"Error deleting period: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/refresh-rates', methods=['POST'])
def refresh_rates():
    """Refresh rates for all periods."""
    try:
        mgr = get_manager()
        mgr.refresh_all_rates()
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error refreshing rates: {e}")
        return f"Error refreshing rates: {str(e)}", 400

if __name__ == '__main__':
    print("🐙 Starting Octopus Tariff Tracker Web Dashboard...")
    print("Dashboard will be available at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000) 