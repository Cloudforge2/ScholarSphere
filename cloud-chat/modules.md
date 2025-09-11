# Modules & Code Structure

**Project:** Cloud-based Chat Bot
**Version:** 0.1 (Draft)
**Date:** 2025-08-31

---

## 1. Overview

The chatbot system will support **basic person-to-person messaging**:

* Users are registered and available immediately.
* A user can send a message to another user.
* The receiver can view messages instantly (on refreshing their inbox).
* UI remains minimal — plain form and message list.

We will divide the system into four main modules:

1. **User Module** – manages users (create, list, lookup).
2. **Message Module** – handles message sending and retrieval.
3. **Chat Controller** – exposes REST APIs for frontend interaction.
4. **Frontend (Thymeleaf UI)** – simple web interface for chat.

---

## 2. Module Breakdown

### 2.1 User Module

**Purpose:** Manage user details (ID, username).

**Components:**

* `User` entity – represents a single user.
* `UserService` – business logic for creating and retrieving users.
* `UserController` – handles registration (POST) and returns success page.
* `PageController` – serves the registration form page (GET).

**Functions:**

public User createUser(String username);
public User getUser(Long id);
public List<User> getAllUsers();

---

### 2.2 Message Module

**Purpose:** Send and fetch messages between users.

**Components:**

* `Message` entity – stores message details (id, sender, receiver, content, timestamp).
* `MessageService` – logic for saving and retrieving messages.
* Integrated with `UserService` for sender/receiver validation.

**Functions:**

public Message sendMessage(Long fromUserId, Long toUserId, String content);
public List<Message> getInbox(Long userId);

---

### 2.3 Chat Controller

**Purpose:** Connect frontend with backend services.

**Components:**

* `ChatController` – REST API endpoints for sending messages and retrieving inbox.

**Endpoints:**

* `POST /chat/send` – send message.
* `GET /chat/inbox/{userId}` – fetch user inbox.

---

### 2.4 Frontend (Thymeleaf UI)

**Purpose:** Provide user-facing interface for chat and registration.

**Components:**

* `index.html` – home page.
* `register.html` – user registration form.
* `chat.html` – chat interface (send/receive messages).
* `style.css` – basic styling.
* `chat.js` – handles sending messages and refreshing inbox.

**Flow:**

1. User registers → redirected to chat page.
2. User enters IDs and sends message.
3. Inbox reloads via JS and fetch API.

---

## 3. Directory Structure

src/main/java/com/example/demo
│
├── Controllers
│   ├── ChatController.java
│   ├── UserController.java
│   └── PageController.java
│
├── Model
│   ├── User.java
│   └── Message.java
│
├── Service
│   ├── UserService.java
│   └── MessageService.java
│
├── repository
│   └── UserRepository.java
│
└── DemoApplication.java

src/main/resources
├── templates
│   ├── index.html
│   ├── register.html
│   ├── register_success.html
│   └── chat.html
├── static
│   ├── css/style.css
│   └── js/chat.js
└── application.properties

---

## 4. Future Extensions

* Add authentication (login/logout).
* Enable real-time chat using WebSockets.
* Persist messages in a relational DB (Postgres/MySQL).
* Add group chat and file sharing.
