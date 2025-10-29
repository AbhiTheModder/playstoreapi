import shutil
import subprocess
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build

PROTOC_EXEC = "protoc"

CURRENT_DIR = Path(__file__).parent


class ProtobufBuilder(_build):
    def run(self):
        # check if protobuf is installed
        exec_path = shutil.which(PROTOC_EXEC)
        if exec_path is None:
            raise Exception("You should install protobuf compiler")

        print("Building protobuf file")
        subprocess.run(
            [
                exec_path,
                "--proto_path=" + str(CURRENT_DIR),
                "--python_out=" + str(CURRENT_DIR / "playstoreapi"),
                str(CURRENT_DIR / "googleplay.proto"),
            ]
        )
        super().run()


setup(
    name="playstoreapi",
    version="0.5.8",
    description="Unofficial python api for google play",
    long_description=(CURRENT_DIR / "README.md").read_text(),
    long_description_content_type="text/markdown",
    url="https://gitlab.com/AbhiTheModder/playstoreapi",
    author="NoMore201, marzzzello, AbhiTheModder",
    author_email="playstoreapi@07f.de",
    license="GPL3",
    packages=["playstoreapi"],
    package_data={
        "playstoreapi": [
            "config.pydevice.properties",
            "googleplay_pb2.py",
            "googleplay.py",
            "utils.py",
        ]
    },
    include_package_data=True,
    cmdclass={"build_py": ProtobufBuilder},
    install_requires=[
        "cryptography>=2.2",
        "protobuf>=3.5.2",
        "requests",
    ],
)
