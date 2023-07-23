import fasttext
import fasttext.util
import bcrypt

# Define global variables to store the loaded model and clusters
ft_model = None
project_clusters = None
candidate_clusters = None
projects_skillset_vectors = None
candidates_skillset_vectors = None
projects_centroids = None
candidates_centroids = None


# This function initializes global variables to None.
# These variables will be used to store the loaded model and clustering results.
def init():
    global ft_model
    global project_clusters
    global candidate_clusters
    global projects_skillset_vectors
    global candidates_skillset_vectors
    global projects_centroids
    global candidates_centroids


# Load pretrained model
def load_fasttext_model():
    global ft_model

    # Download the fastText model if it's not already downloaded
    fasttext.util.download_model('en', if_exists='ignore')
    # Load the fastText model if it's not already loaded
    if ft_model is None:
        print('loading fast text')
        ft_model = fasttext.load_model('cc.en.300.bin')


def hash_password(password: str) -> str:
    # This function takes a password string as input, hashes it using bcrypt, and returns the hashed password.
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')
