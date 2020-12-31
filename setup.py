from setuptools import setup, find_packages


requirements = []

setup(
      name="node_configure",
      version = "0.0.1", #@version@#
      description="handle,.in progressing..,APIs",
      author="ihgazni2",
      url="https://github.com/ihgazni2/node_configure",
      author_email='', 
      license="MIT",
      long_description = "refer to .md files in https://github.com/ihgazni2/node_configure",
      classifiers=[
          'Environment :: Console',
          'Environment :: Web Environment',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'Programming Language :: Python',
          ],
      packages= find_packages(),
      entry_points={
          'console_scripts': [
              'node_configure=node_configure.bin:main'
          ]
      },
      package_data={
          'resources':['RESOURCES/*']
      },
      include_package_data=True,
      install_requires=requirements,
      py_modules=['node_configure'], 
)


# python3 setup.py bdist --formats=tar
# python3 setup.py sdist

