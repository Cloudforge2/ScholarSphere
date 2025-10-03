Of course. A good README is essential for any project. Here is a comprehensive `README.md` file that you can place in the root of your `SCRAPPY` project folder.

It includes the setup requirements, installation steps, detailed API documentation with examples, and other useful sections.

---

# Scrappy - OpenAlex to Neo4j Ingestor

> A Go-based web service that fetches academic data from the OpenAlex API and populates it into a Neo4g graph database.

This application provides a simple API to search for authors and their works, ingesting them and their relationships into Neo4j to build a connected graph of academic knowledge.

## Features

*   **Fetch by Name:** Find authors by their display name.
*   **Fetch Author Works:** Ingest all publications for a given author ID.
*   **Graph Creation:** Automatically creates `Author`, `Work`, and `Institution` nodes, along with `AUTHORED`, `CITES`, and `AFFILIATED_WITH` relationships.
*   **RESTful API:** Interact with the service through simple HTTP endpoints.

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
├── go.sum                // Dependency checksums.
└── README.md             // This file.
```

## 🚀 Getting Started

Follow these instructions to get the project running on your local machine.

### Prerequisites

You will need the following tools installed on your system:

*   **Go:** Version 1.18 or higher.
*   **Neo4j Database:** A running instance of Neo4j.
*   **Git:** For cloning the repository.
*   **curl:** For testing the API endpoints from the command line.

### Installation & Setup

1.  **Clone the Repository**
    ```sh
    git clone https://github.com/Cloudforge2/scrappy.git
    cd scrappy
    ```

2.  **Configure Environment Variables**
    Create a file named `.env` in the root of the project directory. Copy the contents of `.env.example` (if you have one) or use the template below and fill in your Neo4j database credentials.

    ```env
    # .env

    # Neo4j Database Credentials
    NEO4J_URI=neo4j://localhost:7687
    NEO4J_USERNAME=neo4j
    NEO4J_PASSWORD=your_super_secret_password
    ```
    *   **`NEO4J_URI`**: The Bolt URI for your database. For Aura, this will be `neo4j+s://...`.
    *   **`NEO4J_USERNAME`**: The username for your database (default is `neo4j`).
    *   **`NEO4J_PASSWORD`**: The password you set for your database.

3.  **Install Dependencies**
    Run `go mod tidy` to download all the necessary packages (like the Neo4j driver).
    ```sh
    go mod tidy
    ```

4.  **Run the Server**
    Execute the `main.go` application.
    ```sh
    go run ./cmd/main.go
    ```
    If successful, you will see a confirmation message, and the server will be running:
    ```
    Successfully connected to Neo4j
    Starting interactive API server on http://localhost:8080
    ```

## 📚 API Endpoints

The server runs on `http://localhost:8080`. All endpoints are available under the `/api` prefix.

---

### 1. Fetch and Save Author by Name

Fetches the first author matching a given name from OpenAlex, saves them and their affiliations to Neo4j.

*   **Endpoint:** `GET /api/fetch-author`
*   **Description:** Use this to find an author and get their OpenAlex ID.
*   **Query Parameters:**
    | Parameter | Type   | Description              | Required |
    | :-------- | :----- | :----------------------- | :------- |
    | `name`    | string | The name of the author.  | Yes      |

*   **Example Usage:**
    ```sh
    curl "http://localhost:8080/api/fetch-author?name=Yogesh%20Simmhan"
    ```

*   **Success Response (200 OK):**
    ```json
    {
      "message": "Author successfully fetched and saved",
      "id": "https://openalex.org/A5041794289",
      "displayName": "Yogesh Simmhan"
    }
    ```

---

### 2. Fetch and Save All Works by Author ID

Fetches all works for a given author's OpenAlex ID, saves each work, and creates the relationships (`AUTHORED`, `CITES`) in Neo4j.

*   **Endpoint:** `GET /api/fetch-works-by-author`
*   **Description:** Use an author's ID (found with the first endpoint) to ingest all their publications.
*   **Query Parameters:**
    | Parameter | Type   | Description                       | Required |
    | :-------- | :----- | :-------------------------------- | :------- |
    | `id`      | string | The author's full OpenAlex ID.    | Yes      |

*   **Example Usage:**
    ```sh
    # Use the ID found from the previous API call
    curl "http://localhost:8080/api/fetch-works-by-author?id=A5023896336"
    ```

*   **Success Response (200 OK):**
    ```json
    {
      "message": "Successfully fetched and processed works",
      "worksFetched": 25,
      "worksProcessed": 25
    }
    ```
    *(Note: The number of works fetched may vary).*


### 3. Fetch and Save Work by Name

Fetches the first work matching a given name/title from OpenAlex. It saves the work, its authors, and creates the relationships between them in Neo4j.

*   **Endpoint:** `GET /api/fetch-work`
*   **Description:** Use this to find a specific publication and ingest it and its authors into the graph.
*   **Query Parameters:**
    | Parameter | Type   | Description                        | Required |
    | :-------- | :----- | :--------------------------------- | :------- |
    | `name`    | string | The title or keywords for a work.  | Yes      |

*   **Example Usage:**
    ```sh
    curl "http://localhost:8080/api/fetch-work?name=Principia%20Mathematica"
    ```

*   **Success Response (200 OK):**
    ```json
    {
      "message": "Work and its authors successfully fetched and saved",
      "id": "https://openalex.org/W2042485966",
      "title": "Philosophiae Naturalis Principia Mathematica"
    }
    ```
---
