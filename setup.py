from setuptools import setup, find_packages

data = dict(
    name='testino',
    version='0.1',
    description="Test WSGI applications using lxml",
    long_description="",
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
        'lxml>=2.3',
        'werkzeug>=0.6',
        # -*- Extra requirements: -*-
    ],
    entry_points="""
    # -*- Entry points: -*-
    """,
)

if __name__ == '__main__':
    setup(**data)
