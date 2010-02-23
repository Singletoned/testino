from setuptools import setup, find_packages
import sys, os

version = '1'

setup(name='flea',
      version=version,
      description="Test WSGI applications using lxml",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Oliver Cope',
      author_email='oliver@redgecko.org',
      url='',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'pesto',
          'lxml',
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
