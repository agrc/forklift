import glob
import io
from os.path import basename, dirname, join, splitext

from setuptools import find_packages, setup


def read(*names, **kwargs):
    return io.open(join(dirname(__file__), *names), encoding=kwargs.get("encoding", "utf8")).read()


setup(
    name="forklift",
    version="9.1.0",
    license="MIT",
    description="CLI tool for managing automated tasks.",
    long_description="",
    author="Steve Gourley",
    author_email="SGourley@utah.gov",
    url="https://github.com/agrc/forklift",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(i))[0] for i in glob.glob("src/*.py")],
    python_requires=">=3",
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Utilities",
    ],
    keywords=[],
    install_requires=[
        'colorama==0.*', 'docopt==0.6.*', 'gitpython==2.*', 'ndg-httpsclient==0.*', 'pyasn1==0.*', 'pyopenssl==17.*', 'pystache==0.*', 'requests>=2.20.0',
        'xxhash==1.*'
        #: pyopenssl, ndg-httpsclient, pyasn1 are there to disable ssl warnings in requests
    ],
    dependency_links=[],
    extras_require={
        'tests': [
            'mock==3.0.*',
            'pytest-cov==2.7.*',
            'pytest-instafail==0.4.*',
            'pytest-isort==0.3.*',
            'pytest-pylint==0.14.*',
            'pytest==4.*'
        ]
    },
    entry_points={"console_scripts": ["forklift = forklift.__main__:main"]}
)
