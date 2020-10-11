from setuptools import setup

setup(
    name="optopsy",
    description="A nimble backtesting and statistics library for options strategies",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    version="2.0.1",
    url="https://github.com/michaelchu/optopsy",
    author="Michael Chu",
    author_email="mchchu88@gmail.com",
    license="GPL-3.0-or-later",
    classifiers=[
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3.6",
    ],
    packages=["optopsy"],
    install_requires=["pandas", "numpy"],
)
