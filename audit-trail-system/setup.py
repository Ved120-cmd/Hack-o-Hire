from setuptools import setup, find_packages

setup(
    name="audit-trail-system",
    version="1.0.0",
    description="Comprehensive Audit Trail System for SAR Report Generation",
    author="Your Organization",
    author_email="compliance@yourorg.com",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "sqlalchemy>=2.0.23",
        "pydantic>=2.5.0",
        "python-dateutil>=2.8.2",
        "pytz>=2023.3",
        "pyyaml>=6.0.1",
        "python-json-logger>=2.0.7",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
