# Build stage
FROM maven:3.9.3-eclipse-temurin-20 AS builder
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests

# Runtime stage
FROM eclipse-temurin:20-jre
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8082 
ENTRYPOINT ["java", "-jar", "app.jar"]
