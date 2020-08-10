from setuptools import setup, find_packages

__author__ = "Daren Thomas"
__copyright__ = "Copyright 2020, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Daren Thomas"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Daren Thomas"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"

setup(name='cea_osm_gwr_mapper',
      version=__version__,
      description="Maps building properties from GWR data to OpenStreetMaps building geometries in CEA format.",
      license='MIT',
      author='Architecture and Building Systems',
      author_email='cea@arch.ethz.ch',
      url='https://github.com/reyery/cea-osm-gwr-mapper',
      long_description="Maps building properties from GWR data to OpenStreetMaps building geometries in CEA format.",
      py_modules=[''],
      packages=find_packages(),
      package_data={},
      include_package_data=True)
