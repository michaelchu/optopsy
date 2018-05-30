import sys

if sys.version_info > (3, 0):
    # Python 3 code in this block
    import pathlib

    PROJECT_DIR = str(pathlib.Path(__file__).parents[1])
else:
    # Python 2 code in this block
    import pathlib2

    PROJECT_DIR = str(pathlib2.Path(__file__).parents[1])

DATA_SUB_DIR = PROJECT_DIR + "feeds"