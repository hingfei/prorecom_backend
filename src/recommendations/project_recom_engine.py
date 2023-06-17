import json
import src.settings as settings
import numpy as np
import re
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from conn import get_session, JobSeeker as JobSeekerModel, Project as ProjectModel


async def get_user_skillsets(seeker_id):
    async with get_session() as session:
        sql = select(JobSeekerModel).options(selectinload(JobSeekerModel.users)).where(
            JobSeekerModel.seeker_id == seeker_id)
        job_seeker_result = await session.execute(sql)
        job_seeker = job_seeker_result.scalars().one()
        if job_seeker.seeker_skillset_vector is None:
            skillset_size = settings.ft_model.get_dimension()
            return np.zeros(skillset_size)
        user_skillset_vector = np.array(json.loads(job_seeker.seeker_skillset_vector))
        return user_skillset_vector


async def get_projects_skillsets():
    async with get_session() as session:
        sql = select(ProjectModel).where(ProjectModel.project_status == True)
        projects_result = await session.execute(sql)
        projects = projects_result.scalars().all()

        projects_skillset_vectors = []
        for project in projects:
            project_vector = np.array(json.loads(project.project_skillset_vector))
            projects_skillset_vectors.append((project_vector, project.project_id))

        return projects_skillset_vectors


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
    if settings.project_clusters is None or refresh:
        print('clustering projects')
        # Get projects skillset vectors
        projects_skillsets_vectors = await get_projects_skillsets()
        settings.projects_skillset_vectors = projects_skillsets_vectors

        # Cluster projects based on skillset vectors
        n_clusters = 8
        kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit([v[0] for v in settings.projects_skillset_vectors])
        settings.projects_centroids = kmeans.cluster_centers_
        settings.project_clusters = [[] for _ in range(n_clusters)]
        for i, label in enumerate(kmeans.labels_):
            settings.project_clusters[label].append(i)

        print("Project clusters", settings.project_clusters)
        for cluster in settings.project_clusters:
            print(f'Length of cluster: {len(cluster)}')


async def get_ranked_projects(user_vector):
    # Cluster projects
    await cluster_projects()

    # Determine the closest cluster to the user skillset vector
    cluster_similarities = [cosine_similarity(user_vector.reshape(1, -1), centroid.reshape(1, -1)).item() for centroid
                            in settings.projects_centroids]
    closest_cluster_idx = np.argmax(cluster_similarities)

    print('closest cluster', len(settings.project_clusters[closest_cluster_idx]))

    # Compute cosine similarity between user vector and project vectors within closest cluster
    cluster_project_skillset_vectors = [settings.projects_skillset_vectors[i] for i in
                                        settings.project_clusters[closest_cluster_idx]]
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
        # Retrieve skillsets vector from databases
        user_skillset_vector = await get_user_skillsets(seeker_id)

        # Get ranked items
        ranked_projects = await get_ranked_projects(user_skillset_vector)

        return ranked_projects
