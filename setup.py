from setuptools import setup, find_packages

setup(
    name="urbangravity",
    version="1.0.0",
    description="UrbanGravity - Geospatial Economic & Demographic Tier Intelligence Platform for Indian Metros",
    author="UrbanGravity Team",
    packages=find_packages(),
    py_modules=["main", "analyzer", "config"],
    install_requires=[
        "googlemaps>=4.10.0",
        "pandas>=2.0.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "urbangravity=main:main",
        ],
    },
    python_requires=">=3.9",
)

