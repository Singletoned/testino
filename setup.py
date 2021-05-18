from setuptools import setup

data = dict(
    name='testino',
    version='0.3.12',
    description="Test ASGI/WSGI applications using lxml",
    long_description="",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Software Development :: Testing',
    ],
    keywords='',
    author='Ed Singleton',
    author_email='singletoned@gmail.com',
    url='https://github.com/Singletoned/testino',
    license='BSD',
    py_modules=['testino'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "lxml>=3.7",
        "werkzeug>=0.12",
        "cssselect>=1",
        "parsel>=1.1",
        "requests>=2",
        "requests-wsgi-adapter>=0.2",
    ],
    entry_points="""
    # -*- Entry points: -*-
    """,
)

if __name__ == '__main__':
    setup(**data)
