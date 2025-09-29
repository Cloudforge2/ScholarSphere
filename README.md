
# ScholarSphere Backend


## Development Progress

This project is currently under active development. Here is a summary of the current status and the planned next steps.

### Completed
- [x] **Neo4j Entities:**
  - [x] `Author` entity
  - [x] `Institution` entity
  - [x] `Work` entity
- [x] Initial project setup with Spring Boot and Maven.
- [x] `Dockerfile` for containerization.

### Next Steps
- [ ] **Data Access Layer:**
  - [x] Implement Getter and Setter methods for all entities.(used lombok)
  - [x] Create Spring Data Neo4j repositories for `Author`, `Institution`, and `Work`.
- [ ] **Service Layer:**
  - [ ] Author services
  - [ ] Work services
  - [ ] Intitution services
- [ ] **API Layer:**
  - [ ] Author endpoints
  - [ ] Work endpoints
  - [ ] Instition endpoints
- [ ] **Testing:**
  - [ ] Write unit tests for the service layer.
  - [ ] Write integration tests for the repository and controller layers.

## Prerequisites

Before you begin, ensure you have the following installed:
*   Java 17 (or your required version)
*   Apache Maven 3.8+
*   Docker Desktop or Docker Engine
*   A running Neo4j database instance

## Configuration

Before running the application, you need to configure the connection to your Neo4j database.

1.  Open the configuration file located at: `src/main/resources/application.yml`
2.  Update the `spring.neo4j` properties with your database URI and credentials.

**Example `application.yml`:**
```yaml
spring:
  neo4j:
    uri: bolt://localhost:7687
    authentication:
      username: neo4j
      password: your_secret_password
```
> **Note:** Make sure to replace `your_secret_password` with your actual Neo4j password. If you are running Neo4j in a Docker container, ensure the URI is accessible from the application container (e.g., use your host IP or Docker's internal networking).

---

## Development: Running Locally

For local development and quick testing, you can run the application directly using the Spring Boot Maven plugin.

1.  Open your terminal in the project's root directory.
2.  Run the following command:

```bash
mvn spring-boot:run
```

This command will compile the project, start the embedded web server, and run the application. By default, the application will be available at **`http://localhost:8080`**.

---

## Production: Building and Running

For production deployments, the recommended approach is to build a self-contained executable JAR and run it either directly or inside a Docker container.

### Option 1: Building and Running an Executable JAR

#### Step 1: Build the Executable JAR

Run the following Maven command to build the project:

```bash
mvn clean package
```
*   `clean`: Removes any previous build artifacts from the `target` directory.
*   `package`: Compiles your code and packages it into a single, executable "uber-jar" file. The `spring-boot-maven-plugin` handles the process of including all necessary dependencies.

The final JAR file will be located in the `target/` directory.

#### Step 2: Run the Packaged JAR

Once the JAR has been successfully created, you can run it using a standard `java` command:

```bash
java -jar target/your-application-name-0.0.1-SNAPSHOT.jar
```
> **Note:** Remember to replace `your-application-name-0.0.1-SNAPSHOT.jar` with the actual name of the JAR file generated in your `target` directory.

### Option 2: Building and Running with Docker

This project includes a multi-stage `Dockerfile` for creating optimized, production-ready container images. This approach ensures the final image is small, secure, and contains only the necessary Java runtime and the application JAR.

#### The Dockerfile
```dockerfile
# ---- Build Stage ----
# Use a Maven image to build the application JAR
FROM maven:3.9.6-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline
COPY src ./src
RUN mvn clean package -DskipTests

# ---- Run Stage ----
# Use a minimal JRE image for the final, small container
FROM eclipse-temurin:17-jdk-alpine
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java","-jar","app.jar"]
```

#### Step 1: Build the Docker Image

The following command will build the Docker image using the `Dockerfile`. The `-t` flag tags the image with a memorable name (e.g., `my-project-name`).

```bash
docker build -t your-project-name .
```
> **Note:** The `.` at the end of the command is important; it specifies the current directory as the build context.

#### Step 2: Run the Docker Container

Once the image is built, you can run it as a container. The `-p 8080:8080` flag maps port 8080 on your local machine to port 8080 inside the container.

```bash
docker run -p 8080:8080 your-project-name
```

Your containerized application is now running and accessible at **`http://localhost:8080`**.