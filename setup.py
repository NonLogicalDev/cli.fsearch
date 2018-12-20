from setuptools import setup, find_packages

setup(
    name="fsearch",
    version="0.0.1",
    description="A fuzzy matcher based on fzf.",
    author="nonlogicaldev",
    url="https://github.com/NonLogicalDev/nld.cli.fsearch",

    packages=find_packages(),
    scripts=[
        "bin/fsearch"
    ]
)

