package com.scholarsphere.graphservice.controller;

import com.scholarsphere.graphservice.model.Professor;
import com.scholarsphere.graphservice.services.ProfessorService;
import com.scholarsphere.graphservice.repository.ProfessorRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
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

    // @GetMapping("/{name}/graph")
    // public ResponseEntity<Professor> getAuthorByName(@RequestParam String name) {
    //     Optional<Professor> professorOpt = professorService.getProfessorWithName(name);
    //     return professorOpt
    //                     .map(ResponseEntity::ok)
    //                     .orElse(ResponseEntity.notFound().build());
    // }


    @GetMapping("/by-name")
    public ResponseEntity<List<Professor>> getAuthorsByName(@RequestParam String name) {
        List<Professor> authors = professorService.getProfessorWithName(name);

        if (authors.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(authors);
    }



//     @GetMapping("/{id}/graph")
// public ResponseEntity<Professor> getProfessorGraph(@PathVariable String id) {
//     return professorRepository.findProfessorWithPapersById(id)
//             .map(ResponseEntity::ok)
//             .orElse(ResponseEntity.notFound().build());
// }

}
