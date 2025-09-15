# ADDIS

## Configuring the Environment 
    1 Clone the Repo
    2. Install Anaconda on your local machine
    3. Install Dependencies (See Below)

### Install this project's dependencies into a new Conda Environment
    $ conda env create -f environment.yml
### Activate Enviornment 
    $  conda activate <environment_name>


## Build Conda Enviornment From Scratch

### 1. Install Conda

### 2. Initialize conda for shell interaction
    $ conda init


### 3. Create a new fresh environment
    $ conda create --name test-env

### 4. Check if your new environment is created successfully
    $ conda info --envs

### 5. Activate the new environment
    $ conda activate test-env

### Register venv on your OS to generate Ipython Kernal
    $  python -m ipykernel install --user --name=your_environment_name --display-name="Python (Your Environment Name)"

### If Using Conda in Powershell
    Within "Anaconda Prompt":
        $ conda init powershell

    Within Powershell:
        $ Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser



# MLOPS Workflow
## Importing Data
 ### Shap Library
 ### S3
## Visualize Data
 ### Matplotlib
## Split Datasets into train and test sets (80/20) 
 ### Store Training and validation data using scikit learn
