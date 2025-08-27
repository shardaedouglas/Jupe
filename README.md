# Jupe

## Configuring the Environment 

### 1. Install Conda

### 2. Initialize conda for shell interaction
    $ conda init

### 3. Create a new fresh environment
    $ conda create --name test-env

### 4. Check if your new environment is created successfully
    $ conda info --envs

### 5. Activate the new environment
    $ conda activate test-env

### Register venv to generate Ipython Kernal
    $  python -m ipykernel install --user --name=your_environment_name --display-name="Python (Your Environment Name)"

### Using Conda in Powershell
    In Anaconda Prompt:
        $ conda init powershell

    In Powershell:
        $ Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

Link Github
Data
Importing Data
Shap Library
S3
Visualize Data
Matplotlib
Split Datasets into train and test sets
StoreTraining and validation data for model Training using scikit learn
