from setuptools import setup, find_packages

setup(
    name='jobtech-common',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask', 'flask-restplus', 'flask-cors', 'elasticsearch', 'certifi'
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"]
)