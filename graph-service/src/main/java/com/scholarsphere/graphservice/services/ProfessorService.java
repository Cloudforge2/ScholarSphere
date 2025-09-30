package com.scholarsphere.graphservice.services;

import com.scholarsphere.graphservice.model.Professor;
import com.scholarsphere.graphservice.repository.ProfessorRepository;
import org.springframework.stereotype.Service;

import java.util.Optional;
import java.util.List;

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
        System.out.println("Fetching professor with ID: " + id);
        return professorRepository.findAuthorWithWorks(id);
    }

    public List<Professor> getProfessorWithName(String name) {
        System.out.println("Fetching professor with name: " + name);
        //return professorRepository.findAuthorWithWorksByName(name);
        return professorRepository.findByDisplayName(name);
    }
}
