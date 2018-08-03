from setuptools import setup

setup(name='optopsy',
      description='Python Backtesting library for options trading strategies',
      long_description=open("README.md").read(),
      version='0.1.0',
      url='https://github.com/michaelchu/optopsy',
      author='Michael Chu',
      author_email='mchchu88@gmail.com',
      license='MIT',
      classifiers=[
          "Operating System :: OS Independent",
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3'
      ],
      packages=['optopsy']
)

