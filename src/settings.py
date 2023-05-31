import fasttext
import fasttext.util
import bcrypt


# Define global variables to store the loaded model and clusters
ft_model = None
project_clusters = None
projects_skillset_vectors = None
centroids = None


def init():
    global ft_model
    global project_clusters
    global projects_skillset_vectors
    global centroids


# Load pretrained model
def load_fasttext_model():
    global ft_model
    fasttext.util.download_model('en', if_exists='ignore')
    if ft_model is None:
        print('loading fast text')
        ft_model = fasttext.load_model('cc.en.300.bin')


def hash_password(password: str) -> str:
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')
