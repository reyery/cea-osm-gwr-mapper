"""
Creates a simple summary of the demand totals from the cea demand script.

NOTE: This is an example of how to structure a cea plugin script. It is intentionally simplistic to avoid distraction.
"""
from __future__ import division
from __future__ import print_function

import cea.config
import cea.inputlocator
import cea.plugin
import geopandas as gpd
import pandas as pd
from cea.datamanagement.archetypes_mapper import archetypes_mapper
from cea.utilities.dbf import dataframe_to_dbf, dbf_to_dataframe
from shapely.geometry import Point

from gwr_utils import read_gwr, LV95_PROJECTION, gwr_to_cea_code, filter_gwr_by_bounds

__author__ = "Reynold Mok"
__copyright__ = "Copyright 2020, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Daren Thomas"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Reynold Mok"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"


class GWRMapperPlugin(cea.plugin.CeaPlugin):
    """
    Define the plugin class - unless you want to customize the behavior, you only really need to declare the class. The
    rest of the information will be picked up from ``default.config``, ``schemas.yml`` and ``scripts.yml`` by default.
    """
    pass


def map_props_to_geom(building_name, building_geometry, gwr_gdf):
    # Reduce search space by filtering by bounds
    minx, miny, maxx, maxy = building_geometry.bounds
    in_bounds_gwr_gdf = filter_gwr_by_bounds(gwr_gdf, minx, miny, maxx, maxy)

    if in_bounds_gwr_gdf.empty:  # No properties found within geometry bounding box
        building_properties = in_bounds_gwr_gdf.copy()
    else:  # Check if properties are found within geometry points
        properties_in_geometry = in_bounds_gwr_gdf['geometry'].within(building_geometry)
        building_properties = in_bounds_gwr_gdf[properties_in_geometry].copy()

    if building_properties.empty:
        building_properties.loc[0] = None
        building_properties['occupancy_ratio'] = None
    elif len(building_properties) == 1:
        building_type = building_properties['building_type'].values[0]
        building_properties['occupancy_ratio'] = '{}:{}'.format(building_type, 1.0)
    else:  # Reduce building properties to single row if multiple found
        building_properties = reduce_building_properties(building_properties)
    building_properties['Name'] = building_name  # Add CEA building name to properties

    return building_properties


def reduce_building_properties(building_properties_df):
    out = building_properties_df.iloc[[0]].copy()

    # Use latest year
    out['construction_year'] = building_properties_df['construction_year'].max()

    # Use highest number of floors
    out['number_floors'] = building_properties_df['number_floors'].max()

    # Get gross floor area of each property
    building_properties_df['gross_floor_area'] = building_properties_df['building_area'].fillna(1.0).astype(float) \
                                                 * building_properties_df['number_floors']

    # Use building type with largest gross floor area
    building_type = building_properties_df[['building_type', 'gross_floor_area']].groupby('building_type').sum()
    out['building_type'] = building_type['gross_floor_area'].idxmax()

    percentage = building_type['gross_floor_area'] / building_type['gross_floor_area'].sum()
    num = min(len(percentage), 3)  # CEA only supports maximum of 3 different occupancy types in one building
    if num != 1:
        percentage = percentage.round(5).sort_values(ascending=False).iloc[:num]
        percentage.iloc[-1] = round(1.0 - percentage.iloc[:-1].sum(), 5)
    out['occupancy_ratio'] = ';'.join(['{}:{}'.format(occupancy, ratio)
                                       for occupancy, ratio in percentage.to_dict().items()])

    # Use heating tech with largest gross floor area
    heating_tech = building_properties_df[['heating_tech_code', 'gross_floor_area']].groupby('heating_tech_code').sum()
    out['heating_tech_code'] = heating_tech['gross_floor_area'].idxmax()

    # Use hot water tech with largest gross floor area
    hot_water_tech = building_properties_df[['hot_water_tech_code', 'gross_floor_area']].groupby('hot_water_tech_code').sum()
    out['hot_water_tech_code'] = hot_water_tech['gross_floor_area'].idxmax()
    return out


def generate_typology(properties_df, standard_definition_df):
    out = pd.DataFrame()
    out['Name'] = properties_df['Name']
    out['YEAR'] = properties_df['construction_year']

    def get_standard(year):
        return standard_definition_df[(standard_definition_df['YEAR_START'] <= year) & (
                    standard_definition_df['YEAR_END'] >= year)].STANDARD.values[0]
    out['STANDARD'] = out['YEAR'].apply(get_standard)

    occupancy_ratio = properties_df[['Name', 'occupancy_ratio']].set_index('Name')
    occupancy_ratio = occupancy_ratio['occupancy_ratio'].str.split(';', expand=True)
    for i in range(1, 3):
        if i not in occupancy_ratio.columns:
            occupancy_ratio[i] = 'NONE:0.0'
    ratio_split = pd.concat([occupancy_ratio[col].str.split(':', expand=True) for col in occupancy_ratio], axis=1)
    ratio_split[0] = ratio_split[0].fillna('NONE').astype(str)
    ratio_split[1] = ratio_split[1].fillna(0.0).astype(float)
    ratio_split.columns = ['1ST_USE', '1ST_USE_R', '2ND_USE', '2ND_USE_R', '3RD_USE', '3RD_USE_R']
    out = pd.concat([out.set_index('Name'), ratio_split], axis=1).reset_index()

    out['REFERENCE'] = 'GWR Mapper'

    return out


