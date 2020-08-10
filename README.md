# cea-plugin-template

To install, clone this repo to a desired path (you would need to have `git` installed to run this command. Alternatively you can also run this command in the CEA console):

```git clone https://github.com/reyery/cea-osm-gwr-mapper.git DESIRED_PATH```


Open CEA console and enter the following command to install the plugin to CEA:

```pip install -e PATH_OF_PLUGIN_FOLDER```

(NOTE: PATH_OF_PLUGIN_FOLDER would be the DESIRED_PATH + 'cea-osm-gwr-mapper')


In the CEA console, enter the following command to enable the plugin in CEA:

```cea-config write --general:plugins cea_osm_gwr_mapper.gwr_mapper.GWRMapperPlugin```

Now you should be able to enter the following command to run the plugin:

```cea gwr-mapper```