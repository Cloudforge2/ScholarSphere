package com.scholarsphere.graphservice.controller;

import com.scholarsphere.graphservice.model.Professor;
import com.scholarsphere.graphservice.services.ProfessorService;
import com.scholarsphere.graphservice.repository.ProfessorRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.data.neo4j.core.Neo4jClient;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/professors")
public class ProfessorController {

    private final ProfessorService professorService;
    private final Neo4jClient neo4jClient;

    public ProfessorController(ProfessorService professorService, Neo4jClient neo4jClient) {
        this.professorService = professorService;
        this.neo4jClient = neo4jClient;
        
    }

    
    /**
     * Get a professor and their authored papers as a graph structure.
     *
     * Example: GET /api/professors/123/graph
     */
    @GetMapping("/{id:.+}/graph")
    public ResponseEntity<Professor> getProfessorGraph(@PathVariable String id) {
        String decodedId = URLDecoder.decode(id, StandardCharsets.UTF_8);
        System.out.println("Fetching professor with decoded ID: " + decodedId);
        Optional<Professor> professorOpt = professorService.getProfessorWithPapers(decodedId);
    
        return professorOpt.map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }


    @GetMapping("/by-name")
    public ResponseEntity<List<Professor>> getAuthorsByName(@RequestParam String name) {
        List<Professor> authors = professorService.getProfessorWithName(name);

        if (authors.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(authors);
    }

    @GetMapping("/exists/{id:.+}")
    public ResponseEntity<Boolean> authorExists(@PathVariable String id) {
        boolean exists = professorService.checkIfAuthorExists(id);
        return ResponseEntity.ok(exists);
    }
    



}