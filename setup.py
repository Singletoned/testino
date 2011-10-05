from setuptools import setup, find_packages

import __metadata__

setup(
    name=__metadata__.data['name'],
    version=__metadata__.data['version'],
    description=__metadata__.data['description'],
    long_description=__metadata__.data['long_description'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Software Development :: Testing',
    ],
    keywords='',
    author='Oliver Cope',
    author_email='oliver@redgecko.org',
    url='',
    license='BSD',
    py_modules=['testino'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'lxml',
        'werkzeug',
        # -*- Extra requirements: -*-
    ],
    entry_points="""
    # -*- Entry points: -*-
    """,
)
