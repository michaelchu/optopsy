from setuptools import find_packages, setup

# Core library packages (always installed)
_core_packages = find_packages(
    exclude=["tests", "tests.*", "samples", "optopsy.ui", "optopsy.ui.*"],
)

# UI packages — included in the distribution but only functional when
# installed with the [ui] extra, which provides the required third-party
# dependencies (chainlit, litellm, etc.).  The console_scripts entry point
# is gated with [ui] so `optopsy-chat` won't be registered without it.
#
# NOTE: setuptools extras_require controls *dependencies*, not which
# packages are included in a wheel/sdist.  To truly exclude these files
# from a core-only install you would need a separate distribution package
# (e.g. "optopsy-ui").  We include them here so that `pip install
# optopsy[ui]` works correctly in both editable and non-editable installs.
_ui_packages = [
    "optopsy.ui",
    "optopsy.ui.tools",
    "optopsy.ui.providers",
]

setup(
    name="optopsy",
    description="A nimble backtesting and statistics library for options strategies",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    version="2.3.0b1",
    url="https://github.com/michaelchu/optopsy",
    author="Michael Chu",
    author_email="mchchu88@gmail.com",
    license="GPL-3.0-or-later",
    classifiers=[
        "Operating System :: OS Independent",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.12,<3.14",
    packages=_core_packages + _ui_packages,
    package_data={"optopsy.ui": ["public/*"]},
    install_requires=[
        "pandas",
        "numpy",
        "typing_extensions>=4.0.0",
        "tabulate>=0.9.0,<1.0.0",
        "pandas-ta>=0.4.67b0",
    ],
    extras_require={
        "ui": [
            "pyarrow>=14.0.0",
            "chainlit>=1.0.0,<3.0.0",
            "litellm>=1.0.0,<3.0.0",
            "python-dotenv>=1.0.0,<2.0.0",
            "requests>=2.28.0,<3.0.0",
            "yfinance>=0.2.0,<1.0.0",
            "sqlalchemy>=2.0.0,<3.0.0",
            "aiosqlite>=0.17.0,<1.0.0",
            "greenlet>=3.0.0",
            "plotly>=5.0.0,<7.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "optopsy-chat=optopsy.ui.cli:main [ui]",
        ],
    },
)
