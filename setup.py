import codecs

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with codecs.open('requirements.txt', 'r', 'utf8') as reader:
    install_requires = list(map(lambda x: x.strip(), reader.readlines()))

setuptools.setup(
    name="yodo1",
    version="0.0.1",
    author="Eliyar Eziz",
    author_email="eliyar@yodo1.com",
    description="A Yodo1 Python Toolbox",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="git@github.com:Yodo1Games/py-yodo1.git",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(exclude=('tests',)),
    python_requires=">=3.6",
)
