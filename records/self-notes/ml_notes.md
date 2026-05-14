# Machine Learning

Tags: #ml #ai #machinelearning #datascience

---

# What is Machine Learning?

Machine Learning (ML) is a field of AI where systems learn patterns from data instead of being explicitly programmed.

Core idea:

```text
Data -> Pattern Learning -> Predictions / Decisions
```

ML systems improve as they see more data.

---

# Types of Machine Learning

## Supervised Learning

Uses labeled data.

Examples:

* Spam detection
* House price prediction
* Stock movement classification

Algorithms:

* Linear Regression
* Logistic Regression
* Random Forest
* XGBoost
* Neural Networks

---

## Unsupervised Learning

Finds hidden structure in unlabeled data.

Examples:

* Customer segmentation
* Topic modeling
* Clustering

Algorithms:

* K-Means
* DBSCAN
* PCA
* Autoencoders

---

## Reinforcement Learning

Agent learns via rewards and penalties.

Examples:

* Robotics
* Game AI
* Trading agents

Core Concepts:

* Agent
* Environment
* Reward
* Policy

---

# ML Pipeline

```text
Data Collection
    ↓
Data Cleaning
    ↓
Feature Engineering
    ↓
Model Training
    ↓
Evaluation
    ↓
Deployment
    ↓
Monitoring
```

---

# Important Concepts

## Features

Input variables used by the model.

Example:

```python
age = 25
salary = 50000
```

---

## Labels

Ground truth values.

Example:

```python
house_price = 120000
```

---

## Training vs Testing

* Train set → learn patterns
* Test set → evaluate generalization

Common split:

```python
80% train
20% test
```

---

# Overfitting vs Underfitting

## Overfitting

Model memorizes training data.

Symptoms:

* High train accuracy
* Low test accuracy

Solutions:

* Regularization
* More data
* Dropout
* Simpler models

---

## Underfitting

Model too simple to learn patterns.

Solutions:

* Better features
* Larger model
* Longer training

---

# Evaluation Metrics

## Classification

* Accuracy
* Precision
* Recall
* F1 Score
* ROC-AUC

---

## Regression

* MAE
* MSE
* RMSE
* R²

---

# Deep Learning

Subset of ML using neural networks.

Important architectures:

* CNNs
* RNNs
* Transformers
* LSTMs

Applications:

* NLP
* Vision
* Audio
* Recommendation systems

---

# Embeddings

Embeddings convert data into dense vectors.

Used in:

* RAG
* Search
* Recommendation systems
* Semantic similarity

Example:

```python
text -> [0.12, -0.44, 0.91, ...]
```

---

# RAG (Retrieval-Augmented Generation)

Combines:

* retrieval systems
* vector search
* LLMs

Pipeline:

```text
Query
  ↓
Retriever
  ↓
Relevant Context
  ↓
LLM
  ↓
Generated Response
```

Related:

* [[Vector Databases]]
* [[Graph RAG]]
* [[Embeddings]]

---

# Common ML Libraries

## Python ML Stack

* NumPy
* Pandas
* Scikit-learn
* PyTorch
* TensorFlow
* XGBoost

---

# Vector Databases

Used for semantic retrieval.

Examples:

* FAISS
* Chroma
* Weaviate
* Pinecone

---

# Graph RAG Ideas

Graph RAG improves retrieval using:

* entities
* relationships
* knowledge graphs

Useful for:

* PKMS
* agentic systems
* reasoning

Related:

* [[Knowledge Graphs]]
* [[Neo4j]]
* [[Semantic Search]]

---

# Challenges in ML

* Data quality
* Hallucinations
* Bias
* Retrieval failures
* Long context handling
* Scalability

---

# Current Trends

* Multimodal AI
* Agentic systems
* Graph RAG
* Long-context memory
* Small language models
* Personalized AI systems

---

# Ideas

## PKMS + ML

Potential architecture:

```text
Documents
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector DB
    ↓
Graph Construction
    ↓
Hybrid Retrieval
    ↓
LLM Agents
```

---

# Questions

* How to improve retrieval quality?
* How to combine graph + vector retrieval?
* How should memory systems evolve?
* Can agents build dynamic knowledge graphs?

---

# References

* [[Graph RAG]]
* [[Embeddings]]
* [[Transformers]]
* [[Vector Search]]
* [[Knowledge Graphs]]
* [[Agents]]

---

Created: 2026-05-12
