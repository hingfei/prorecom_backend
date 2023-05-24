import fasttext
import fasttext.util
import numpy as np
import re
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from conn import get_session, JobSeeker as JobSeekerModel, Project as ProjectModel


# Define global variables to store the loaded model and clusters
ft_model = None
project_clusters = None
projects_skillset_vectors = None
centroids = None


def load_fasttext_model():
    global ft_model
    fasttext.util.download_model('en', if_exists='ignore')
    if ft_model is None:
        print('loading fast text')
        ft_model = fasttext.load_model('cc.en.300.bin')


async def get_user_skillsets(seeker_id):
    async with get_session() as session:
        sql = select(JobSeekerModel).options(selectinload(JobSeekerModel.users),
                                             selectinload(JobSeekerModel.skills)).where(
            JobSeekerModel.seeker_id == seeker_id)
        job_seeker_result = await session.execute(sql)
        job_seeker = job_seeker_result.scalars().one()

        user_skillsets = [skillset.skill_name for skillset in job_seeker.skills]
        return user_skillsets


async def get_projects_skillsets():
    async with get_session() as session:
        sql = select(ProjectModel).options(selectinload(ProjectModel.skills))
        projects_result = await session.execute(sql)
        projects = projects_result.scalars().all()

        projects_skillsets = []
        project_ids = []
        for project in projects:
            skills = [skill.skill_name for skill in project.skills]
            projects_skillsets.append(skills)
            project_ids.append(project.project_id)

        return projects_skillsets, project_ids


def preprocess_skillsets(skillsets):
    user_skillset = False
    preprocessed_skillsets = []

    for skills in skillsets:
        if isinstance(skills, str):  # Single skill within a skillset
            user_skillset = True
            # Convert to lowercase and remove symbols
            preprocessed_skills = re.sub(r'[^a-zA-Z\s+]', '', skills.lower().strip())
            # Split the skillset into separate skills
            preprocessed_skills = preprocessed_skills.split()
        else:  # List of skills within a skillset
            preprocessed_skills = []
            for skill in skills:
                # Convert to lowercase and remove symbols
                preprocessed_skill = re.sub(r'[^a-zA-Z\s+]', '', skill.lower().strip())
                preprocessed_skills += preprocessed_skill.split()
        preprocessed_skillsets.append(preprocessed_skills)

    if user_skillset:
        # Flatten the list of skillsets
        preprocessed_skillsets = [skill for skills in preprocessed_skillsets for skill in skills]

    return preprocessed_skillsets


async def cluster_projects(refresh=False):
    global project_clusters
    global projects_skillset_vectors
    global centroids
    if project_clusters is None or refresh:
        print('clustering projects')
        projects_skillsets, project_ids = await get_projects_skillsets()
        projects_skillsets_processed = preprocess_skillsets(projects_skillsets)

        skillset_size = ft_model.get_dimension()
        projects_skillset_vectors = []
        for i, skills in enumerate(projects_skillsets_processed):
            if skills:
                project_vector = np.mean([ft_model.get_word_vector(skill) for skill in skills], axis=0)
            else:
                project_vector = np.zeros(skillset_size)
            projects_skillset_vectors.append((project_vector, project_ids[i]))

        # Cluster projects based on skillset vectors
        n_clusters = 8
        kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit([v[0] for v in projects_skillset_vectors])
        centroids = kmeans.cluster_centers_
        project_clusters = [[] for _ in range(n_clusters)]
        for i, label in enumerate(kmeans.labels_):
            project_clusters[label].append(i)

        print("Project clusters", project_clusters)
        for cluster in project_clusters:
            print(f'Length of cluster: {len(cluster)}')


async def get_ranked_items(user_vector):
    # Cluster projects
    await cluster_projects()

    # Determine the closest cluster to the user skillset vector
    cluster_similarities = [cosine_similarity(user_vector.reshape(1, -1), centroid.reshape(1, -1)).item() for centroid
                            in centroids]
    closest_cluster_idx = np.argmax(cluster_similarities)

    print('closest cluster', len(project_clusters[closest_cluster_idx]))

    # Compute cosine similarity between user vector and project vectors within closest cluster
    cluster_project_skillset_vectors = [projects_skillset_vectors[i] for i in project_clusters[closest_cluster_idx]]
    cluster_project_vectors = [v[0] for v in cluster_project_skillset_vectors]
    cosine_similarities = cosine_similarity(user_vector.reshape(1, -1), cluster_project_vectors)

    # Rank projects by cosine similarity score
    ranked_projects = [(cluster_project_skillset_vectors[i][1], cosine_similarities[0][i])
                       for i in range(len(cluster_project_vectors))]
    ranked_projects = sorted(ranked_projects, key=lambda x: x[1], reverse=True)

    # Show recommendation
    print('Recommended projects:')
    print(f'Length of recommended project: {len(ranked_projects)}')
    for i, similarity in ranked_projects:
        print(f'Project {i} with similarity score {similarity:.4f}')

    return ranked_projects


async def get_projects_recommendations(seeker_id):
    async with get_session() as session:
        # Load the pre-trained FastText model
        load_fasttext_model()

        # Retrieve skillsets from databases
        user_skillsets = await get_user_skillsets(seeker_id)

        # Preprocess skillsets
        user_skillsets_processed = preprocess_skillsets(user_skillsets)

        # Generate vectors
        user_skillset_vector = np.mean([ft_model.get_word_vector(skillset) for skillset in user_skillsets_processed],
                                       axis=0)

        # print(project_skillset_vectors[0])
        # # Test Vectors
        # first_skill = ['c++ programming language', 'python', 'javascript programming language', 'frontend developer', 'php']
        # second_skill = ['c++', 'javascript', 'nodejs server', 'reactjs']
        # first_skill = preprocess_skillsets(first_skill)
        # second_skill = preprocess_skillsets(second_skill)
        # print('first', first_skill)
        # print('second', second_skill)
        # for skill in first_skill:
        #     print(skill)
        #
        # first_skill_vector = np.mean([ft_model.get_word_vector(skillset) for skillset in first_skill], axis=0)
        # second_skill_vector = np.mean([ft_model.get_word_vector(skillset) for skillset in second_skill], axis=0)
        # print(first_skill_vector.shape, first_skill_vector.ndim)
        # print(second_skill_vector.shape, second_skill_vector.ndim)
        # print(first_skill_vector)
        # print(first_skill_vector.reshape(1,-1))
        # print(first_skill_vector.reshape(1,-1).shape, first_skill_vector.reshape(1,-1).ndim)
        # similarity = cosine_similarity(first_skill_vector.reshape(1,-1), second_skill_vector.reshape(1,-1))
        # print('similarity', similarity)

        # Get ranked items
        ranked_projects = await get_ranked_items(user_skillset_vector)

        return ranked_projects
