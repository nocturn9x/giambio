import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name="GiambIO",
    version="1.0",
    author="Nocturn9x aka IsGiambyy",
    author_email="hackhab@gmail.com",
    description="Asynchronous Python made easy (and friendly)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nocturn9x/giambio",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: Apache License 2.0"
    ],
    python_requires='>=3.6'
)
