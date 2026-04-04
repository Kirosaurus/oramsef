from setuptools import setup, find_packages

setup(
    name="fesmaro",
    version="1.0.0",
    description="Sistem deteksi kesehatan mata & jarak layar berbasis AI secara real-time",
    packages=find_packages(),
    python_requires=">=3.8,<3.12",
    install_requires=[
        "opencv-python",
        "mediapipe",
        "numpy",
        "fastapi",
        "uvicorn",
        "websockets",
    ],
)
