# ProRecom

## Intelligent Project Recommendation System (Back-end)

ProRecom Backend is the server-side component of the ProRecom application, an intelligent project recommendation system.
It is designed to handle data processing, database operations, and GraphQL APIs to support seamless communication
between the frontend and the underlying database. Leveraging advanced technologies, ProRecom Backend is a key component
that drives the platform's skillset-based project recommendations and candidate matching capabilities.

## Table of Contents

- [ProRecom](#prorecom)
    - [Table of Contents](#table-of-contents)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Description](#description)
        - [Purpose](#purpose)
        - [Main Features](#main-features)
        - [How it Works](#how-it-works)
    - [Technologies](#technologies)
    - [Features](#features)
    - [Usage](#usage)
    - [Frontend Reference](#frontend-reference)

## Prerequisites

Before installing ProRecom Backend, ensure that you have the following prerequisites set up:

1. **Anaconda or Miniconda**: ProRecom Backend requires Conda, a package manager and environment management system. If
   you don't have Conda installed, you can download Anaconda (which includes Conda) or Miniconda (a minimal version of
   Anaconda) from the official website: [Anaconda](https://www.anaconda.com/download)
   or [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
2. **Conda Environment**: Create a Conda environment to isolate the dependencies for ProRecom Backend.
3. **Python Package Installer (pip)**: Make sure you have pip installed in your Conda environment. Pip is required to
   install additional Python packages used in the project.

## Installation

1. Clone the repository: `git clone https://github.com/hingfei/prorecom_backend.git`
2. Create conda environment: `conda create -n prorecom-backend python=3.9 pip`
3. Activate conda environment: `conda activate prorecom-backend`
4. Install FastText dependency: `conda install -c esri fasttext`
4. Install remaining dependencies: `pip install -r requirements.txt`
5. Add .env file
6. Start the server: `uvicorn src.main:app --reload`

## Description

### Purpose

ProRecom Backend serves as the backbone of the ProRecom application, providing robust functionalities to enable
skillset-based project recommendations and candidate matching. The primary purpose of ProRecom Backend is to process
user data, skillset keyword extraction, vectorization, matching and ranking to provide recommendation and manage the
database to support smooth communication with the frontend.

### Main Features

1. **Skillset Keyword Extraction**: ProRecom Backend implements an advanced algorithm to extract skillset keywords from
   projects and job seekers' profiles. By analyzing textual data and identifying key skills and expertise, the backend
   creates the foundation for skill-based recommendations.

2. **Word Embeddings using FastText**: To enrich the representation of words and phrases in the skillset keywords,
   ProRecom Backend employs FastText pretrained word embeddings. This embedding technique captures semantic
   relationships and improves the quality of clustering and matching.

3. **Clustering using KMeans**: The backend utilizes the KMeans clustering algorithm from scikit-learn to group similar
   projects and job seekers based on their skillset characteristics. Clustering helps organize data into meaningful
   groups, enhancing the accuracy of recommendations.

4. **Matching and Ranking using Cosine Similarities**: ProRecom Backend employs cosine similarities to perform matching
   and ranking between projects and job seekers. By measuring the similarity between skillset vectors, the backend
   provides highly relevant and accurate project recommendations for job seekers and candidate recommendations for
   companies.

5. **Push Notifications**: To keep users informed and engaged, ProRecom generates notifications for every relevant
   action,
   status update, or response. Job seekers and companies receive real-time notifications about project applications,
   invitations, and other activities, ensuring timely communication and updates.

### How it Works

1. **Skillset Keyword Extraction**: When job seekers create profiles and update skillsets, ProRecom Backend processes
   the
   data and extracts relevant skillset keywords. The backend's advanced algorithm analyzes the textual information to
   identify skills and expertise, creating a skillset representation.

2. **Word Embeddings**: To enhance the quality of skillset representations, ProRecom Backend utilizes FastText
   pretrained word embeddings. This technique converts skillset keywords into dense vector representations, capturing
   semantic relationships and context.

3. **Clustering**: The backend employs the KMeans clustering algorithm to group projects and job seekers based on their
   skillset characteristics. This clustering process organizes similar entities into clusters, enabling efficient
   matching and recommendation.

4. **Matching and Ranking**: ProRecom Backend calculates cosine similarities between skillset vectors of projects and
   job seekers. The higher the cosine similarity, the more similar the skillsets, resulting in better matching and
   ranking. This process generates accurate project recommendations for job seekers and candidate recommendations for
   companies.

## Technologies

- **Backend Framework**: FastAPI
- **GraphQL**: Strawberry GraphQL
- **Database**: SQLite

## Features

- GraphQL API
- Skillset Keyword Extraction
- Word Embeddings using FastText
- Clustering using KMeans
- Matching and Ranking using Cosine Similarities
- Database Management
- Authentication and Authorization
- Push Notifications
- CRUD Operations
    - Profile
    - Projects
    - Project Applications

## Usage

ProRecom Backend serves as the foundation of the ProRecom application, providing the necessary data processing, skillset
extraction, clustering, and database operations. By leveraging advanced technologies and efficient GraphQL APIs, the
backend enables seamless communication with the frontend, empowering users with skillset-based project recommendations
and candidate matching capabilities.

For a complete understanding of the ProRecom project, including the frontend and backend components, kindly refer to the
[ProRecom Frontend Repository](https://github.com/hingfei/prorecom_frontend).

## Frontend Reference

For backend reference, kindly visit [ProRecom Frontend Repository](https://github.com/hingfei/prorecom_frontend).
