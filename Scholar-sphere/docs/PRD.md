 
ScholarSphere: Cloud-based research knowledge hub 

Project Timeline: 12 Sep – 7 Nov 2025 

Technologies:  Spring Boot, Thymeleaf / React.js, Neo4j/ Postgres, Cytoscape.js, opensource LLM, AWS 

Members: Ikshita, Anu, Kunal, Paul 

1. Purpose 

Researchers at IISc often struggle to: 

Explore publication of faculty (who worked with whom, in what years). 
Quickly assess through summarization whether a paper is relevant without reading it fully. 
Explore faculty profiles easily through profile summarization. 
 

Objective: 
Develop a cloud-hosted web application that aggregates faculty publication data, visualizes faculty bibliography, and provides AI-powered summarization of papers and faculty profiles. 

 

2. Scope & Goals 

In Scope (MVP): 

Periodic Scrape publication metadata from DBLP, ORCID, Google Scholar etc.  
Build a knowledge graph representing authors, papers, and co-authorships. 
Interactive graph visualization with filters: year, professor, department, etc. 
AI-powered summaries: 
    Paper summary ( abstract-style). 
    Faculty profile summary ( derived from publications and biography from orcid id, Google Scholar, etc). 
Deploy on AWS EC2 with GitHub Actions CI/CD. 


Long-Term Functionality:

Metadata for Dead Nodes – Retain and display metadata even for inactive or missing nodes (e.g., publications removed from source, incomplete faculty profiles).
Graph Expansion – Support additional graphs such as:
    Professor collaboration networks.
    Domains and categories of research papers.
Beyond IISc Faculty – Extend ScholarSphere to include faculty from other universities and institutes, enabling cross-institute collaboration exploration.


Non-Goals : 

Automated download of restricted/full PDFs. 
Uploading new papers by users. 
No recommendation based on collaboration patterns. 
Not including paper-to-paper citation graphs. 


Assumptions :

Sufficient open-access data available from DBLP/ORCID /Google Scholar/Institute website. 
Sufficient open-source scraping tools are available for DBLP/ORCID /Google Scholar/Institute website. 
Summarization can be done effectively from abstracts and metadata if PDFs are unavailable. 
First test the open-source LLM/proprietary LLM on IISC servers, then after testing deploy it on AWS EC2. 
 

3. Functional Requirements 

3.1 Data Ingestion :

Scrape faculty and publication metadata (title, year, authors, conference). 
Validate and clean data. 
Store in Neo4j as nodes and relationships.

3.2 Graph Service / API :

REST endpoints: 
    /api/graph?professor=X&year=Y&dept=Z → JSON nodes & edges for visualization. 
    /api/search?professorName=... → search for professor. 
    /api/paper/{id} → metadata + summary. 
    /api/faculty/{id} → metadata + summary. 
Apply filters dynamically: year, professor, department. 

3.3 Visualization :

Frontend: Cytoscape.js or D3.js integrated via Thymeleaf or React.js. 
Graph features: 
    Node types: Professor (blue), Paper (green). 
    Clicking on node displays metadata and summary. 
Filters: Year, professor, department. 

3.4 Summarization :

Paper summary:  Abstract-style. 
Faculty summary: Key research areas + recent work overview. 
save summaries in DB to reduce repeated API calls. 

3.5 Performance & Scalability :

Use incremental loading or lazy-load paper nodes to optimize graph rendering. 
Backend queries optimized with Neo4j indexes on author names and paper IDs. 
 

4. Non-Functional Requirements 

Usability: Simple UI, clear legends, tooltips for nodes and edges. 
Availability: Application uptime ≥ 95% during demo/test period. 
Maintainability: Modular backend services (scraper, graph, summarizer). 
Portability: Dockerized services for easy deployment. 
 

5. Architecture Overview 

High-Level Architecture: 

[Data Sources: DBLP, ORCID, etc] 
        ↓ 
 [Scraper Service ] 
        ↓ 
     [Neo4j Graph DB, Postgres DB] 
        ↓ 
 [Graph Service & Summarization API] 
        ↓ 
[Frontend: Thymeleaf / React + Cytoscape.js] 
        ↓ 
      [User Interaction] 
 

Technology Stack: 

