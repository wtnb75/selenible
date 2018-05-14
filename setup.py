from setuptools import setup
from selenible.version import VERSION

setup(
    name="selenible",
    version=VERSION,
    description="selenium like ansible",
    author="Takashi WATANABE",
    author_email="wtnb75@gmail.com",
    url="https://github.com/wtnb75/selenible",
    packages=["selenible", "selenible.modules"],
    package_data={"selenible": ["schema/*.yaml"]},
    license="MIT",
    install_requires=open("requirements.txt").readlines(),
    entry_points={
        "console_scripts": [
            "selenible=selenible.base:cli"
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python :: 3',
    ],
    python_requires='>=3',
    keywords="selenium web",
)
