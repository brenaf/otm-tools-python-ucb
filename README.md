`otm-tools-python` is a python interface to using [OpenTrafficModels](http://github.com/ggomes/otm-sim).

# Prerequisites
A clean install of Anaconda3 should set us on our way. We do need to install additional packages.
```
conda install -y geopandas py4j
conda install -y -c conda-forge osmnx
conda install pip
# retrieve wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#python-igraph
python -m pip install python_igraph-0.7.1.post6-cp37-cp37m-win_amd64.whl
```
To save video output consider installing ffmpeg.
```
apt install ffmpeg
or
conda install -c menpo ffmpeg
```
# Setup
Please ensure java 8 and maven is installed in your system.
```
apt install openjdk-8-jdk openjdk-8-jre maven
or
conda install -c anaconda openjdk maven lxml
```

The following command will compile the jar file and make the package importable.
```
python setup.py develop
```

# Usage
Please see examples/Usage.ipynb for sample code.
