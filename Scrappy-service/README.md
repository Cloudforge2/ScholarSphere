# Scrappy - OpenAlex to Neo4j Knowledge Graph Ingestor

A Go-based web service that fetches academic data from the OpenAlex API and populates it into a rich, hierarchical Neo4j graph database.

This application provides a simple API to search for authors and works, ingesting them and their relationships into Neo4j.

## Features

*   **Asynchronous Ingestion:** The main ingestion endpoint (`/api/fetch-author-by-id`) immediately returns a `202 Accepted` response and processes the majority of the author's publications in a background goroutine, preventing HTTP timeouts.
*   **Rich Graph Model:** Creates a hierarchical graph of `Topics`, `Subfields`, `Fields`, and `Domains` and connects them to both `Author` and `Work` nodes.
*   **Author Ingestion Flag:** Sets a `fullyIngested: true` property on the `Author` node in Neo4j only after all works (initial batch + background batch) have been processed.
*   **Comprehensive Data:** Ingests Authors, Works, Institutions, and Venues, creating critical relationships like `AUTHORED`, `PUBLISHED_IN`, and the hierarchical topic relationships.
*   **API for Discovery & Ingestion:** Separate endpoints for searching/discovery and full ingestion.

## Graph Schema

The service builds the following model in your Neo4j database:

**Nodes:**
*   `(:Author {id, displayName, fullyIngested})`
*   `(:Work {id, title, publicationYear, doi})`
*   `(:Institution {id, displayName})`
*   `(:Venue {id, displayName})` - A journal or conference.
*   `(:Topic {id, displayName})`
*   `(:Subfield {id, displayName})`
*   `(:Field {id, displayName})`
*   `(:Domain {id, displayName})`

**Relationships:**
*   `(:Author)-[:AUTHORED {position, institutionIds}]->(:Work)`
*   `(:Author)-[:AFFILIATED_WITH]->(:Institution)`
*   `(:Author)-[:HAS_TOPIC {paperCount}]->(:Topic)`
*   `(:Work)-[:PUBLISHED_IN]->(:Venue)`
*   `(:Work)-[:IS_ABOUT_TOPIC {score}]->(:Topic)`
*   `(:Topic)-[:IN_SUBFIELD]->(:Subfield)`
*   `(:Subfield)-[:IN_FIELD]->(:Field)`
*   `(:Field)-[:IN_DOMAIN]->(:Domain)`

## Project Structure

```
.
├── cmd/
│   └── main.go         // Main application entrypoint. Initializes and starts the server.
├── internal/
│   ├── api/
│   │   └── handler.go    // HTTP handlers that control the API logic.
│   ├── config/
│   │   └── config.go     // Configuration loader (not provided, assumed).
│   ├── domain/
│   │   └── model.go      // Go structs that model the data from OpenAlex.
│   ├── openalex/
│   │   └── client.go     // Client for making requests to the OpenAlex API.
│   └── storage/
│       └── neo4j.go      // Neo4j repository for all database queries and transactions.
├── .env                  // (You create this) Local environment variables.
├── go.mod                // Go module definitions.
└── README.md             // This file.
```

## 🚀 Getting Started


### Prerequisites

*   **Go:** Version 1.18 or higher.
*   **Neo4j Database:** A running instance of Neo4j.
<!-- *   **Git:** For cloning the repository. -->

### Installation & Setup

<!-- 1.  **Clone the Repository**
    ```sh
    git clone https://github.com/Cloudforge2/scrappy.git
    cd scrappy
    ``` -->

1. **Create a file named `.env` in the root of the project. Fill in your Neo4j database credentials.**

    ```env
    # .env
    NEO4J_URI=neo4j://localhost:7687
    NEO4J_USERNAME=neo4j
    NEO4J_PASSWORD=your_super_secret_password
    ```

2.  **Install Dependencies**
    ```sh
    go mod tidy
    ```

3.  **Run the Server**
    ```sh
    go run ./cmd/main.go
    ```
    You should see the server start on port 8083:
    ```
    Successfully connected to Neo4j
    Starting interactive API server on http://localhost:8083
    ```


## 📚 API Endpoints

The server runs on `http://localhost:8083`.

---

### 1. Find Authors by Name (Discovery)

Finds potential author matches from OpenAlex. This is a read-only endpoint used to discover an author's ID. **It does not save anything to the database.**

*   **Endpoint:** `GET /api/fetch-authors-by-name`
*   **Query Parameters:**
    | Parameter | Type   | Description             | Required |
    | :-------- | :----- | :---------------------- | :------- |
    | `name`    | string | The name of the author. | Yes      |
