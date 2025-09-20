package com.scholarsphere.graphservice.repository;

import com.scholarsphere.graphservice.model.Professor;
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface ProfessorRepository extends Neo4jRepository<Professor, String> {

    // Custom query: fetch professor and expand authored papers
    @Query("""
           MATCH (p:Professor {id: $id})-[:AUTHORED]->(paper:Paper)
           RETURN p, collect(paper) as papers
           """)
    Optional<Professor> findProfessorWithPapers(String id);
}
