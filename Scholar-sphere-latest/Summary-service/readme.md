
# Enhanced Author and Paper Summary Service

This service provides advanced, multi-source, LLM-generated summaries for academic authors and papers. It leverages the OpenAlex, Unpaywall, and Semantic Scholar APIs to gather comprehensive data, and uses a Groq model to generate insightful summaries.

## Features

*   **Professor Summaries**: Get a detailed research summary for a professor by name.
*   **Paper Summaries by ID**: Generate a multi-source summary for a paper using its OpenAlex ID.
*   **Paper Summaries by Title**: Find a paper by its title and get a detailed summary.
*   **Multi-source Data Aggregation**: Gathers information from OpenAlex, Unpaywall, and Semantic Scholar for comprehensive analysis.
*   **LLM-Powered Summaries**: Utilizes a Large Language Model to generate human-like summaries of research work.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file in the root directory and add the following:
    ```
    GROQ_API_KEY="YOUR_GROQ_API_KEY"
    MAILTO_EMAIL="your.email@example.com"
    ```
    *   `GROQ_API_KEY`: Your API key for the Groq service.
    *   `MAILTO_EMAIL`: An email address to be used for polite API requests to OpenAlex.

## API Endpoints

The service exposes the following endpoints:

### 1. Get Professor Summary by Name

*   **Endpoint:** `/professors/summary/by-name`
*   **Method:** `GET`
*   **Description:** Generates a research summary for a professor by their full name.
*   **Query Parameters:**
    *   `name` (string, required): The full name of the author.
*   **Example Request:**
    ```bash
    curl -X GET "http://127.0.0.1:8000/professors/summary/by-name?name=Geoffrey+Hinton"
    ```
*   **Example Response:**
    ```json
    {
      "research_summary": "...",
      "papers_analyzed": [
        {
          "title": "...",
          "year": 2023,
          "citations": 1234,
          "sources": [
            "OpenAlex",
            "Unpaywall PDF",
            "Semantic Scholar"
          ]
        }
      ]
    }
    ```

### 2. Get Paper Summary by ID

*   **Endpoint:** `/paper/by-id`
*   **Method:** `GET`
*   **Description:** Generates a detailed, multi-source summary for a single paper by its OpenAlex ID.
*   **Query Parameters:**
    *   `paper_id` (string, required): The OpenAlex ID or full OpenAlex URL of the paper.
*   **Example Request:**
    ```bash
    curl -X GET "http://127.0.0.1:8000/paper/by-id?paper_id=W2177745701"
    ```
*   **Example Response:**
    ```json
    {
      "paper_info": {
        "id": "https://openalex.org/W2177745701",
        "title": "...",
        ...
      },
      "summary": "..."
    }
    ```

### 3. Get Paper Summary by Title

*   **Endpoint:** `/paper/by-title`
*   **Method:** `GET`
*   **Description:** Finds a paper by its title and generates a detailed, multi-source summary.
*   **Query Parameters:**
    *   `title` (string, required): The title of the paper to search for.
*   **Example Request:**
    ```bash
    curl -X GET "http://127.0.0.1:8000/paper/by-title?title=Attention+Is+All+You+Need"
    ```
*   **Example Response:**
    ```json
    {
      "paper_info": {
        "id": "https://openalex.org/W2753945155",
        "title": "Attention Is All You Need",
        ...
      },
      "summary": "..."
    }
    ```

## Core Logic

The service's core logic is divided into two main parts:

### Data Enrichment

1.  **Initial Fetch**: For a given author or paper, the service first fetches initial data from the OpenAlex API.
2.  **Concurrent Enrichment**: It then concurrently fetches additional data from other sources:
    *   **Unpaywall**: To get the full text of the paper from a PDF, if available.
    *   **Semantic Scholar**: To get the abstract and TLDR (Too Long; Didn't Read) summary.
3.  **Deduplication**: The gathered content from all sources is deduplicated to avoid redundant information.

### Summarization

1.  **LLM-Powered Generation**: The enriched and deduplicated content is then passed to a Large Language Model (LLM) via the Groq API.
2.  **Structured Summaries**: The LLM is prompted to generate a structured summary with sections like "Background", "Main Contribution", "Methodology", "Results/Findings", and "Implications/Impact".
3.  **Fallback Mechanism**: If the LLM fails to generate a summary, a fallback mechanism provides a simple excerpt of the available content.