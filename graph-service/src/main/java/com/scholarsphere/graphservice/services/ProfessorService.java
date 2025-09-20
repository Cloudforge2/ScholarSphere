package com.scholarsphere.graphservice.services;

import com.scholarsphere.graphservice.model.Professor;
import com.scholarsphere.graphservice.repository.ProfessorRepository;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
public class ProfessorService {

    private final ProfessorRepository professorRepository;

    public ProfessorService(ProfessorRepository professorRepository) {
        this.professorRepository = professorRepository;
    }

    /**
     * Fetch a professor and their authored papers from Neo4j.
     *
     * @param id Professor ID
     * @return Professor with related papers (if found)
     */
    public Optional<Professor> getProfessorWithPapers(String id) {
        return professorRepository.findProfessorWithPapers(id);
    }
}
