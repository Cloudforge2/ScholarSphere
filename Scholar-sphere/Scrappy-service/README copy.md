Of course. It's an excellent idea to update the documentation to reflect the significant architectural improvements you've made. The application is far more robust and feature-rich than the original version.

This updated README includes:
*   A new **Graph Schema** section to showcase the rich, hierarchical model you've built.
*   Accurate endpoint names and `curl` commands.
*   A clear explanation of the **asynchronous ingestion** process for the main endpoint, including the `202 Accepted` response.
*   A recommended workflow for users.

Here is the complete, updated `README.md` file.

---

# Scrappy - OpenAlex to Neo4j Knowledge Graph Ingestor

A Go-based web service that fetches academic data from the OpenAlex API and populates it into a rich, hierarchical Neo4j graph database.

This application provides a simple API to search for authors and their works, ingesting them and their relationships into Neo4j. It's designed for performance, using asynchronous background processing and efficient bulk database operations to build a deeply connected graph of academic knowledge.

## Features

*   **Rich Graph Model:** Creates a hierarchical graph of `Topics`, `Subfields`, `Fields`, and `Domains`, not just a flat list of concepts.
*   **Asynchronous Ingestion:** The main data ingestion endpoint immediately returns a response and processes large numbers of publications in the background, preventing timeouts and creating a better user experience.
*   **Bulk Database Operations:** Saves works in large batches using a single Cypher query, dramatically improving performance and reducing network load.
*   **Comprehensive Data:** Ingests Authors, Works, Institutions, and Venues, creating critical relationships like `AUTHORED`, `CITES`, `PUBLISHED_IN`, and `HAS_TOPIC`.
*   **RESTful API:** Interact with the service through simple, well-defined HTTP endpoints.

## Graph Schema

The service builds the following model in your Neo4j database:

**Nodes:**
*   `(:Author)`
*   `(:Work)`
*   `(:Institution)`
*   `(:Venue)` - A journal or conference.
*   `(:Topic)`
*   `(:Subfield)`
*   `(:Field)`
*   `(:Domain)`

**Relationships:**
*   `(:Author)-[:AUTHORED {position, institutionIds}]->(:Work)`
*   `(:Author)-[:AFFILIATED_WITH]->(:Institution)`
*   `(:Author)-[:HAS_TOPIC {paperCount}]->(:Topic)`
*   `(:Work)-[:CITES]->(:Work)`
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
│   │   └── config.go     // Configuration loader for environment variables.
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
*   **Git:** For cloning the repository.

### Installation & Setup

1.  **Clone the Repository**
    ```sh
    git clone https://github.com/Cloudforge2/scrappy.git
    cd scrappy
    ```

2.  **Configure Environment Variables**
    Create a file named `.env` in the root of the project. Fill in your Neo4j database credentials.

    ```env
    # .env
    NEO4J_URI=neo4j://localhost:7687
    NEO4J_USERNAME=neo4j
    NEO4J_PASSWORD=your_super_secret_password
    ```

3.  **Install Dependencies**
    ```sh
    go mod tidy
    ```

4.  **Run the Server**
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

The primary ingestion endpoint. Fetches an author and **all** of their works, then saves the complete graph to Neo4j. It processes an initial batch synchronously and the rest in the background.

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

---

### 3. Get Recent Works for an Author (Read-Only)

Fetches the 30 most highly-cited works for an author. **Does not save to the database.**

*   **Endpoint:** `GET /api/fetch-recent-works/`
*   **Query Parameters:**
    | Parameter | Type   | Description                    | Required |
    | :-------- | :----- | :----------------------------- | :------- |
    | `id`      | string | The author's full OpenAlex ID. | Yes      |
*   **Example Usage:**
    ```sh
    curl "http://localhost:8083/api/fetch-recent-works/?id=A5041794289"
    ```
*   **Success Response (200 OK):** A JSON array of up to 30 `Work` objects.

---

### Recommended Workflow

1.  **Discover:** Use the `/api/fetch-authors-by-name` endpoint to find the correct OpenAlex ID for an author you are interested in.
2.  **Ingest:** Use the `/api/fetch-author-by-id` endpoint with the ID you found. You will get an immediate `202 Accepted` response.
3.  **Monitor:** Check the server's console logs to see the progress of the background ingestion task.
4.  **Query:** Once the background task is complete, query your Neo4j database to explore the newly created knowledge graph for that author.