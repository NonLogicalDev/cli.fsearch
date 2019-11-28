from setuptools import setup, find_packages

setup(
    name="nl-fsearch",
    version="0.0.2",
    license="MIT",

    author="nonlogicaldev",
    description="A file/folder lookup tool for use with fzf.",
    url="https://github.com/NonLogicalDev/cli.fsearch",

    packages=find_packages(),
    scripts=[
        "bin/fsearch"
    ]
)