*   **Example Usage:**
    ```sh
    curl "http://localhost:8083/api/fetch-authors-by-name?name=Yogesh%20Simmhan"
    ```
*   **Success Response (200 OK):** An array of matching authors.
    ```json
    [
      {
        "id": "https://openalex.org/A5023896336",
        "displayName": "Yogesh Simmhan",
        "lastKnownInstitution": "Indian Institute of Science",
        "citedByCount": 3583,
        "updatedDate": "2024-07-29T17:15:15.580218",
        "orcid": "https://orcid.org/0000-0003-0130-3945"
      }
    ]
    ```

---

### 2. Ingest Author and All Works by ID (Asynchronous)

**The primary ingestion endpoint.** Fetches a full Author entity and **all** of their associated Work entities from OpenAlex.

*   **Synchronous Action:** The Author node and an initial batch of works (currently 30) are saved to Neo4j immediately.
*   **Asynchronous Action:** A background goroutine handles the ingestion of all remaining works.
*   **Post-Ingestion:** The `Author` node's `fullyIngested` property is set to `true` after the background process completes.

*   **Endpoint:** `GET /api/fetch-author-by-id`
*   **Query Parameters:**
    | Parameter | Type   | Description                    | Required |
    | :-------- | :----- | :----------------------------- | :------- |
    | `id`      | string | The author's full OpenAlex ID. | Yes      |
*   **Example Usage:**
    ```sh
    curl "http://localhost:8083/api/fetch-author-by-id?id=A5041794289"
    ```
*   **Success Response (202 Accepted):** An immediate confirmation that the job has started.
    ```json
    {
      "message": "Request accepted. Initial works are being processed. The rest will be ingested in the background.",
      "totalWorks": 258,
      "initialBatchSize": 30
    }
    ```

<!-- ---

### 3. Ingest Single Work by Name (Synchronous)

Searches for and ingests the **first** matching Work found by name. This is a synchronous operation.

*   **Action:** Creates the `Work` node, its associated `Author` nodes, `AUTHORED` relationships, `Venue`, and `Topic` hierarchy.
*   **Endpoint:** `GET /api/fetch-work-by-name`
*   **Query Parameters:** `name` (string, required) - The title of the work.
*   **Example Usage:**
    ```sh
    curl "http://localhost:8083/api/fetch-work-by-name?name=principia%20mathematica"
    ```
*   **Success Response (200 OK):** Confirmation of the successful save.

--- -->

### 3. Get Author's Works (Read-Only)

Fetches the **30 most highly cited** works for a given author from OpenAlex. **Does not save to the database.**

*   **Endpoint:** `GET /api/fetch-recent-works/`
*   **Query Parameters:** `id` (string, required) - The author's full OpenAlex ID.
*   **Example Usage:**
    ```sh
    curl "http://localhost:8083/api/fetch-recent-works/?id=A5041794289"
    ```
*   **Success Response (200 OK):** A JSON array of up to 30 `Work` objects.



<!-- ### 5. Get Author's Abstract Inverted Indexes (Read-Only)

Fetches abstract data (specifically the `abstract_inverted_index`) for the 30 most highly-cited works by an author, using a custom select query on the OpenAlex API. **Does not save to the database.**

*   **Endpoint:** `GET /api/fetch-abstracts/`
*   **Query Parameters:** `id` (string, required) - The author's full OpenAlex ID.
*   **Example Usage:**
    ```sh
    curl "http://localhost:8083/api/fetch-abstracts/?id=A5041794289"
    ```
*   **Success Response (200 OK):** A JSON array of simplified publication objects containing `title`, `publication_year`, `cited_by_count`, and the raw `abstract_inverted_index`. -->



## Recommended Workflow

1.  **Discover:** Use `/api/fetch-authors-by-name` to find the correct OpenAlex ID (e.g., `A5041794289`) for the author.
2.  **Ingest:** Use `/api/fetch-author-by-id?id=A5041794289`. Get the `202 Accepted` response.
3.  **Monitor:** Check the server logs for the "BACKGROUND SUCCESS" and final "**Author... marked as fully ingested in Neo4j**" messages.
4.  **Query:** Once ingestion is complete, use a Cypher query like `MATCH (a:Author {id: 'A5041794289'})-[r:AUTHORED]->(w:Work) RETURN a,r,w LIMIT 10` in Neo4j Browser to explore your new knowledge graph.