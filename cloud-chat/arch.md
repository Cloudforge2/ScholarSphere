# Architecture Document

**Project:** Cloud-based Chat Bot
**Version:** 1.0
**Date:** 2025-08-31

---

## 1. Technologies

* **Backend:** Spring Boot (Java 17, MVC + REST)
* **Frontend:** Thymeleaf templates with HTML/CSS/JavaScript
* **Database:** H2 (in-memory, dev) / MySQL or PostgreSQL (prod) for storing users and messages
* **Containerization:** Docker (`openjdk:17-jdk-slim` base image, Maven build inside container)
* **Hosting:** Cloud VM (AWS EC2 / GCP Compute Engine / Azure VM)
* **Security:** HTTPS (Let’s Encrypt or self-signed certificate)

---

## 2. High-Level Architecture

flowchart TD
    A[User Browser] <--> B[Spring Boot App]
    B <--> C[(Database - Users + Messages)]
    B --> D[Docker Container]
    D --> E[Cloud VM / Deployment Environment]


---

## 3. Request Flow


sequenceDiagram
    participant U as User (Browser)
    participant S as Spring Boot App
    participant DB as Database

    U->>S: Register user (POST /register)
    S->>DB: Save user
    DB-->>S: Confirmation
    S-->>U: Redirect to /chat?username=...

    U->>S: Send message (POST /chat/send)
    S->>DB: Persist message (from, to, content)
    DB-->>S: Save OK
    S-->>U: Acknowledge

    U->>S: Fetch inbox (GET /chat/inbox/{userId})
    S->>DB: Query messages for user
    DB-->>S: Return messages
    S-->>U: JSON response → rendered in chat.html


---

## 4. Components

### 4.1 Controllers

* **PageController**

  * Serves UI pages (`/`, `/chat`, `/register`) using Thymeleaf.
* **UserController**

  * Handles user registration (`POST /register`).
* **ChatController**

  * REST endpoints:

    * `POST /chat/send` – send message
    * `GET /chat/inbox/{userId}` – fetch inbox

### 4.2 Services

* **UserService** (optional abstraction)

  * Validate users exist before sending messages.
* **ChatService**

  * Store and retrieve chat messages.

### 4.3 Repository

* **UserRepository** – JPA repository for `User` entity.
* **MessageRepository** – JPA repository for `Message` entity.

### 4.4 Entities

* **User**

  * `id (Long)`
  * `username (String)`
* **Message**

  * `id (Long)`
  * `fromUserId (Long)`
  * `toUserId (Long)`
  * `content (String)`
  * `timestamp (LocalDateTime)`

---

## 5. Frontend

* **index.html** – home page (links to register or chat).
* **register.html** – registration form.
* **chat.html** – chat interface (send + inbox).
* **style.css** – simple styling.
* **chat.js** – handles AJAX calls for sending/fetching messages.

---

## 6. Deployment

1. Build Docker image:

   docker build -t chatbot-app .

2. Run with database:

   docker run -p 8080:8080 --add-host=host.docker.internal:host-gateway chatbot-app

3. Access at: `http://<VM-IP>:8080/`

---

## 7. Future Enhancements

* Add authentication & sessions (Spring Security).
* Persist chat history permanently (MySQL/Postgres).
* Group chat / multiple participants.
* Real-time messaging with WebSockets.
* UI improvements with Bootstrap/Tailwind.
