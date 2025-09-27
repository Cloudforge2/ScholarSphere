# ---- Build Stage ----
    FROM maven:3.9.6-eclipse-temurin-17 AS build
    
    # WORKDIR creates dir if it doesn't exist
    WORKDIR /app
    COPY pom.xml .

    # creates a dependency cache layer that can be reused if pom.xml doesn't change
    RUN mvn dependency:go-offline
    COPY src ./src

    # creates the final build artifact(jar file)
    RUN mvn clean package -DskipTests
    
    # ---- Run Stage ----
    FROM eclipse-temurin:17-jdk-alpine
    WORKDIR /app
    COPY --from=build /app/target/*.jar app.jar
    EXPOSE 8080
    ENTRYPOINT ["java","-jar","app.jar"]
