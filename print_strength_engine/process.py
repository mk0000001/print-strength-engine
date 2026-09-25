"""Preserve process context without inventing a calibrated strength transfer."""
from math import isfinite
from copy import deepcopy
import re
from .evidence import literature_comparisons

VERSION='GCODE_PROCESS_EVIDENCE_V3_THERMAL_CONTEXT'
AXES=('X','Y','Z')


def number(value,low,high):
    if isinstance(value,(list,tuple)):
        value=value[0] if value else None
    try:value=float(str(value).split(',')[0].strip().rstrip('%'))
    except (TypeError,ValueError):return None
    return value if isfinite(value) and low<=value<=high else None


def numeric_values(value, low, high):
    """Preserve per-tool slots, including invalid entries; no first-tool proxy."""
    values=value if isinstance(value,(list,tuple)) else re.split('[,;]',str(value)) if value is not None else []
    return [number(item,low,high) for item in values]


def uniform(values):
    return values[0] if values and values[0] is not None and all(v==values[0] for v in values) else None


def settings(analysis):
    """Only values the scanner actually read from the file; never slicer defaults."""
    analysis=analysis or {}
    config=analysis.get('configuration') or {}
    metrics=analysis.get('process_metrics') or {}
    speeds=metrics.get('commanded_speed_mm_s') or {}
    def first(*keys):
        return next((config[k] for k in keys if config.get(k) not in (None,'')),None)
    detected=analysis.get('detected_materials')
    family_value=detected if detected else first('filament_type','material_family')
    family_values=family_value if isinstance(family_value,(list,tuple)) else [family_value]
    families={part.strip(' \"').upper() for value in family_values if value is not None
              for part in re.split('[,;]',str(value)) if part.strip(' \"')}
    family=next(iter(families)) if len(families)==1 else None
    width=next((value for key in ('outer_wall_line_width','external_perimeter_extrusion_width','line_width','extrusion_width')
                if '%' not in str(config.get(key)) and (value:=number(config.get(key),.05,3)) is not None),None)
    width_source='GCODE_LINE_WIDTH'
    if width is None:
        width=number(config.get('nozzle_diameter'),.05,3) or number(analysis.get('nozzle_diameter_mm'),.05,3)
        width_source='NOZZLE_DIAMETER_ASSUMPTION' if width is not None else 'UNKNOWN'
    temperatures=numeric_values(first('nozzle_temperature','temperature'),50,600)
    bed_temperatures=numeric_values(first('bed_temperature'),0,300)
    flows=numeric_values(first('filament_flow_ratio','extrusion_multiplier'),0,5)
    return {'infill_percent':number(first('sparse_infill_density','fill_density'),0,100),
            'pattern':(str(config.get('sparse_infill_pattern') or config.get('fill_pattern') or '').strip().lower() or None),
            'walls':number(first('wall_loops','perimeters'),0,40),
            'line_width_mm':width,'line_width_source':width_source,
            'layer_height_mm':number(config.get('layer_height') or config.get('first_layer_height'),.01,3),
            'speed_mm_s':number(speeds.get('p50_approx'),1,2000),
            'nozzle_c':uniform(temperatures),'nozzle_temperatures_c':temperatures,
            'bed_c':uniform(bed_temperatures),'bed_temperatures_c':bed_temperatures,
            'flow_ratio':uniform(flows),'flow_ratios':flows,
            'top_shell_layers':number(first('top_shell_layers','top_solid_layers'),0,1000),
            'bottom_shell_layers':number(first('bottom_shell_layers','bottom_solid_layers'),0,1000),
            'minimum_layer_time_setting_s':number(first('slow_down_layer_time','min_layer_time'),0,86400),
            # Slicer setpoints and duration/layer count cannot establish local heat history.
            'local_interlayer_return_time_s':None,
            'measured_substrate_temperature_c':None,
            'measured_void_fraction':None,
            'measured_bonded_contact_fraction':None,
            'chamber_c':number(first('chamber_temperature'),0,300),
            'fan_percent':number(first('fan_speed','fan_speed_percent'),0,100),
            'material_family':family,
            # A slicer profile name is not a verified manufacturer grade.
            'material_grade':first('filament_grade','material_grade'),
            'filament_profile':first('filament_settings_id'),
            'moisture_condition':first('moisture_condition','filament_moisture'),
            'annealing':first('annealing','anneal_condition'),
            'process_context_raw':deepcopy({k:v for k,v in config.items()
                if any(token in k.lower() for token in ('temperature','fan','moisture','anneal','grade','filament'))})}


def material_factors(analysis):
    """Identity factors are legacy placeholders, never equal-strength predictions."""
    read=settings(analysis)
    return {'version':VERSION,'status':'UNCALIBRATED_PROCESS_MODEL',
            'factor_status':'NOT_APPLIED','is_prediction':False,
            'factors':{axis:1. for axis in AXES},'applied':[],'settings':read,
            'literature_comparisons':literature_comparisons(read),
            'limitations':['No calibrated transfer from reference coupon to target process is available.',
                           'Identity factors mean no correction applied, not unchanged physical strength.',
                           'Literature observations are not applied to target material strength or force.',
                           'Reference and target grade, thermal history, orientation and test conditions must be established.']}


def process_adjustment(analysis,directional_mpa,*,reference_context=None):
    """Reference data and process evidence; no effective stress without calibration."""
    if not isinstance(directional_mpa,dict):return None
    report=material_factors(analysis)
    for axis in AXES:
        base=number(directional_mpa.get(axis),0,1e5)
        if base is None:return None
    report['reference_mpa']={axis:str(directional_mpa.get(axis)) for axis in AXES}
    report['effective_mpa']=None
    report['adjusted']=False
    report['reference_context']=deepcopy(reference_context) if isinstance(reference_context,dict) else None
    report['target_context']=deepcopy(report['settings'])
    return report
