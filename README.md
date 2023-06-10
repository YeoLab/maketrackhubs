# maketrackhubs
Current version: 1.0.0

# you need to have an aws profile called "yeolab-trackhubs"

contact me (Brian) if you need credentials

# Install requirements:

Consult the requirements.txt for a full list, but basically these packages are needed:
- trackhub
- boto3
- awscli
- python3

### Instructions:
```
conda create -y -n maketrackhubs python=3
source activate maketrackhubs
conda install -y -c bioconda -c anaconda -c conda-forge boto3 awscli trackhub=0.2.4
cd bin;
git clone https://github.com/byee4/trackhub
cd trackhub;
python setup.py install
```

# Example:
```
maketrackhubs --hub 20230610-maketrackhubstest --genome hg38 *.bb *.bw
```