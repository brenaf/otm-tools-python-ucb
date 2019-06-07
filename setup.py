import subprocess
import sys
from setuptools.command.develop import develop
import setuptools
import os

class DevelopWrapper(develop):
  """Compiles the otm-python-api so that pyotm can
  call on the OTM api."""

  def run(self):
    # Run this first so the develop stops in case 
    # these fail otherwise the Python package is
    # successfully developed
    self._compile_otm_python_api()
    develop.run(self)

  def _compile_otm_python_api(self):
    try:
        # subprocess.call('mvn package -f otm-python-api\pom.xml -DskipTests'.split(' '))
        os.system('mvn package -f otm-python-api\pom.xml -DskipTests')
    except Exception as err:
        print(err)
        sys.exit(1)

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyotm",
    version="0.0.1",
    author="Chester Balingit, Damian Dailisan",
    author_email="acbalingit@nip.upd.edu.ph, ddailisan@nip.upd.edu.ph",
    description="Wrapper for interating with OpenTrafficModels",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nipcxteam/otm-tools-python",
    packages=setuptools.find_packages(),
    # classifiers=[
    #     "Programming Language :: Python :: 3",
    #     "License :: OSI Approved :: MIT License",
    #     "Operating System :: OS Independent",
    # ],
    cmdclass={'develop': DevelopWrapper}
)