Backend: Spring Boot (REST APIs) 
Frontend: Thymeleaf / React.js, Cytoscape.js 
Database: Neo4j (graph), Postgres for summary storage 
AI Summarization: Open source LLM/ Proprietary LLM 
Hosting: AWS EC2 (backend) 
CI/CD: GitHub Actions 
 

6. Data Management / Storage 

Neo4j: stores nodes (Author, Paper) and edges . 
Metadata fields: 
    Author: name, department, profile. 
    Paper: title, year, conference, authors. 
Summaries: stored in PostgreSQL table. 
 

7. Security & Privacy 

Only store public metadata, no personal or confidential info. 
Minimal access: read-only scraping and graph exploration. 
Login access control for researchers and professors. 
Optional: API rate-limiting to prevent abuse. 
 

8. Deployment & Operations 

Dockerized backend services + frontend. 
GitHub Actions CI/CD: build → test → deploy to AWS EC2. 
Optional auto-scaling EC2 instance for increased load. 
 

9. Acceptance Criteria 

User can search IISc faculty and view a working bibliographic graph. 
Filters (year, conference, department, etc) and  update the graph correctly. 
Clicking a paper node shows metadata + AI-generated summary. 
Clicking a faculty node shows metadata + faculty summary. 
Application deployed on AWS. 
 

10. Testing Plan 

Unit tests: Scraper, API endpoints, summarization microservice. 
Integration tests: API → Frontend JSON → Cytoscape rendering. 
Performance tests: Graph rendering with full dataset. 
User acceptance tests: 
    Verify filters work correctly. 
    Check metadata and summaries display accurately. 
    Confirm deployment accessibility. 

11. Future Enhancement 
Agentic scraping for institute website to get professor’s profile, lab work, current events of department. 
D3.js for more diverse visualizations of the data 
 

12. Weekly Milestones 

Week 1 (12–18 Sep): 
    Finalize scope, PRD, and tech stack.
    Set up project repo, GitHub Actions initial pipeline.
    Begin scraper prototype for DBLP (basic author → papers).

Week 2 (19–26 Sep):
    Extend scraper to ORCID, integrate with cleaning/validation module.
    Draft Neo4j schema (Author, Paper, Co-author relationships).
    Draft Postgres schema for summaries.
    Load initial dataset into Neo4j.

Week 3 (27 Sep – 3 Oct):
    Implement Spring Boot API stubs (/api/graph, /api/faculty, /api/paper).
    Connect APIs to Neo4j/Postgres.
    Build test dataset queries for validation.

Week 4 (4–10 Oct):
    Integrate AI summarizer (abstract → short summary).
    Add faculty profile summary (from ORCID + Google Scholar).
    Write unit tests for scraper, APIs, summarizer.
    Midterm Review checkpoint: base features demo.

Week 5 (11–17 Oct):
    Frontend skeleton: React/Thymeleaf layout.
    Integrate Cytoscape.js with backend API data.
    Implement graph rendering of sample dataset.

Week 6 (18–24 Oct):
    Add filters (year, department, professor) to visualization.
    Persist summaries in Postgres (reduce repeated API calls).
    Perform integration testing (scraper → DB → API → frontend).

Week 7 (25–31 Oct):
    Implement incremental/lazy loading for graph visualization.
    Add Neo4j indexes for query optimization.
    Conduct system testing with extended dataset (10–15 professors).

Week 8 (1–7 Nov):
    Full dataset ingestion and performance testing.
    UI polish: tooltips, legends, accessibility features.
    Prepare system testing report.

Week 9 (8–14 Nov):
    Dockerize backend + frontend services.
    Finalize GitHub Actions CI/CD → AWS EC2.
    Conduct pre-deployment load testing.

Week 10 (15–21 Nov):
    User Acceptance Testing (faculty/researchers demo).
    Fix UAT feedback, final polish.
    Final presentation + submission. 
 
 
13. Responsibilities 

Paul – Scrape faculty/publication data, clean & aggregation, DB design/storage 
Ikshita - Build Spring Boot APIs, manage DB (Postgres/Neo4j), connect frontend. 
Annu - Implement UI (Thymeleaf/React), Cytoscape.js graph, filters & interactions. 
Kunal -Summarization for papers & faculty, optimize models, store results. 
 
