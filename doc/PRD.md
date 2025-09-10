 
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

[Data Sources: DBLP, ORCID, Google scholar] 
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
Graph nodes also include domain as a node. 
Agentic scraping for institute website to get professor’s profile, lab work, current events of department. 
D3.js for more diverse visualizations of the data 
 

12. Weekly Milestones 

Week Ending :Goals / Milestones 
Fri 12 Sep:
Project Proposal Presentation: Finalize scope, architecture, PRD, and tech stack. 
 
Fri 19 Sep:
Scraper development complete; basic dataset for faculty loaded. 
Fri 26 Sep: 
Neo4j schema designed; backend APIs for graph retrieval implemented. 
Fri 3 Oct: 
Frontend skeleton + Cytoscape.js graph integration; filters applied. 
Fri 10 Oct :
Midterm Review: 67% feature completion. Graph functional with filters and basic metadata display and AI summarization service integrated; paper and faculty summaries functional. 
 
 
Fri 17 Oct: 
Updation of features according to the midterm review. 
Fri 24 Oct: 
Testing of features: Unit testing, UI polish. 
Fri 31 Oct: 
Testing of features: Functional testing. 
Fri 7 Nov: 
Final Submission: Deployment verified on AWS. 
 
 
13. Responsibilities 

Paul – Scrape faculty/publication data, clean & aggregation, DB design/storage 
Ikshita - Build Spring Boot APIs, manage DB (Postgres/Neo4j), connect frontend. 
Annu - Implement UI (Thymeleaf/React), Cytoscape.js graph, filters & interactions. 
Kunal -Summarization for papers & faculty, optimize models, store results. 
 
