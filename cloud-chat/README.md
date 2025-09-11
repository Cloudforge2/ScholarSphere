# Chatbot_dummy (Spring Boot + Thymeleaf + WebSocket + H2 DB)

A simple WhatsApp-like chat application built using **Spring Boot 3**, **Thymeleaf**, **WebSocket (STOMP)**, and **H2 in-memory database**.  
It supports real-time messaging, user login, and a chat UI styled with CSS.

---

## Features
- User signup & login  
- Real-time chat with WebSocket (no refresh needed)  
- In-memory H2 database (resets on restart)  
- Responsive UI with Thymeleaf templates  

---

## Tech Stack
- **Backend:** Spring Boot (Web, WebSocket, Security, JPA, H2 DB)  
- **Frontend:** Thymeleaf + CSS  
- **Database:** H2 (in-memory)  

---

## Getting Started

### Prerequisites
- Java 17+  
- Maven 3.9+  

### Run the project
```bash
# Clone the repository
git clone https://github.com/your-username/whatsapp-clone.git
cd whatsapp-clone

# Build the project
mvn clean install

# Run the Spring Boot app
mvn spring-boot:run
