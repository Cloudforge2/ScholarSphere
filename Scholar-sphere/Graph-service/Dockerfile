# ---- Build Stage ----
    FROM maven:3.9.6-eclipse-temurin-17 AS build
    WORKDIR /app
    COPY pom.xml .
    RUN mvn dependency:go-offline
    COPY src ./src
    RUN mvn clean package -DskipTests
    
    # ---- Run Stage ----
    FROM eclipse-temurin:17-jdk-alpine
    WORKDIR /app
    COPY --from=build /app/target/*.jar app.jar
    EXPOSE 8082
    ENTRYPOINT ["java","-jar","app.jar"]
    # To run the application, use the command: docker run -p 8080:8080 <image_name>