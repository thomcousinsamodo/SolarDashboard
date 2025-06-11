# Legacy Solar Dashboard Files

This directory contains the original standalone solar dashboard and related development files that have been superseded by the main unified dashboard.

## Contents

### Original Solar Dashboard
- **`solar_dashboard.py`** - Original standalone solar energy dashboard (now integrated into main dashboard)
- **`weather_integration.py`** - Weather data integration module

### Debug and Development Files
- **`debug_*.py`** - Various debugging scripts used during dashboard development
- **`UNIFIED_DASHBOARD_*.md`** - Development documentation and fix logs

## Status

These files are kept for reference and debugging purposes but are no longer the primary dashboard implementation. 

**For current functionality, use `../dashboard.py` in the root directory.**

## Migration Notes

The solar energy functionality from `solar_dashboard.py` has been fully integrated into the main dashboard at `../dashboard.py`, which now provides:

- Solar energy monitoring and visualization
- Tariff period management and tracking  
- Unified interface combining both functionalities
- No code duplication - uses original tariff_tracker as a library

The main dashboard includes all chart types, date range controls, statistics, and features from the original solar dashboard. 