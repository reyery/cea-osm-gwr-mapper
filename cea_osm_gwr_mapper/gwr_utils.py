import pandas as pd

LV95_PROJECTION = {'init': 'epsg:2056'}

GWR_HEADERS = [
    'federal_id',
    'official_building_number',
    'building_designation',
    'e_coordinate',
    'n_coordinate',
    'coordinate_origin',
    'local_code_1',
    'local_code_2',
    'local_code_3',
    'local_code_4',
    'quarter',
    'building_status',
    'building_category',
    'building_class',
    'construction_year',
    'construction_month',
    'construction_year_month',
    'construction_period',
    'renovation_year',
    'demolition_year',
    'building_area',
    'building_volume',
    'building_volume_source',
    'building_volume_norm',
    'number_floors',
    'number_living_rooms',
    'civil_defence_room',
    'energy_reference_area',
    'heating_tech_1',
    'heating_source_1',
    'heating_info_source_1',
    'heating_update_date_1',
    'heating_tech_2',
    'heating_source_2',
    'heating_info_source_2',
    'heating_update_date_2',
    'hot_water_tech_1',
    'hot_water_source_1',
    'hot_water_info_source_1',
    'hot_water_update_date_1',
    'hot_water_tech_2',
    'hot_water_source_2',
    'hot_water_info_source_2',
    'hot_water_update_date_2',
    'create_date',
    'update_date',
    'district_number',
    'district_name',
    'canton',
]

HEATING_TECH = {
    7400: "None",
    7410: "HeatPump",
    7411: "HeatPump",
    7420: "SolarThermal",
    7421: "SolarThermal",
    7430: "Boiler",
    7431: "Boiler",
    7432: "Boiler",
    7433: "Boiler",
    7434: "Boiler",
    7435: "Boiler",
    7436: "Boiler",
    7440: "Cogeneration",
    7441: "Cogeneration",
    7450: "Resistance",
    7451: "Resistance",
    7452: "Resistance",
    7460: "HeatExchanger",
    7461: "HeatExchanger",
    7499: "Unknown"
}

HOT_WATER_TECH = {
    7600: "None",
    7610: "HeatPump",
    7620: "SolarThermal",
    7630: "Boiler",
    7632: "Boiler",
    7634: "Boiler",
    7640: "Cogeneration",
    7650: "Resistance",
    7651: "Resistance",
    7660: "HeatExchanger",
    7699: "Unknown"
}

ENERGY_HEAT_SOURCE = {
    7500: 'None',
    7501: "Air",
    7510: "Ground",
    7511: "Ground",
    7512: "Ground",
    7513: "Water",
    7520: "Gas",
    7530: "Oil",
    7540: "Wood",
    7541: "Wood",
    7542: "Wood",
    7543: "Wood",
    7550: "ExhaustHeat",
    7560: "Electricity",
    7570: "Sun",
    7580: "DistrictHeating",
    7581: "DistrictHeating",
    7582: "DistrictHeating",
    7598: "Unknown",
    7599: "Unknown"
}

BUILDING_TYPE = {
    1110: "SINGLE_RES",
    1121: "MULTI_RES",
    1122: "MULTI_RES",
    1130: "MULTI_RES",
    1211: "HOTEL",
    1212: "HOTEL",
    1220: "OFFICE",
    1230: "RETAIL",
    1231: "RESTAURANT",
    1241: "PARKING",
    1242: "PARKING",
    1251: "INDUSTRIAL",
    1252: "INDUSTRIAL",
    1261: "LIBRARY",
    1262: "LIBRARY",
    1263: "SCHOOL",
    1264: "HOSPITAL",
    1265: "GYM",
    1271: "INDUSTRIAL",
    1272: "LIBRARY",
    1273: "LIBRARY",
    1274: "PARKING",
    1275: "HOSPITAL",
    1276: "INDUSTRIAL",
    1277: "INDUSTRIAL",
    1278: "INDUSTRIAL",
}