def gwr_mapper(config, locator):
    gwr_path = config.gwr_mapper.gwr_path
    zone_path = locator.get_zone_geometry()
    surroundings_path = locator.get_surroundings_geometry()

    gwr_df = read_gwr(gwr_path)
    zone_gdf = gpd.read_file(zone_path)

    # Filter GWR data to zone extent
    print('Filtering GWR data to location')
    reprojected_zone_gdf = zone_gdf.to_crs(LV95_PROJECTION)
    minx, miny, maxx, maxy = reprojected_zone_gdf['geometry'].total_bounds
    gwr_df = filter_gwr_by_bounds(gwr_df, minx, miny, maxx, maxy)

    print('Translating GWR to CEA code')
    gwr_df = gwr_to_cea_code(gwr_df)

    print('Mapping GWR Buildings to CEA Buildings')
    coord_points = [Point(x, y) for x, y in zip(gwr_df['e_coordinate'], gwr_df['n_coordinate'])]
    gwr_gdf = gpd.GeoDataFrame(gwr_df, geometry=coord_points, crs=LV95_PROJECTION)
    building_properties = [map_props_to_geom(building_name, building_geom, gwr_gdf) for building_name, building_geom in
                           zip(reprojected_zone_gdf['Name'], reprojected_zone_gdf['geometry'])]
    properties_df = pd.concat(building_properties)

    print('Filling in missing data')
    # Fill empty rows with most common building type
    building_type = properties_df['building_type'].value_counts().idxmax()
    common_building_properties_df = properties_df.loc[properties_df['building_type'] == building_type]
    construction_year = common_building_properties_df['construction_year'].median()
    number_floors = common_building_properties_df['number_floors'].median()
    heating_tech_code = common_building_properties_df['heating_tech_code'].value_counts().idxmax()
    hot_water_tech_code = common_building_properties_df['hot_water_tech_code'].value_counts().idxmax()

    properties_df['construction_year'] = properties_df['construction_year'].fillna(construction_year).astype(int)
    properties_df['number_floors'] = properties_df['number_floors'].fillna(number_floors).astype(int)
    properties_df['occupancy_ratio'] = properties_df['occupancy_ratio'].fillna('{}:{}'.format(building_type, 1.0)).astype(str)
    properties_df['heating_tech_code'] = properties_df['heating_tech_code'].fillna(heating_tech_code).astype(str)
    properties_df['hot_water_tech_code'] = properties_df['hot_water_tech_code'].fillna(hot_water_tech_code).astype(str)

    # properties_df.to_csv(r'C:\Users\Reynold Mok\Downloads\GWR Data\mappings.csv')

    print('Setting CEA building floors from GWR data')
    new_zone_gdf = zone_gdf.set_index('Name')
    gwr_floors_df = properties_df[['Name', 'number_floors']].set_index('Name').rename(
        columns={"number_floors": "floors_ag"})
    new_zone_gdf.update(gwr_floors_df)
    new_zone_gdf['height_ag'] = new_zone_gdf['floors_ag'] * 3
    new_zone_gdf = new_zone_gdf.reset_index()
    new_zone_gdf.to_file(zone_path)

    print('Generating CEA building typology from GWR data')
    standard_definition_df = pd.read_excel(locator.get_database_construction_standards(), sheet_name='STANDARD_DEFINITION')
    typology_df = generate_typology(properties_df, standard_definition_df)

    print('Run CEA `archetypes-mapper` with generated building typology')
    dataframe_to_dbf(typology_df, locator.get_building_typology())

    mapper_flags = {'update_architecture_dbf': True,
                    'update_air_conditioning_systems_dbf': True,
                    'update_indoor_comfort_dbf': True,
                    'update_internal_loads_dbf': True,
                    'update_supply_systems_dbf': True,
                    'update_schedule_operation_cea': True}
    archetypes_mapper(locator, buildings=typology_df['Name'].values, **mapper_flags)

    print('Update heating and hot water supply systems from GWR data')
    supply_systems_df = dbf_to_dataframe(locator.get_building_supply()).set_index('Name')
    gwr_supply_systems_df = properties_df[['Name', 'heating_tech_code', 'hot_water_tech_code']].set_index('Name').rename(
        columns={"heating_tech_code": "type_hs", "hot_water_tech_code": "type_dhw"})
    supply_systems_df.update(gwr_supply_systems_df)
    supply_systems_df = supply_systems_df.reset_index()
    dataframe_to_dbf(supply_systems_df, locator.get_building_supply())


def main(config):
    """
    This is the main entry point to your script. Any parameters used by your script must be present in the ``config``
    parameter. The CLI will call this ``main`` function passing in a ``config`` object after adjusting the configuration
    to reflect parameters passed on the command line / user interface

    :param cea.config.Configuration config: The configuration for this script, restricted to the scripts parameters.
    :return: None
    """
    locator = cea.inputlocator.InputLocator(config.scenario, config.plugins)
    gwr_mapper(config, locator)


if __name__ == '__main__':
    main(cea.config.Configuration())
