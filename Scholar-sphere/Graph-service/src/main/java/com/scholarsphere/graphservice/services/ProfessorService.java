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

    


}