def read_gwr(gwr_path):
    filter_cols = [
        'canton',
        'district_number',
        'district_name',
        'e_coordinate',
        'n_coordinate',
        'building_category',
        'building_class',
        'building_status',
        'construction_year',
        'building_area',
        'number_floors',
        'heating_tech_1',
        'heating_source_1',
        'hot_water_tech_1',
        'hot_water_source_1'
    ]

    df = pd.read_csv(gwr_path, sep='\t', header=0, names=GWR_HEADERS, index_col=False).set_index('federal_id')
    df = df[filter_cols]

    # Drop properties without any coordinates
    no_coords = df['e_coordinate'].isna() | df['n_coordinate'].isna()
    df = df[~no_coords]

    # Drop non-existing buildings
    existing_buildings = df['building_status'] == 1004
    df = df[existing_buildings]

    # Fill missing year with median
    df['construction_year'] = df['construction_year'].fillna(df['construction_year'].median()).astype(int)

    # Fill missing floors with median
    df['number_floors'] = df['number_floors'].fillna(df['number_floors'].median()).astype(int)

    return df


def filter_gwr_by_bounds(gwr_df, minx, miny, maxx, maxy):
    e_coords = gwr_df['e_coordinate'].values
    n_coords = gwr_df['n_coordinate'].values
    within_e = (minx <= e_coords) & (e_coords <= maxx)
    within_n = (miny <= n_coords) & (n_coords <= maxy)

    return gwr_df[within_e & within_n]


