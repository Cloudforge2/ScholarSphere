package com.scholarsphere.graphservice.services;

import com.scholarsphere.graphservice.model.Paper;
import com.scholarsphere.graphservice.model.Professor;
import com.scholarsphere.graphservice.repository.ProfessorRepository;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.neo4j.core.Neo4jClient;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.schema.Relationship;
import org.springframework.stereotype.Service;
import org.neo4j.driver.Record;
import java.util.Optional;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class ProfessorService {

    private final ProfessorRepository professorRepository;
    private final Neo4jClient neo4jClient;

    @Autowired
    public ProfessorService(ProfessorRepository professorRepository, Neo4jClient neo4jClient) {
        this.professorRepository = professorRepository;
        this.neo4jClient = neo4jClient;
    }

    /**
     * Fetch a professor and their authored papers from Neo4j.
     *
     * @param id Professor ID
     * @return Professor with related papers (if found)
     */
    public Optional<Professor> getProfessorWithPapers(String id) {
        System.out.println("Fetching professor with ID: " + id);
        return professorRepository.findById(id);
    }
    /**
     * Fetch professors by their display name.
     *
     * @param name Professor display name
     * @return List of professors matching the name
     */

    public List<Professor> getProfessorWithName(String name) {
        System.out.println("Fetching professor with name: " + name);
        return professorRepository.findByDisplayName(name);
    }

    public boolean checkIfAuthorExists(String id) {
        String decodedId = URLDecoder.decode(id, StandardCharsets.UTF_8);
        System.out.println("🔍 Checking Neo4j for Author ID: " + decodedId);
        boolean exists = professorRepository.existsByAuthorId(decodedId);
        System.out.println("🟢 Author exists? " + exists);
        return exists;
    }

    /**
     * 1️⃣ Fetch all authors for a given paper ID
     */
    public List<Professor> getAuthorsByPaperId(String paperId) {
        System.out.println("📄 Fetching authors for paper ID: " + paperId);
        return professorRepository.findAuthorsByPaperId(paperId);
    }

    /**
     * 2️⃣ Fetch all coauthors for a given author ID
     */
    public List<Professor> getCoauthorsByAuthorId(String authorId) {
        System.out.println("👥 Fetching coauthors for author ID: " + authorId);
        return professorRepository.findCoauthorsByAuthorId(authorId);
    }

    /**
 * 3️⃣ Fetch all topics for a given author ID
 */
public List<String> getTopicsByAuthorId(String authorId) {
    System.out.println("service: Fetching topics for author ID: " + authorId);
    return professorRepository.findTopicsByAuthorId(authorId);
}

/**
 * Fetch all papers for a given author and topic
 */
public List<Paper> getPapersByAuthorIdAndTopic(String authorId, String topicName) {
    System.out.println("Service: Fetching papers for author ID: " + authorId +
                       " and topic: " + topicName);
    return professorRepository.findPapersByAuthorIdAndTopic(authorId, topicName);
}

public boolean shouldIngest(String authorId) {
    String decodedId = URLDecoder.decode(authorId, StandardCharsets.UTF_8);
    System.out.println("Checking if author with ID " + decodedId + " should be ingested.");

    // 1️⃣ Check if author exists
    boolean exists = professorRepository.existsByAuthorId(decodedId);
    if (!exists) {
        System.out.println("🟠 Author not found in Neo4j. Should ingest.");
        return true;
    }

    // 2️⃣ Check if fully ingested
    Boolean ingested = professorRepository.isFullyIngested(decodedId);
    System.out.println("🟢 Author ingested status: " + ingested);

    // 3️⃣ Check if data is stale (>15 days old)
    String lastFetchedStr = professorRepository.getLastFetchedDate(decodedId);
    if (lastFetchedStr != null) {
        try {
            LocalDateTime lastFetched = LocalDateTime.parse(lastFetchedStr, DateTimeFormatter.ISO_DATE_TIME);
            LocalDateTime now = LocalDateTime.now();
            long minutes = ChronoUnit.MINUTES.between(lastFetched, now);
            long days = ChronoUnit.DAYS.between(lastFetched, now);
            if (days > 15 ) {
                System.out.println("🟡 Author data is " + days + " days old. Should re-ingest.");
                return true;
            }
            else{
                System.out.println("🟢 Author data is fresh (" + days + " days old). No need to re-ingest.");
            }
        } catch (Exception e) {
            System.out.println("⚠️ Could not parse lastFetched date: " + lastFetchedStr);
        }
    }

    // If not ingested or null → re-ingest
    return ingested == null || !ingested;
}



    


}
