# Project Requirements Document (PRD)
**Project:** Cloud-based Chat Bot   
**Version:** 0.1 (Draft)  
**Date:** 2025-08-31  

---

## 1. Overview
The goal is to develop a cloud-based chat bot application that provides a browser-based user interface and is hosted on cloud virtual machines. The bot will support basic conversational features and ensure secure connectivity. The system will be containerized using Docker and implemented with **Spring Boot** for backend services and **Thymeleaf** for frontend templating.

---

## 2. Goals & Non-Goals
### Goals
- Provide a simple, intuitive browser-based chat UI.
- Enable conversational interaction with a rule-based chatbot.
- Host backend server on a cloud VM within free tier limits.
- Containerize the application for consistent deployment using Docker.
- Ensure secure connectivity (e.g., HTTPS, API tokens).

### Non-Goals
- Not aiming for advanced AI/LLM chatbot in the first release.
- Not implementing enterprise-grade authentication/authorization in initial version.
- Not building mobile-native apps (browser only).

---

## 3. Target Users
- **Students / developers** exploring chatbot development on the cloud.
- **Small businesses / demo users** who need a simple chatbot prototype.
- **Educators** using the chatbot as a teaching/demo tool.

---

## 4. User Stories
1. As a **user**, I want to access a chatbot in my browser, so I can interact with it easily without setup.
2. As a **developer**, I want the chatbot hosted in the cloud, so I don’t have to run it locally.
4. As a **developer**, I want to it deploy using Docker, so I can ensure portability and consistency across environments.

---

## 5. Features
### 5.1 Browser-based UI
- Built with Thymeleaf templates (HTML, CSS, JS).
- Simple chat interface (input box, message history).
- Responsive design (desktop and mobile browser friendly).

### 5.2 Backend (Spring Boot)
- REST endpoints for chat interactions.
- Rule-based chatbot responses (initially keyword-based).

### 5.3 Hosting & Infrastructure
- Deployment on Cloud VM (AWS, GCP, or Azure free tier).
- Application containerized via Docker.
- Expose ports securely for browser access.

---

## 6. Technical Requirements
- **Language/Framework:** Java 17+, Spring Boot, Thymeleaf.
- **Frontend:** Thymeleaf templates + basic JS for async requests.
- **Containerization:** Dockerfile with openjdk:17 base image.
- **Database (Optional):** In-memory (H2) for storing chat history (MVP can skip persistence).
- **Cloud Hosting:** VM within free tier (e.g., AWS EC2 t2.micro).
- **Security:** HTTPS (customer-managed).

---

## 7. Constraints
- Must run within free-tier cloud VM resources (low memory/CPU).
- Keep dependencies lightweight to avoid resource exhaustion.
- Avoid heavy NLP libraries in MVP.

---

## 8. Success Metrics
- User can connect to chatbot via browser from internet.
- User can send and receive chat messages reliably.
- Application runs stably within free-tier VM constraints.
- Secure (encrypted) communication is enabled.

---

## 9. Future Enhancements (v2+)
- Multi-user sessions with persistent chat history.
- Integration with NLP APIs (Dialogflow, Rasa, or LLMs).
- Support for plugins (FAQ bot, customer support integration).
- Mobile app wrappers for iOS/Android.

---


## 10. Open Questions
- Which cloud provider will be used (AWS, GCP, Azure)?
- Should chat history be stored (H2 vs external DB)?
- What chatbot logic to start with (rules, regex, small NLP)?
- How should authentication be handled in MVP?

---