# FIXME: Implement missing supply types for heating and hot water e.g. Solar Thermal, Cogen, Heat Exchanger
def gwr_to_cea_code(gwr_df):
    # Heating
    gwr_df['heating_tech'] = gwr_df['heating_tech_1'].map(HEATING_TECH).fillna('None')
    gwr_df['heating_source'] = gwr_df['heating_source_1'].map(ENERGY_HEAT_SOURCE).fillna('None')

    no_heating = (gwr_df['heating_tech'] == 'None') | (gwr_df['heating_tech'] == 'Unknown')  # Set unknown to None
    oil_boiler = (gwr_df['heating_tech'] == 'Boiler') & (gwr_df['heating_source'] == 'Oil')
    coal_boiler = (gwr_df['heating_tech'] == 'Boiler') & (gwr_df['heating_source'] == 'Coal')
    gas_boiler = (gwr_df['heating_tech'] == 'Boiler') & (gwr_df['heating_source'] == 'Gas')
    electrical_boiler = gwr_df['heating_tech'] == 'Resistance'
    wood_boiler = (gwr_df['heating_tech'] == 'Boiler') & (gwr_df['heating_source'] == 'Wood')
    ground_heat_pump = (gwr_df['heating_tech'] == 'HeatPump') & (gwr_df['heating_source'] == 'Ground')
    air_heat_pump = (gwr_df['heating_tech'] == 'HeatPump') & (gwr_df['heating_source'] == 'Air')
    water_heat_pump = (gwr_df['heating_tech'] == 'HeatPump') & (gwr_df['heating_source'] == 'Water')
    district_heating = gwr_df['heating_source'] == 'DistrictHeating'

    gwr_df.loc[no_heating, 'heating_tech_code'] = "SUPPLY_HEATING_AS0"
    gwr_df.loc[oil_boiler, 'heating_tech_code'] = "SUPPLY_HEATING_AS1"
    gwr_df.loc[coal_boiler, 'heating_tech_code'] = "SUPPLY_HEATING_AS2"
    gwr_df.loc[gas_boiler, 'heating_tech_code'] = "SUPPLY_HEATING_AS3"
    gwr_df.loc[electrical_boiler, 'heating_tech_code'] = "SUPPLY_HEATING_AS4"
    gwr_df.loc[wood_boiler, 'heating_tech_code'] = "SUPPLY_HEATING_AS5"
    gwr_df.loc[ground_heat_pump, 'heating_tech_code'] = "SUPPLY_HEATING_AS6"
    gwr_df.loc[air_heat_pump, 'heating_tech_code'] = "SUPPLY_HEATING_AS7"
    gwr_df.loc[water_heat_pump, 'heating_tech_code'] = "SUPPLY_HEATING_AS8"
    gwr_df.loc[district_heating, 'heating_tech_code'] = "SUPPLY_HEATING_AS9"

    # Set everything else to no heating
    gwr_df['heating_tech_code'] = gwr_df['heating_tech_code'].fillna("SUPPLY_HEATING_AS0")

    # Hot water
    gwr_df['hot_water_tech'] = gwr_df['hot_water_tech_1'].map(HOT_WATER_TECH).fillna('None')
    gwr_df['hot_water_source'] = gwr_df['hot_water_source_1'].map(ENERGY_HEAT_SOURCE).fillna('None')

    no_hot_water = (gwr_df['hot_water_tech'] == 'None') | (gwr_df['hot_water_tech'] == 'Unknown')  # Set unknown to None
    oil_boiler = (gwr_df['hot_water_tech'] == 'Boiler') & (gwr_df['hot_water_source'] == 'Oil')
    coal_boiler = (gwr_df['hot_water_tech'] == 'Boiler') & (gwr_df['hot_water_source'] == 'Coal')
    gas_boiler = (gwr_df['hot_water_tech'] == 'Boiler') & (gwr_df['hot_water_source'] == 'Gas')
    electrical_boiler = gwr_df['hot_water_tech'] == 'Resistance'
    wood_boiler = (gwr_df['hot_water_tech'] == 'Boiler') & (gwr_df['hot_water_source'] == 'Wood')
    ground_heat_pump = (gwr_df['hot_water_tech'] == 'HeatPump') & (gwr_df['hot_water_source'] == 'Ground')
    air_heat_pump = (gwr_df['hot_water_tech'] == 'HeatPump') & (gwr_df['hot_water_source'] == 'Air')
    water_heat_pump = (gwr_df['hot_water_tech'] == 'HeatPump') & (gwr_df['hot_water_source'] == 'Water')
    district_heating = gwr_df['hot_water_source'] == 'DistrictHeating'

    gwr_df.loc[no_hot_water, 'hot_water_tech_code'] = "SUPPLY_HOTWATER_AS0"
    gwr_df.loc[oil_boiler, 'hot_water_tech_code'] = "SUPPLY_HOTWATER_AS1"
    gwr_df.loc[coal_boiler, 'hot_water_tech_code'] = "SUPPLY_HOTWATER_AS2"
    gwr_df.loc[gas_boiler, 'hot_water_tech_code'] = "SUPPLY_HOTWATER_AS3"
    gwr_df.loc[electrical_boiler, 'hot_water_tech_code'] = "SUPPLY_HOTWATER_AS4"
    gwr_df.loc[wood_boiler, 'hot_water_tech_code'] = "SUPPLY_HOTWATER_AS5"
    gwr_df.loc[ground_heat_pump, 'hot_water_tech_code'] = "SUPPLY_HOTWATER_AS6"
    gwr_df.loc[air_heat_pump, 'hot_water_tech_code'] = "SUPPLY_HOTWATER_AS7"
    gwr_df.loc[water_heat_pump, 'hot_water_tech_code'] = "SUPPLY_HOTWATER_AS8"
    gwr_df.loc[district_heating, 'hot_water_tech_code'] = "SUPPLY_HOTWATER_AS9"

    # Set everything else to no hot water
    gwr_df['hot_water_tech_code'] = gwr_df['hot_water_tech_code'].fillna("SUPPLY_HOTWATER_AS0")

    # Building type
    building_type = gwr_df['building_class'].map(BUILDING_TYPE)
    most_common_type = building_type.value_counts().idxmax()
    gwr_df['building_type'] = building_type.fillna(most_common_type)  # Fill empty values with most common building type

    return gwr_df
