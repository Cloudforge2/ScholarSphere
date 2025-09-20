package com.scholarsphere.graphservice.controller;

import com.scholarsphere.graphservice.model.Professor;
import com.scholarsphere.graphservice.services.ProfessorService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Optional;

@RestController
@RequestMapping("/api/professors")
public class ProfessorController {

    private final ProfessorService professorService;

    public ProfessorController(ProfessorService professorService) {
        this.professorService = professorService;
    }

    /**
     * Get a professor and their authored papers as a graph structure.
     *
     * Example: GET /api/professors/123/graph
     */
    @GetMapping("/{id}/graph")
    public ResponseEntity<Professor> getProfessorGraph(@PathVariable String id) {
        Optional<Professor> professorOpt = professorService.getProfessorWithPapers(id);

        return professorOpt
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }
}
