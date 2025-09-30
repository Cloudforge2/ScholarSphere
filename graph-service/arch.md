1. Technology Stack

    *Backend Services:*

        - Graph Service: Spring Boot (Java), Spring Data Neo4j.
        - Summarization Service: FastAPI (Python), LangChain, Celery.
        - Data Scraper: Python (maybe).
        - API Gateway/Search: Spring Boot (Java), Spring Cloud Gateway.

    *Databases:*

        - Graph Database: Neo4j (for authors, papers, and relationships).
        - Relational Database: PostgreSQL (for storing faculty bios and LLM-generated summaries).

    *Frontend:*

        - Framework: React.js/Thymeleaf.
        - Visualization Library: Cytoscape.js.

    *Cloud & DevOps:*

        - Cloud Provider: AWS (EC2).
        - Containerization: Docker.
        - CI/CD: GitHub Actions.

---

2. Architecture Diagram

The system uses a microservices architecture with an API Gateway as the single entry point for the frontend.

- **Client (React.js Frontend):** The user's web application. It sends requests to the API Gateway.  
- **API Gateway:** Routes incoming requests to the appropriate backend service and handles search queries.  
- **Graph Service:** A Spring Boot application that queries the Neo4j graph database for data about professors and papers.  
- **Summarization Service:** A service that uses an open-source LLM to create summaries and stores them in a PostgreSQL database.  
- **Data Scraper:** A separate process that scrapes and ingests data into the Neo4j and PostgreSQL databases.  
- **Neo4j:** Stores the knowledge graph (nodes and relationships).  
- **PostgreSQL:** Stores supplementary data like LLM-generated summaries and faculty biographies.  

---

3. Sequence Diagrams

**User Views Co-Authorship Graph**

```mermaid
sequenceDiagram
    participant User as User
    participant Frontend as Frontend (React.js)
    participant APIGateway as API Gateway/Search Service
    participant GraphService as Graph Service
    participant Neo4j as Neo4j DB

    User->>Frontend: Clicks 'View Graph' for Professor X
    Frontend->>APIGateway: GET /api/graph?professor=X
    APIGateway->>GraphService: GET /api/graph?professor=X
    GraphService->>Neo4j: Cypher Query (MATCH ... RETURN ...)
    Neo4j-->>GraphService: JSON of Nodes & Edges
    GraphService-->>APIGateway: JSON of Nodes & Edges
    APIGateway-->>Frontend: JSON of Nodes & Edges
    Frontend->>User: Renders graph with Cytoscape.js


**User Views Paper Summary**

sequenceDiagram
    participant User as User
    participant Frontend as Frontend (React.js)
    participant APIGateway as API Gateway/Search Service
    participant SummaryService as Summary Service
    participant Postgres as PostgreSQL DB
    participant LLM as Open Source LLM

    User->>Frontend: Clicks on a paper node
    Frontend->>APIGateway: GET /api/paper/{paperId}
    APIGateway->>SummaryService: GET /api/paper/{paperId}
    SummaryService->>Postgres: Check for existing summary
    alt Summary Exists
        Postgres-->>SummaryService: Summary data
    else Summary Does Not Exist
        Postgres-->>SummaryService: No data
        SummaryService->>LLM: Request new summary
        LLM-->>SummaryService: Generated summary
        SummaryService->>Postgres: Save new summary
    end
    SummaryService-->>APIGateway: Summary & metadata
    APIGateway-->>Frontend: Summary & metadata
    Frontend->>User: Displays paper details & summary
