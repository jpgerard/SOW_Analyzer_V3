from setuptools import setup, find_packages

setup(
    name="sow-analyzer",
    version="0.1.0",
    packages=find_packages(),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "pdfplumber>=0.10.0",
        "python-docx>=0.8.11",
        "spacy>=3.7.0",
        "streamlit>=1.29.0",
        "anthropic>=0.7.0",
        "pytest>=7.4.0",
        "black>=23.12.0",
        "pylint>=3.0.0",
        "python-dotenv>=1.0.0",
        "typing-extensions>=4.9.0",
    ],
    python_requires=">=3.9",
)
