"""Deposition-process knockdowns read from the parsed G-code settings.

Speed and layer height change how long each weld line stays hot enough to heal,
so they scale the deposited material stress itself. Infill density, pattern and
wall count change the load-bearing section instead; those belong to capacity.py
and must never be applied here as well.
"""
from math import isfinite

VERSION='GCODE_PROCESS_KNOCKDOWN_V1'
# 986-file corpus: outer-wall setting median 200 mm/s (p75 250), measured time-weighted
# p50 median 146 mm/s (p90 225). The derate is relative to that fleet norm, so it only
# bites on prints faster than the machines normally run.
REFERENCE_SPEED_MM_S=200.
REFERENCE_LAYER_MM=.2
AXES=('X','Y','Z')


def number(value,low,high):
    try:value=float(str(value).split(',')[0].strip().rstrip('%'))
    except (TypeError,ValueError):return None
    return value if isfinite(value) and low<=value<=high else None


def settings(analysis):
    """Only values the scanner actually read from the file; never slicer defaults."""
    analysis=analysis or {}
    config=analysis.get('configuration') or {}
    metrics=analysis.get('process_metrics') or {}
    speeds=metrics.get('commanded_speed_mm_s') or {}
    def first(*keys):
        return next((config[k] for k in keys if config.get(k) not in (None,'')),None)
    width=next((value for key in ('outer_wall_line_width','external_perimeter_extrusion_width','line_width','extrusion_width')
                if '%' not in str(config.get(key)) and (value:=number(config.get(key),.05,3)) is not None),None)
    width_source='GCODE_LINE_WIDTH'
    if width is None:
        width=number(config.get('nozzle_diameter'),.05,3) or number(analysis.get('nozzle_diameter_mm'),.05,3)
        width_source='NOZZLE_DIAMETER_ASSUMPTION' if width is not None else 'UNKNOWN'
    return {'infill_percent':number(first('sparse_infill_density','fill_density'),0,100),
            'pattern':(str(config.get('sparse_infill_pattern') or config.get('fill_pattern') or '').strip().lower() or None),
            'walls':number(first('wall_loops','perimeters'),0,40),
            'line_width_mm':width,'line_width_source':width_source,
            'layer_height_mm':number(config.get('layer_height') or config.get('first_layer_height'),.01,3),
            'speed_mm_s':number(speeds.get('p50_approx'),1,2000),
            'nozzle_c':number(config.get('nozzle_temperature') or config.get('temperature'),50,600)}


def material_factors(analysis):
    """Bounded per-axis scaling of the material stress. Never rises above one."""
    read=settings(analysis);factors={axis:1. for axis in AXES};applied=[]
    speed=read['speed_mm_s']
    if speed and speed>REFERENCE_SPEED_MM_S:
        # Faster deposition shortens the time each interface spends healing.
        plane=max(.85,1-(speed-REFERENCE_SPEED_MM_S)*.0004)
        build=max(.70,1-(speed-REFERENCE_SPEED_MM_S)*.0010)
        factors['X']*=plane;factors['Y']*=plane;factors['Z']*=build
        applied.append({'variable':'DEPOSITION_SPEED','value':round(speed,1),'unit':'mm/s',
                        'reference':REFERENCE_SPEED_MM_S,'in_plane':round(plane,4),'build_axis':round(build,4)})
    layer=read['layer_height_mm']
    if layer and layer>REFERENCE_LAYER_MM:
        # Taller layers weld a smaller share of the section at each interface.
        plane=max(.9,(REFERENCE_LAYER_MM/layer)**.12)
        build=max(.7,(REFERENCE_LAYER_MM/layer)**.35)
        factors['X']*=plane;factors['Y']*=plane;factors['Z']*=build
        applied.append({'variable':'LAYER_HEIGHT','value':layer,'unit':'mm',
                        'reference':REFERENCE_LAYER_MM,'in_plane':round(plane,4),'build_axis':round(build,4)})
    return {'version':VERSION,'factors':{axis:round(factors[axis],6) for axis in AXES},
            'applied':applied,'settings':read,
            'limitations':['Speed and layer-height scaling are bounded engineering assumptions, not measured coupon corrections.',
                           'Infill density, pattern and wall count are applied per section when a load limit is computed, not here.',
                           'No value is ever raised above the published test-specimen strength.']}


def process_adjustment(analysis,directional_mpa):
    """As-printed material stress placed next to the published reference."""
    if not isinstance(directional_mpa,dict):return None
    report=material_factors(analysis);effective={}
    for axis in AXES:
        base=number(directional_mpa.get(axis),0,1e5)
        if base is None:return None
        effective[axis]=str(round(base*report['factors'][axis],4))
    report['reference_mpa']={axis:str(directional_mpa.get(axis)) for axis in AXES}
    report['effective_mpa']=effective
    report['adjusted']=any(report['factors'][axis]<1 for axis in AXES)
    return report
