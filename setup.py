import codecs
import pathlib
import setuptools
import re

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


def get_version() -> str:
    # Read version from file.
    version_file = pathlib.Path(__file__).parent.resolve() / "yodo1" / "__version__.py"
    with open(version_file, "r", encoding="utf-8") as f:
        version_file = f.read()
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                                  version_file, re.M)
        if version_match:
            return version_match.group(1)
        raise RuntimeError("Unable to find version string.")


with codecs.open('requirements.txt', 'r', 'utf8') as reader:
    install_requires = list(map(lambda x: x.strip(), reader.readlines()))

setuptools.setup(
    name="yodo1-toolkit",
    version=get_version(),
    author="Eliyar Eziz",
    author_email="eliyar@yodo1.com",
    description="A Yodo1 Python Toolbox",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Yodo1Games/py-yodo1",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(exclude=('tests',)),
    install_requires=install_requires,
    python_requires=">=3.6",
)
