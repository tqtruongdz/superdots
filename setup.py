#!/usr/bin/env python3
"""
SuperDots - A cross-platform dotfiles and configuration management tool
"""

from setuptools import setup, find_packages
import os

# Read the README file
current_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(current_dir, "README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open(os.path.join(current_dir, "requirements.txt"), "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="superdots",
    version="1.0.0",
    author="SuperDots Team",
    author_email="admin@superdots.dev",
    description="A cross-platform dotfiles and configuration management tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/superdots/superdots",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "security": [
            "cryptography>=3.4.0",
        ],
        "watch": [
            "watchdog>=2.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "superdots=superdots.cli:main",
            "sdots=superdots.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "superdots": ["templates/*.yaml", "templates/*.json"],
    },
    project_urls={
        "Bug Reports": "https://github.com/superdots/superdots/issues",
        "Source": "https://github.com/superdots/superdots",
        "Documentation": "https://superdots.readthedocs.io",
    },
    keywords="dotfiles configuration management git sync cross-platform",
    zip_safe=False,
)
