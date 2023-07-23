import json
import src.settings as settings
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from conn import get_session, JobSeeker as JobSeekerModel, Project as ProjectModel


# Function to retrieve skillsets of job seekers who are open for work
async def get_user_skillsets():
    async with get_session() as session:
        query = select(JobSeekerModel).options(selectinload(JobSeekerModel.users)).where(
            JobSeekerModel.seeker_is_open_for_work == True)
        job_seekers_result = await session.execute(query)
        job_seekers = job_seekers_result.scalars().all()

        skillset_size = settings.ft_model.get_dimension()
        user_skillsets = []
        for job_seeker in job_seekers:
            if job_seeker.seeker_skillset_vector is None:
                user_skillsets.append((np.zeros(skillset_size), job_seeker.seeker_id))
            else:
                user_skillset_vector = np.array(json.loads(job_seeker.seeker_skillset_vector))
                user_skillsets.append((user_skillset_vector, job_seeker.seeker_id))

        return user_skillsets


# Function to retrieve the skillset vector of a project
async def get_project_skillset(project_id):
    async with get_session() as session:
        query = select(ProjectModel).where(ProjectModel.project_id == project_id)
        project_result = await session.execute(query)
        project = project_result.scalars().one()

        skillset_size = settings.ft_model.get_dimension()
        if project.project_skillset_vector is None:
            return np.zeros(skillset_size)

        project_skillset_vector = np.array(json.loads(project.project_skillset_vector))
        return project_skillset_vector


# Function to cluster the candidates based on their skillset vectors
async def cluster_candidates(refresh=False):
    if settings.candidate_clusters is None or refresh:
        print('clustering candidates')
        # Get candidates skillset vectors
        candidates_skillset_vectors = await get_user_skillsets()
        if len(candidates_skillset_vectors) < 4:
            return

        settings.candidates_skillset_vectors = candidates_skillset_vectors

        # Cluster candidates based on skillset vectors
        n_clusters = 4
        kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit([v[0] for v in settings.candidates_skillset_vectors])
        settings.candidates_centroids = kmeans.cluster_centers_
        settings.candidate_clusters = [[] for _ in range(n_clusters)]
        for i, label in enumerate(kmeans.labels_):
            settings.candidate_clusters[label].append(i)

        print("Candidates clusters", settings.candidate_clusters)
        for cluster in settings.candidate_clusters:
            print(f'Length of cluster: {len(cluster)}')


# Function to rank the candidates based on their similarity to the project's skillset vector
async def get_ranked_candidates(project_vector):
    # Cluster projects
    await cluster_candidates()

    # Determine the closest cluster to the project skillset vector
    cluster_similarities = [cosine_similarity(project_vector.reshape(1, -1), centroid.reshape(1, -1)).item() for
                            centroid
                            in settings.candidates_centroids]
    closest_cluster_idx = np.argmax(cluster_similarities)

    print('closest cluster', len(settings.candidate_clusters[closest_cluster_idx]))

    # Compute cosine similarity between project vector and candidates vectors within closest cluster
    cluster_candidate_skillset_vectors = [settings.candidates_skillset_vectors[i] for i in
                                          settings.candidate_clusters[closest_cluster_idx]]
    cluster_candidate_vectors = [v[0] for v in cluster_candidate_skillset_vectors]
    cosine_similarities = cosine_similarity(project_vector.reshape(1, -1), cluster_candidate_vectors)

    # Rank candidates by cosine similarity score
    ranked_candidates = [(cluster_candidate_skillset_vectors[i][1], cosine_similarities[0][i])
                         for i in range(len(cluster_candidate_vectors))]
    ranked_candidates = sorted(ranked_candidates, key=lambda x: x[1], reverse=True)

    # Show recommendation
    print('Recommended candidates:')
    print(f'Length of recommended candidates: {len(ranked_candidates)}')
    for i, similarity in ranked_candidates:
        print(f'Candidate {i} with similarity score {similarity:.4f}')

    return ranked_candidates


# Function to get candidates' recommendations for a project
async def get_candidates_recommendations(project_id):
    async with get_session() as session:
        # Retrieve skillsets vector from databases
        project_skillset_vector = await get_project_skillset(project_id)

        # Get ranked candidates based on project's skillset vector
        ranked_candidates = await get_ranked_candidates(project_skillset_vector)

        return ranked_candidates
